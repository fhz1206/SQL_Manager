"""Nebula Graph 图数据库驱动"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sql_manager.drivers.base import BaseDriver


class NebulaGraphDriver(BaseDriver):
    """Nebula Graph 驱动

    通过 nebula-python 客户端连接，执行 nGQL 语句。
    """

    def connect(self) -> bool:
        try:
            from nebula3.gclient.net import ConnectionPool
            from nebula3.Config import Config
        except ImportError:
            raise ImportError("请安装 nebula3-python: pip install nebula3-python")
        config = Config()
        config.max_connection_pool_size = self.params.get("pool_size", 10)
        self.pool = ConnectionPool()
        ok = self.pool.init(
            [(self.params.get("host", "localhost"), self.params.get("port", 9669))],
            config,
        )
        if not ok:
            raise ConnectionError("Nebula Graph 连接池初始化失败")
        self.session = self.pool.get_session(
            self.params.get("user", "root"),
            self.params.get("password", "nebula"),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # sql 为 nGQL 语句
        try:
            self._last_result = self.session.execute(sql)
            return True
        except Exception as e:
            print(f"[NebulaGraphDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        res = getattr(self, "_last_result", None)
        if res is None:
            return []
        try:
            return [row.values() for row in res.rows()]
        except Exception:
            return []

    def fetchone(self) -> Optional[Any]:
        res = self.fetchall()
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        # Nebula Graph 中 "空间" 对应表的概念
        if not self.execute("SHOW SPACES"):
            return []
        return [r[0] for r in self.fetchall()]

    def get_table_info(self, table_name: str) -> List[Any]:
        if not self.execute(f"USE {table_name}"):
            return []
        if not self.execute("SHOW TAGS"):
            return []
        return [[r[0]] for r in self.fetchall()]

    def disconnect(self) -> None:
        try:
            if getattr(self, "session", None):
                self.session.release()
            if getattr(self, "pool", None):
                self.pool.close()
        except Exception:
            pass
        self.connected = False
