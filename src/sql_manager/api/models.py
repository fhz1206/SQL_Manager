"""API 请求/响应模型

定义局域网转发API的所有数据契约，包括：
- 数据库连接参数
- SQL执行请求/响应（含 is_slow_sql、IO耗时、分段加载）
- 数据库组/分片管理
- 负载均衡与同步状态
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ---------------------------------------------------------------------------
# 连接相关
# ---------------------------------------------------------------------------
class ConnectionParams(BaseModel):
    """数据库连接参数"""
    type: str = Field(..., description="数据库类型: sqlite/mysql/postgres/mariadb/sqlserver/oracle/...")
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    charset: Optional[str] = "utf8mb4"
    timeout: Optional[int] = 30


class ConnectRequest(BaseModel):
    node_id: str = Field(..., description="唯一节点ID")
    params: ConnectionParams


class ConnectResponse(BaseModel):
    success: bool
    message: str
    node_id: str
    db_info: Optional[Dict[str, Any]] = None


class DisconnectRequest(BaseModel):
    node_id: str


# ---------------------------------------------------------------------------
# SQL 执行
# ---------------------------------------------------------------------------
class SqlExecuteRequest(BaseModel):
    node_id: str = Field(..., description="目标节点ID；为空时自动负载均衡路由")
    sql: str = Field(..., description="标准SQL语句")
    page_size: int = Field(default=100, ge=1, le=10000, description="分段加载行数")
    page: int = Field(default=1, ge=1, description="页码，从1开始")
    slow_sql_threshold_ms: int = Field(default=1000, ge=0, description="慢SQL阈值(ms)，超过即标记为慢SQL")


class SqlExecuteResponse(BaseModel):
    success: bool
    message: str
    node_id: str
    sql: str
    columns: List[str] = []
    rows: List[List[Any]] = []
    total_rows: int = 0
    loaded_rows: int = 0
    has_more: bool = False
    page: int = 1
    page_size: int = 100
    io_cost_ms: float = 0.0
    is_slow_sql: bool = False
    executed_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# 数据库组 / 分片
# ---------------------------------------------------------------------------
class DbGroupCreateRequest(BaseModel):
    group_id: str
    description: Optional[str] = None
    shard_size: int = Field(default=1000000, ge=1, description="单分片最大行数")


class DbGroupAddNodeRequest(BaseModel):
    group_id: str
    node_id: str


class ShardInfo(BaseModel):
    shard_id: str
    group_id: str
    node_id: str
    row_count: int
    range_start: Optional[Any] = None
    range_end: Optional[Any] = None


# ---------------------------------------------------------------------------
# 负载均衡 / 同步
# ---------------------------------------------------------------------------
class LoadBalanceStrategy(str):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONN = "least_conn"


class SyncRequest(BaseModel):
    source_group: str
    target_group: str
    tables: Optional[List[str]] = None


class SyncResponse(BaseModel):
    success: bool
    message: str
    synced_tables: int = 0
    synced_rows: int = 0
    cost_ms: float = 0.0


# ---------------------------------------------------------------------------
# 节点状态
# ---------------------------------------------------------------------------
class NodeStatus(BaseModel):
    node_id: str
    type: str
    host: Optional[str] = None
    port: Optional[int] = None
    connected: bool = False
    qps: float = 0.0
    avg_io_ms: float = 0.0
    slow_sql_count: int = 0
    last_heartbeat: Optional[str] = None
