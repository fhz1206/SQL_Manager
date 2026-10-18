"""数据库驱动抽象基类

所有数据库驱动均继承 BaseDriver，实现统一接口：
- connect(params) -> bool
- execute(sql, params=None) -> bool
- fetchall() -> list
- fetchone() -> dict|tuple|None
- read_sql_chunked(sql, chunksize) -> generator of (columns, rows)
- get_tables() -> list
- get_table_info(table_name) -> list
- disconnect()
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Tuple
from abc import ABC, abstractmethod


class BaseDriver(ABC):
    """数据库驱动基类"""

    def __init__(self, params: Dict[str, Any]):
        self.params = params or {}
        self.conn = None
        self.cursor = None
        self.connected = False

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        raise NotImplementedError

    @abstractmethod
    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        """执行SQL"""
        raise NotImplementedError

    @abstractmethod
    def fetchall(self) -> List[Any]:
        """获取全部结果"""
        raise NotImplementedError

    @abstractmethod
    def fetchone(self) -> Optional[Any]:
        """获取单条结果"""
        raise NotImplementedError

    @abstractmethod
    def get_tables(self) -> List[str]:
        """获取表列表"""
        raise NotImplementedError

    @abstractmethod
    def get_table_info(self, table_name: str) -> List[Any]:
        """获取表结构"""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """断开连接"""
        raise NotImplementedError

    def read_sql_chunked(
        self, sql: str, chunksize: int = 1000
    ) -> Generator[Tuple[List[str], List[List[Any]]], None, None]:
        """分段读取SQL结果（基于LIMIT/OFFSET实现，子类可覆盖为原生分页）

        Yields:
            (columns, rows) 元组
        """
        offset = 0
        while True:
            page_sql = f"{sql.rstrip().rstrip(';')} LIMIT {chunksize} OFFSET {offset}"
            if not self.execute(page_sql):
                break
            columns = [d[0] for d in self.cursor.description] if self.cursor and self.cursor.description else []
            rows = self.fetchall()
            if not rows:
                break
            yield columns, rows
            offset += len(rows)
            if len(rows) < chunksize:
                break

    def commit(self) -> None:
        if self.conn and hasattr(self.conn, "commit"):
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn and hasattr(self.conn, "rollback"):
            self.conn.rollback()
