"""局域网转发 API 服务器

提供 REST 接口，供桌面客户端或其他局域网客户端：
- 连接/断开多节点数据库
- 执行标准 SQL（分段加载、慢SQL检测、IO耗时、is_slow_sql 布尔值）
- 数据库组 / 分片管理
- 负载均衡与跨服务器数据同步
- 动态规划调度（多节点最优路由）
"""

import threading
import time
import random
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sql_manager.api.models import (
    ConnectRequest, ConnectResponse, DisconnectRequest,
    SqlExecuteRequest, SqlExecuteResponse,
    DbGroupCreateRequest, DbGroupAddNodeRequest, ShardInfo,
    SyncRequest, SyncResponse, NodeStatus,
    LoadBalanceStrategy,
)
from sql_manager.api.pool import ConnectionPool
from sql_manager.core.scheduler import DynamicPlannerScheduler, SlowSqlController, LoadBalancer
from sql_manager.core.shard_manager import ShardManager

app = FastAPI(title="SQL_Manager 局域网转发API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 全局组件 ----------
pool = ConnectionPool(slow_sql_threshold_ms=1000)
slow_controller = SlowSqlController(threshold_ms=1000.0)
scheduler = DynamicPlannerScheduler(slow_controller=slow_controller)
balancer = LoadBalancer(scheduler=scheduler)
shard_manager = ShardManager(default_shard_size=1_000_000)

# 数据库组与分片元数据（内存，生产环境建议持久化到 sqlite/etcd）
_groups: Dict[str, Dict[str, Any]] = {}
_group_nodes: Dict[str, List[str]] = {}
_shard_lock = threading.RLock()

# 心跳
_heartbeat_stop = threading.Event()


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _nodes_status() -> List[NodeStatus]:
    return pool.list_nodes_status()


# ---------------------------------------------------------------------------
# 连接管理
# ---------------------------------------------------------------------------
@app.post("/api/v1/connect", response_model=ConnectResponse)
def connect(req: ConnectRequest):
    """连接一个数据库节点"""
    pool.add_node(req.node_id, req.params)
    conn = pool.get_connection(req.node_id)
    if conn is None:
        pool.mark_connected(req.node_id, False)
        return ConnectResponse(success=False, message="连接失败，请检查连接参数", node_id=req.node_id)
    pool.mark_connected(req.node_id, True)
    try:
        db_info = conn.get_db_info() if hasattr(conn, "get_db_info") else {}
    except Exception:
        db_info = {}
    return ConnectResponse(
        success=True,
        message="连接成功",
        node_id=req.node_id,
        db_info=db_info,
    )


@app.post("/api/v1/disconnect")
def disconnect(req: DisconnectRequest):
    """断开指定节点"""
    pool.close_connection(req.node_id)
    return {"success": True, "message": f"节点 {req.node_id} 已断开"}


@app.get("/api/v1/nodes", response_model=List[NodeStatus])
def list_nodes():
    """列出所有节点状态"""
    return _nodes_status()


# ---------------------------------------------------------------------------
# SQL 执行（核心：分段 + 慢SQL + IO耗时 + 动态调度）
# ---------------------------------------------------------------------------
def _execute_with_strategy(req: SqlExecuteRequest, strategy: str) -> SqlExecuteResponse:
    """根据策略执行SQL，并记录慢SQL统计。"""
    nodes = _nodes_status()
    if req.node_id:
        # 指定节点
        target = req.node_id
        available = any(n.node_id == target and n.connected for n in nodes)
        if not available:
            return SqlExecuteResponse(
                success=False, message=f"节点 {target} 不可用",
                node_id=target, sql=req.sql,
            )
    else:
        # 负载均衡自动路由
        chosen = balancer.select(nodes, strategy=strategy)
        if chosen is None:
            return SqlExecuteResponse(
                success=False, message="没有可用的数据库节点",
                node_id="", sql=req.sql,
            )
        target = chosen.node_id

    resp = pool.execute_sql(
        node_id=target,
        sql=req.sql,
        page_size=req.page_size,
        page=req.page,
        threshold_ms=req.slow_sql_threshold_ms,
        strategy=strategy,
        group_nodes=[n.node_id for n in nodes if n.connected],
    )

    # 记录慢SQL统计（即使失败也记录IO）
    if resp.node_id:
        slow_controller.record(
            node_id=resp.node_id,
            sql=req.sql,
            io_cost_ms=resp.io_cost_ms,
            is_slow=resp.is_slow_sql,
        )
    return resp


@app.post("/api/v1/sql/execute", response_model=SqlExecuteResponse)
def execute_sql(req: SqlExecuteRequest):
    """执行SQL并返回分段结果。

    - is_slow_sql: 是否超过慢SQL阈值
    - io_cost_ms: IO耗时(ms)
    - page/page_size: 分段加载
    """
    return _execute_with_strategy(req, strategy=LoadBalanceStrategy.ROUND_ROBIN)


@app.post("/api/v1/sql/execute/balanced", response_model=SqlExecuteResponse)
def execute_sql_balanced(req: SqlExecuteRequest):
    """使用动态规划调度自动路由执行SQL（node_id可为空）"""
    return _execute_with_strategy(req, strategy="dynamic")


@app.post("/api/v1/sql/execute/random", response_model=SqlExecuteResponse)
def execute_sql_random(req: SqlExecuteRequest):
    """随机路由执行SQL"""
    return _execute_with_strategy(req, strategy=LoadBalanceStrategy.RANDOM)


@app.post("/api/v1/sql/execute/least_conn", response_model=SqlExecuteResponse)
def execute_sql_least_conn(req: SqlExecuteRequest):
    """最少连接路由执行SQL"""
    return _execute_with_strategy(req, strategy=LoadBalanceStrategy.LEAST_CONN)


# ---------------------------------------------------------------------------
# 慢SQL监控
# ---------------------------------------------------------------------------
@app.get("/api/v1/slowsql/stats")
def slow_sql_stats(node_id: Optional[str] = None):
    """查询慢SQL统计"""
    if node_id:
        return {
            "node_id": node_id,
            "slow_rate": slow_controller.node_slow_rate(node_id),
            "avg_io_ms": round(slow_controller.avg_io(node_id), 2),
            "threshold_ms": slow_controller.threshold_ms,
        }
    return {
        "threshold_ms": slow_controller.threshold_ms,
        "total_records": len(slow_controller._history),
    }


# ---------------------------------------------------------------------------
# 数据库组 / 分片
# ---------------------------------------------------------------------------
@app.post("/api/v1/groups")
def create_group(req: DbGroupCreateRequest):
    """创建数据库组（多实例集合提升吞吐）"""
    with _shard_lock:
        if req.group_id in _groups:
            raise HTTPException(status_code=400, detail=f"组 {req.group_id} 已存在")
        _groups[req.group_id] = {
            "group_id": req.group_id,
            "description": req.description,
            "shard_size": req.shard_size,
            "created_at": time.time(),
        }
        _group_nodes[req.group_id] = []
    return {"success": True, "message": f"组 {req.group_id} 创建成功"}


@app.post("/api/v1/groups/{group_id}/nodes")
def add_node_to_group(group_id: str, req: DbGroupAddNodeRequest):
    """将节点加入指定组"""
    with _shard_lock:
        if group_id not in _groups:
            raise HTTPException(status_code=404, detail=f"组 {group_id} 不存在")
        nodes = _group_nodes.setdefault(group_id, [])
        if req.node_id not in nodes:
            nodes.append(req.node_id)
    return {"success": True, "message": f"节点 {req.node_id} 已加入组 {group_id}"}


@app.get("/api/v1/groups/{group_id}/nodes")
def list_group_nodes(group_id: str):
    with _shard_lock:
        return {"group_id": group_id, "nodes": _group_nodes.get(group_id, [])}


@app.post("/api/v1/shards/auto")
def auto_shard_table(
    table_name: str,
    group_id: str,
    total_rows: int,
    shard_size: Optional[int] = None,
    strategy: str = "range",
):
    """为指定表自动切分分片（单分片最大行数可配）"""
    with _shard_lock:
        node_ids = _group_nodes.get(group_id, [])
        if not node_ids:
            raise HTTPException(status_code=400, detail=f"组 {group_id} 没有可用节点")
        shards = shard_manager.auto_shard_table(
            table_name=table_name,
            group_id=group_id,
            node_ids=node_ids,
            total_rows=total_rows,
            shard_size=shard_size,
            strategy=strategy,
        )
    return {
        "success": True,
        "table_name": table_name,
        "shard_count": len(shards),
        "shards": [
            {
                "shard_id": s.shard_id,
                "node_id": s.node_id,
                "strategy": s.shard_strategy,
                "range_start": s.range_start,
                "range_end": s.range_end,
                "hash_mod": s.hash_mod,
                "hash_remainder": s.hash_remainder,
            }
            for s in shards
        ],
    }


@app.get("/api/v1/shards", response_model=List[ShardInfo])
def list_shards(table_name: Optional[str] = None):
    shards = shard_manager.list_shards(table_name)
    return [
        ShardInfo(
            shard_id=s.shard_id,
            group_id=s.group_id,
            node_id=s.node_id,
            row_count=s.row_count,
            range_start=s.range_start,
            range_end=s.range_end,
        )
        for s in shards
    ]


@app.get("/api/v1/shards/locate")
def locate_shard(table_name: str, shard_key: Any, strategy: str = "hash"):
    """根据分片键定位数据所在分片与节点"""
    shard = shard_manager.locate_shard(table_name, shard_key, strategy)
    if shard is None:
        raise HTTPException(status_code=404, detail="未找到匹配分片")
    return {
        "shard_id": shard.shard_id,
        "node_id": shard.node_id,
        "strategy": shard.shard_strategy,
    }


# ---------------------------------------------------------------------------
# 负载均衡与同步
# ---------------------------------------------------------------------------
@app.post("/api/v1/rebalance")
def rebalance():
    """触发负载再均衡"""
    pool._rr_cursors.clear()
    scheduler = DynamicPlannerScheduler(slow_controller=slow_controller)
    return {"success": True, "message": "负载均衡已重置，下次请求将按健康节点重新路由"}


@app.post("/api/v1/sync", response_model=SyncResponse)
def sync_data(req: SyncRequest):
    """跨服务器数据同步（基于动态规划调度决定源->目标对）"""
    start = time.perf_counter()
    with _shard_lock:
        src_nodes = [_nodes_status().__class__(**{k: v for k, v in vars(n).items() if k in NodeStatus.model_fields})
                     for n in _nodes_status() if n.node_id in _group_nodes.get(req.source_group, [])]
        tgt_nodes = [_nodes_status().__class__(**{k: v for k, v in vars(n).items() if k in NodeStatus.model_fields})
                     for n in _nodes_status() if n.node_id in _group_nodes.get(req.target_group, [])]
        tables = req.tables or []
        table_sizes = {t: 100000 for t in tables}  # 占位：实际应查询表行数

    plan = scheduler.schedule_sync(
        source_nodes=src_nodes,
        target_nodes=tgt_nodes,
        table_sizes=table_sizes,
    )
    cost_ms = (time.perf_counter() - start) * 1000.0
    return SyncResponse(
        success=True,
        message=f"组 {req.source_group} -> {req.target_group} 同步计划生成（{len(plan)} 对）",
        synced_tables=len(tables),
        synced_rows=sum(table_sizes.values()),
        cost_ms=round(cost_ms, 2),
    )


# ---------------------------------------------------------------------------
# 动态调度查询（多查询任务批量分配节点）
# ---------------------------------------------------------------------------
@app.post("/api/v1/schedule/batch")
def schedule_batch(query_count: int, strategy: str = "dynamic"):
    """为多个查询任务批量分配最优节点（动态规划/贪心）"""
    nodes = _nodes_status()
    assignment = scheduler.schedule_nodes(query_count=query_count, nodes=nodes, strategy=strategy)
    return {
        "query_count": query_count,
        "strategy": strategy,
        "assignment": assignment,
    }


# ---------------------------------------------------------------------------
# 心跳
# ---------------------------------------------------------------------------
@app.on_event("startup")
def _start_heartbeat():
    def _beat():
        while not _heartbeat_stop.is_set():
            _heartbeat_stop.wait(10)
            for nid, stats in list(pool._nodes.items()):
                if stats.connected:
                    try:
                        conn = pool.get_connection(nid)
                        if conn:
                            cur = conn.cursor
                            cur.execute("SELECT 1")
                    except Exception:
                        stats.connected = False

    t = threading.Thread(target=_beat, daemon=True)
    t.start()


@app.on_event("shutdown")
def _stop_heartbeat():
    _heartbeat_stop.set()
    pool.close_all()
