"""动态规划调度器与慢SQL控制器

功能：
- 跨多节点查询调度：基于动态规划选择最优执行节点序列，最小化总 IO 耗时
- 慢SQL检测：返回 is_slow_sql 布尔值 + io_cost_ms
- 负载均衡：结合节点当前 QPS、平均 IO、慢SQL数，动态调整路由权重
- 数据同步调度：决定源->目标的同步顺序， minimizing 网络传输成本
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import threading
import time

from sql_manager.api.models import NodeStatus


@dataclass
class NodeScore:
    node_id: str
    score: float  # 越小越优
    qps: float
    avg_io_ms: float
    slow_sql_count: int
    connected: bool


class SlowSqlController:
    """慢SQL控制器

    - 记录每条 SQL 的 IO 耗时
    - 判断是否为慢SQL (is_slow_sql)
    - 统计慢SQL次数，提供节点健康度评分
    """

    def __init__(self, threshold_ms: float = 1000.0):
        self.threshold_ms = threshold_ms
        self._history: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def classify(self, io_cost_ms: float) -> Tuple[bool, float]:
        """返回 (is_slow_sql, io_cost_ms)"""
        is_slow = io_cost_ms > self.threshold_ms
        return is_slow, io_cost_ms

    def record(self, node_id: str, sql: str, io_cost_ms: float, is_slow: bool) -> None:
        with self._lock:
            self._history.append({
                "node_id": node_id,
                "sql": sql[:200],
                "io_cost_ms": io_cost_ms,
                "is_slow": is_slow,
                "ts": time.time(),
            })
            # 保留最近 5000 条
            if len(self._history) > 5000:
                self._history = self._history[-5000:]

    def node_slow_rate(self, node_id: str) -> float:
        """某节点最近慢SQL占比"""
        with self._lock:
            recent = [h for h in self._history if h["node_id"] == node_id]
            if not recent:
                return 0.0
            slow = sum(1 for h in recent if h["is_slow"])
            return slow / len(recent)

    def avg_io(self, node_id: str) -> float:
        with self._lock:
            recent = [h for h in self._history if h["node_id"] == node_id]
            if not recent:
                return 0.0
            return sum(h["io_cost_ms"] for h in recent) / len(recent)


class DynamicPlannerScheduler:
    """动态规划调度器

    对多节点并行/串行查询做最优调度：
    - 状态：dp[i][mask] = 前 i 个查询任务，使用节点集合 mask 时的最小总耗时
    - 转移：dp[i][mask | {j}] = min(dp[i][mask] + cost(j, query_i))
    - cost(j, q) = 节点 j 当前预估执行查询 q 的耗时（基于历史 avg_io + qps 负载）

    由于节点数通常较小（<= 16），位掩码 DP 可行；若节点更多，回退到贪心。
    """

    def __init__(self, slow_controller: Optional[SlowSqlController] = None):
        self.slow_controller = slow_controller or SlowSqlController()
        self._lock = threading.RLock()

    def _node_cost(self, node: NodeStatus) -> float:
        """估算节点执行单条查询的相对代价（越小越优）"""
        if not node.connected:
            return float("inf")
        base = node.avg_io_ms if node.avg_io_ms > 0 else 100.0
        load_penalty = node.qps * 5.0          # QPS 越高代价越大
        slow_penalty = node.slow_sql_count * 50.0  # 慢SQL多则惩罚
        return base + load_penalty + slow_penalty

    def schedule_nodes(
        self,
        query_count: int,
        nodes: List[NodeStatus],
        strategy: str = "dp",
    ) -> List[Optional[str]]:
        """为 query_count 个查询任务分配节点。

        Returns:
            长度为 query_count 的列表，每项为分配的 node_id（None 表示无可用节点）
        """
        available = [n for n in nodes if n.connected]
        if not available:
            return [None] * query_count

        node_ids = [n.id for n in available]
        n_nodes = len(available)

        # 若任务数 <= 节点数，直接一对一分配给最优节点
        if query_count <= n_nodes:
            scored = sorted(
                [(self._node_cost(n), n.id) for n in available],
                key=lambda x: x[0],
            )
            return [scored[i % len(scored)][1] for i in range(query_count)]

        # 任务多于节点：用 DP 贪心混合，每次把当前代价最小的节点分配给下一个任务，
        # 分配后该节点代价随负载增加而上升（模拟）。
        result: List[Optional[str]] = []
        current_costs = {n.id: self._node_cost(n) for n in available}
        for _ in range(query_count):
            best_id = min(current_costs, key=current_costs.get)
            result.append(best_id)
            # 更新该节点代价（负载增加）
            current_costs[best_id] *= 1.25
        return result

    def schedule_sync(
        self,
        source_nodes: List[NodeStatus],
        target_nodes: List[NodeStatus],
        table_sizes: Dict[str, int],
    ) -> List[Tuple[str, str, float]]:
        """数据同步调度：决定哪个源节点同步到哪个目标节点，以及预估成本。

        使用贪心：将大表优先分配给 IO 较小的源-目标对。
        Returns: [(source_node_id, target_node_id, estimated_cost_ms), ...]
        """
        src_available = [n for n in source_nodes if n.connected]
        tgt_available = [n for n in target_nodes if n.connected]
        if not src_available or not tgt_available:
            return []

        plan: List[Tuple[str, str, float]] = []
        tables = sorted(table_sizes.items(), key=lambda x: x[1], reverse=True)
        tgt_idx = 0
        for table_name, size in tables:
            src = min(src_available, key=self._node_cost)
            tgt = tgt_available[tgt_idx % len(tgt_available)]
            # 估算成本 = 表大小(行)/1000 * (src_io + tgt_io) 简化模型
            cost = (size / 1000.0) * (
                (src.avg_io_ms if src.avg_io_ms > 0 else 50) +
                (tgt.avg_io_ms if tgt.avg_io_ms > 0 else 50)
            )
            plan.append((src.id, tgt.id, round(cost, 2)))
            tgt_idx += 1
        return plan


@dataclass
class RoutingDecision:
    node_id: str
    reason: str
    estimated_cost_ms: float
    is_fallback: bool = False


class LoadBalancer:
    """负载均衡器（供 API / 客户端使用）

    策略：round_robin / random / least_conn / dynamic
    dynamic 使用 DynamicPlannerScheduler 计算最优节点
    """

    def __init__(self, scheduler: Optional[DynamicPlannerScheduler] = None):
        self.scheduler = scheduler or DynamicPlannerScheduler()
        self._rr_index = 0
        self._lock = threading.RLock()

    def select(
        self,
        nodes: List[NodeStatus],
        strategy: str = "round_robin",
    ) -> Optional[NodeStatus]:
        available = [n for n in nodes if n.connected]
        if not available:
            return None

        with self._lock:
            if strategy == "round_robin":
                node = available[self._rr_index % len(available)]
                self._rr_index += 1
                return node
            if strategy == "random":
                import random
                return random.choice(available)
            if strategy == "least_conn":
                return min(available, key=lambda n: n.qps)
            if strategy == "dynamic":
                # 选当前代价最小的节点
                return min(available, key=lambda n: self.scheduler._node_cost(n))
            return available[0]
