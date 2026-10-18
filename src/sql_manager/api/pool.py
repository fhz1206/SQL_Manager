"""数据库节点连接池与节点管理

负责：
- 多节点数据库连接的建立与复用
- 负载均衡路由（轮询/随机/最少连接）
- 慢SQL检测与 IO 耗时统计
- 节点状态心跳与 QPS 统计
"""

import time
import threading
import random
from typing import Dict, Optional, List, Any
from collections import defaultdict, deque

from sql_manager.api.models import (
    ConnectionParams, NodeStatus, LoadBalanceStrategy,
    SqlExecuteResponse,
)
from sql_manager.core.db_manager import DatabaseConnection


class NodeStats:
    """单节点运行时统计"""
    def __init__(self, node_id: str, params: ConnectionParams):
        self.node_id = node_id
        self.params = params
        self.connected = False
        self.qps = 0.0
        self.avg_io_ms = 0.0
        self.slow_sql_count = 0
        self.last_heartbeat: Optional[str] = None
        self._conn_count = 0
        self._io_samples: deque = deque(maxlen=100)
        self._lock = threading.Lock()
        self._last_second = int(time.time())
        self._req_last_second = 0

    def record_request(self, io_ms: float, is_slow: bool):
        with self._lock:
            self._conn_count += 1
            self._io_samples.append(io_ms)
            self.avg_io_ms = sum(self._io_samples) / len(self._io_samples)
            if is_slow:
                self.slow_sql_count += 1
            now = int(time.time())
            self._req_last_second += 1
            if now != self._last_second:
                self.qps = self._req_last_second
                self._req_last_second = 0
                self._last_second = now
            self.last_heartbeat = time.strftime("%H:%M:%S")

    def to_status(self) -> NodeStatus:
        with self._lock:
            return NodeStatus(
                node_id=self.node_id,
                type=self.params.type,
                host=self.params.host,
                port=self.params.port,
                connected=self.connected,
                qps=self.qps,
                avg_io_ms=round(self.avg_io_ms, 2),
                slow_sql_count=self.slow_sql_count,
                last_heartbeat=self.last_heartbeat,
            )


class ConnectionPool:
    """多节点连接池与负载均衡管理器"""

    def __init__(self, slow_sql_threshold_ms: int = 1000):
        self._nodes: Dict[str, NodeStats] = {}
        self._connections: Dict[str, DatabaseConnection] = {}
        self._lock = threading.RLock()
        self.slow_sql_threshold_ms = slow_sql_threshold_ms
        # 轮询游标（按组维护）
        self._rr_cursors: Dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # 节点管理
    # ------------------------------------------------------------------
    def add_node(self, node_id: str, params: ConnectionParams) -> None:
        with self._lock:
            self._nodes[node_id] = NodeStats(node_id, params)

    def remove_node(self, node_id: str) -> None:
        with self._lock:
            self._nodes.pop(node_id, None)
            self._connections.pop(node_id, None)

    def get_node(self, node_id: str) -> Optional[NodeStats]:
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self) -> List[NodeStats]:
        with self._lock:
            return [n.to_status() for n in self._nodes.values()]

    def list_nodes_status(self) -> List[NodeStatus]:
        return self.list_nodes()

    def mark_connected(self, node_id: str, connected: bool = True) -> None:
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].connected = connected

    # ------------------------------------------------------------------
    # 连接获取/释放
    # ------------------------------------------------------------------
    def get_connection(self, node_id: str) -> Optional[DatabaseConnection]:
        with self._lock:
            conn = self._connections.get(node_id)
            if conn is None:
                stats = self._nodes.get(node_id)
                if stats is None:
                    return None
                conn = DatabaseConnection(stats.params.type, {
                    "host": stats.params.host,
                    "port": stats.params.port,
                    "user": stats.params.user,
                    "password": stats.params.password,
                    "database": stats.params.database,
                    "charset": stats.params.charset,
                    "timeout": stats.params.timeout or 30,
                })
                if conn.connect():
                    self._connections[node_id] = conn
                    stats.connected = True
                    return conn
                else:
                    stats.connected = False
                    return None
            return conn

    def close_connection(self, node_id: str) -> None:
        with self._lock:
            conn = self._connections.pop(node_id, None)
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass
            if node_id in self._nodes:
                self._nodes[node_id].connected = False

    # ------------------------------------------------------------------
    # 负载均衡路由
    # ------------------------------------------------------------------
    def route_node(self, strategy: str = LoadBalanceStrategy.ROUND_ROBIN,
                   group_nodes: Optional[List[str]] = None) -> Optional[str]:
        """根据策略选择一个可用节点"""
        with self._lock:
            candidates = group_nodes or [nid for nid, n in self._nodes.items() if n.connected]
            candidates = [nid for nid in candidates if nid in self._nodes and self._nodes[nid].connected]
            if not candidates:
                return None

            if strategy == LoadBalanceStrategy.RANDOM:
                return random.choice(candidates)

            if strategy == LoadBalanceStrategy.LEAST_CONN:
                # 选当前活跃连接/请求数最少的（简化用 qps 反比）
                best = min(candidates, key=lambda nid: self._nodes[nid].qps)
                return best

            # round_robin
            key = ",".join(candidates)
            cursor = self._rr_cursors[key] % len(candidates)
            chosen = candidates[cursor]
            self._rr_cursors[key] = cursor + 1
            return chosen

    # ------------------------------------------------------------------
    # SQL 执行（带慢SQL检测、分段、IO统计）
    # ------------------------------------------------------------------
    def execute_sql(self, node_id: Optional[str], sql: str, page_size: int = 100,
                    page: int = 1, threshold_ms: int = 1000,
                    strategy: str = LoadBalanceStrategy.ROUND_ROBIN,
                    group_nodes: Optional[List[str]] = None) -> SqlExecuteResponse:
        """在指定节点或负载均衡选定节点执行SQL，返回分段结果与慢SQL标记。"""
        start = time.perf_counter()
        target_id = node_id
        if not target_id:
            target_id = self.route_node(strategy, group_nodes)
        if not target_id:
            return SqlExecuteResponse(
                success=False, message="没有可用的数据库节点",
                node_id="", sql=sql,
            )

        stats = self._nodes.get(target_id)
        if stats is None:
            return SqlExecuteResponse(
                success=False, message=f"节点 {target_id} 不存在",
                node_id=target_id or "", sql=sql,
            )

        conn = self.get_connection(target_id)
        if conn is None:
            stats.connected = False
            return SqlExecuteResponse(
                success=False, message=f"无法连接到节点 {target_id}",
                node_id=target_id, sql=sql,
            )

        try:
            # 执行查询
            cur = conn.cursor
            cur.execute(sql)
            first_word = sql.split(None, 1)[0].upper() if sql.split() else ""

            columns: List[str] = []
            rows: List[List[Any]] = []
            total_rows = 0
            loaded_rows = 0
            has_more = False

            if first_word in ("SELECT", "WITH", "PRAGMA", "EXPLAIN", "VALUES"):
                all_rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description] if cur.description else []
                total_rows = len(all_rows)
                # 分段加载
                offset = (page - 1) * page_size
                page_rows = all_rows[offset:offset + page_size]
                rows = [list(r) for r in page_rows]
                loaded_rows = len(rows)
                has_more = offset + loaded_rows < total_rows
            else:
                if hasattr(conn, "commit"):
                    conn.commit()
                total_rows = cur.rowcount if hasattr(cur, "rowcount") else 0
                rows = []
                loaded_rows = 0
                has_more = False

            io_ms = (time.perf_counter() - start) * 1000.0
            is_slow = io_ms > threshold_ms
            stats.record_request(io_ms, is_slow)

            return SqlExecuteResponse(
                success=True,
                message="执行成功",
                node_id=target_id,
                sql=sql,
                columns=columns,
                rows=rows,
                total_rows=total_rows,
                loaded_rows=loaded_rows,
                has_more=has_more,
                page=page,
                page_size=page_size,
                io_cost_ms=round(io_ms, 2),
                is_slow_sql=is_slow,
            )
        except Exception as exc:
            io_ms = (time.perf_counter() - start) * 1000.0
            stats.record_request(io_ms, False)
            return SqlExecuteResponse(
                success=False,
                message=f"SQL执行错误: {exc}",
                node_id=target_id,
                sql=sql,
                io_cost_ms=round(io_ms, 2),
                is_slow_sql=False,
            )

    def close_all(self) -> None:
        with self._lock:
            for nid in list(self._connections.keys()):
                self.close_connection(nid)
