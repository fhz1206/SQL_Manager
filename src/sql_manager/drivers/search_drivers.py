"""Elasticsearch / OpenSearch 驱动

统一接口：
- execute(sql)：sql 为索引名，params 为 DSL 查询体（dict）
- fetchall()：返回命中文档列表
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .base import BaseDriver


class ElasticsearchDriver(BaseDriver):
    """Elasticsearch / OpenSearch 驱动"""

    def connect(self) -> bool:
        try:
            from elasticsearch import Elasticsearch
        except ImportError:
            raise ImportError("请安装 elasticsearch: pip install elasticsearch")
        hosts = [f"http://{self.params.get('host','localhost')}:{self.params.get('port',9200)}"]
        self.conn = Elasticsearch(
            hosts,
            basic_auth=(self.params.get("user", ""), self.params.get("password", "")),
            request_timeout=self.params.get("timeout", 30),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # sql = 索引名，params = ES DSL 查询体
        try:
            if not isinstance(params, dict):
                params = {}
            body = {
                "query": params.get("query", {"match_all": {}}),
                "size": params.get("limit", 100),
                "sort": params.get("sort"),
                "filter_path": params.get("filter_path"),
            }
            self._last_result = self.conn.search(index=sql, body=body)
            return True
        except Exception as e:
            print(f"[ElasticsearchDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        res = getattr(self, "_last_result", {})
        hits = res.get("hits", {}).get("hits", [])
        return [h.get("_source", {}) for h in hits]

    def fetchone(self) -> Optional[Any]:
        res = self.fetchall()
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        try:
            return list(self.conn.indices.get_alias().keys())
        except Exception:
            return []

    def get_table_info(self, table_name: str) -> List[Any]:
        try:
            return [self.conn.indices.get_mapping(index=table_name)]
        except Exception:
            return []

    def disconnect(self) -> None:
        self.connected = False
