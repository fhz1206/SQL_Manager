"""桌面客户端 API 客户端

通过 HTTP 调用局域网转发 API 服务器，实现：
- 连接/断开远程数据库节点
- 执行标准 SQL（分段加载、慢SQL检测、IO耗时、is_slow_sql）
- 查询节点状态、负载均衡、数据同步
"""

from typing import Any, Dict, List, Optional
try:
    import requests
except ImportError:  # 惰性依赖：未安装时只在真正发起请求时报错
    requests = None  # type: ignore

from .models import (
    ConnectRequest, ConnectResponse, DisconnectRequest,
    SqlExecuteRequest, SqlExecuteResponse,
    DbGroupCreateRequest, DbGroupAddNodeRequest, ShardInfo,
    SyncRequest, SyncResponse, NodeStatus,
)


class ApiClient:
    """轻量级 API 客户端，封装对 /api/v1/* 接口的调用"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 30):
        if requests is None:
            raise ImportError("ApiClient 需要 requests，请安装: pip install requests")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------
    def connect(self, node_id: str, params: Dict[str, Any]) -> ConnectResponse:
        """连接一个数据库节点"""
        req = ConnectRequest(node_id=node_id, params=params)
        resp = self.session.post(
            f"{self.base_url}/api/v1/connect",
            json=req.model_dump(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return ConnectResponse(**resp.json())

    def disconnect(self, node_id: str) -> Dict[str, Any]:
        """断开指定节点"""
        req = DisconnectRequest(node_id=node_id)
        resp = self.session.post(
            f"{self.base_url}/api/v1/disconnect",
            json=req.model_dump(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def list_nodes(self) -> List[NodeStatus]:
        """列出所有节点状态"""
        resp = self.session.get(f"{self.base_url}/api/v1/nodes", timeout=self.timeout)
        resp.raise_for_status()
        return [NodeStatus(**item) for item in resp.json()]

    # ------------------------------------------------------------------
    # SQL 执行
    # ------------------------------------------------------------------
    def execute_sql(
        self,
        sql: str,
        node_id: Optional[str] = None,
        page_size: int = 100,
        page: int = 1,
        slow_sql_threshold_ms: int = 1000,
        balanced: bool = False,
    ) -> SqlExecuteResponse:
        """执行 SQL，返回分段结果与慢SQL标记。

        - balanced=True 时自动负载均衡路由（node_id 可为空）
        """
        req = SqlExecuteRequest(
            node_id=node_id,
            sql=sql,
            page_size=page_size,
            page=page,
            slow_sql_threshold_ms=slow_sql_threshold_ms,
        )
        endpoint = "/api/v1/sql/execute/balanced" if balanced else "/api/v1/sql/execute"
        resp = self.session.post(
            f"{self.base_url}{endpoint}",
            json=req.model_dump(exclude_none=True),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return SqlExecuteResponse(**resp.json())

    # ------------------------------------------------------------------
    # 数据库组 / 分片
    # ------------------------------------------------------------------
    def create_group(self, group_id: str, description: Optional[str] = None,
                     shard_size: int = 1000000) -> Dict[str, Any]:
        req = DbGroupCreateRequest(
            group_id=group_id, description=description, shard_size=shard_size
        )
        resp = self.session.post(
            f"{self.base_url}/api/v1/groups", json=req.model_dump(), timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def add_node_to_group(self, group_id: str, node_id: str) -> Dict[str, Any]:
        req = DbGroupAddNodeRequest(group_id=group_id, node_id=node_id)
        resp = self.session.post(
            f"{self.base_url}/api/v1/groups/{group_id}/nodes",
            json=req.model_dump(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def list_group_nodes(self, group_id: str) -> Dict[str, Any]:
        resp = self.session.get(
            f"{self.base_url}/api/v1/groups/{group_id}/nodes", timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def list_shards(self) -> List[ShardInfo]:
        resp = self.session.get(f"{self.base_url}/api/v1/shards", timeout=self.timeout)
        resp.raise_for_status()
        return [ShardInfo(**item) for item in resp.json()]

    # ------------------------------------------------------------------
    # 负载均衡与同步
    # ------------------------------------------------------------------
    def rebalance(self) -> Dict[str, Any]:
        resp = self.session.post(f"{self.base_url}/api/v1/rebalance", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def sync_data(self, source_group: str, target_group: str,
                  tables: Optional[List[str]] = None) -> SyncResponse:
        req = SyncRequest(source_group=source_group, target_group=target_group, tables=tables)
        resp = self.session.post(
            f"{self.base_url}/api/v1/sync", json=req.model_dump(), timeout=self.timeout
        )
        resp.raise_for_status()
        return SyncResponse(**resp.json())
