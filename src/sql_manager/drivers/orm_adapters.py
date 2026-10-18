"""ORM 抽象适配层

支持：SQLAlchemy、Django ORM、Peewee、Tortoise ORM

本层不直接持有数据库连接，而是封装对各 ORM 的常见操作：
- 执行原生 SQL（分段读取）
- 获取表列表与表结构
- 统一返回 (columns, rows) 格式，便于与驱动层对接
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Tuple


# ---------------------------------------------------------------------------
# SQLAlchemy 适配器
# ---------------------------------------------------------------------------
class SqlAlchemyAdapter:
    """SQLAlchemy 原生 SQL 分段执行适配器"""

    def __init__(self, engine_or_session, params: Optional[Dict[str, Any]] = None):
        self.engine = engine_or_session
        self.params = params or {}
        self.connected = engine_or_session is not None

    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None):
        try:
            from sqlalchemy import text
            if hasattr(self.engine, "connect"):
                with self.engine.connect() as conn:
                    result = conn.execute(text(sql), params or {})
                    return result
            else:
                result = self.engine.execute(text(sql), params or {})
                return result
        except Exception as e:
            print(f"[SqlAlchemyAdapter] 执行失败: {e}")
            return None

    def fetch_columns(self, result) -> List[str]:
        try:
            return list(result.keys())
        except Exception:
            return []

    def fetch_rows(self, result) -> List[List[Any]]:
        try:
            return [list(row) for row in result.fetchall()]
        except Exception:
            return []

    def read_chunked(
        self, sql: str, chunksize: int = 1000, params: Optional[Dict[str, Any]] = None
    ) -> Generator[Tuple[List[str], List[List[Any]]], None, None]:
        """使用 SQLAlchemy 原生执行 + 分段读取（避免一次性加载全部）"""
        result = self.execute(sql, params)
        if result is None:
            return
        columns = self.fetch_columns(result)
        offset = 0
        while True:
            page_sql = f"{sql.rstrip().rstrip(';')} LIMIT {chunksize} OFFSET {offset}"
            page_result = self.execute(page_sql, params)
            if page_result is None:
                break
            rows = self.fetch_rows(page_result)
            if not rows:
                break
            yield columns, rows
            offset += len(rows)
            if len(rows) < chunksize:
                break


# ---------------------------------------------------------------------------
# Django ORM 适配器（需在 Django 项目中使用）
# ---------------------------------------------------------------------------
class DjangoORMAdapter:
    """Django ORM 原生 SQL 分段执行适配器"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self.connected = False
        try:
            import django  # noqa: F401
            from django.db import connection
            self.connection = connection
            self.connected = True
        except ImportError:
            print("[DjangoORMAdapter] Django 未安装，请先在 Django 项目中使用")
            self.connection = None

    def read_chunked(
        self, sql: str, chunksize: int = 1000, params: Optional[Dict[str, Any]] = None
    ) -> Generator[Tuple[List[str], List[List[Any]]], None, None]:
        """使用 Django connection.cursor 分段读取"""
        if self.connection is None:
            return
        with self.connection.cursor() as cursor:
            offset = 0
            while True:
                page_sql = f"{sql.rstrip().rstrip(';')} LIMIT {chunksize} OFFSET {offset}"
                cursor.execute(page_sql, params or {})
                columns = [col[0] for col in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                if not rows:
                    break
                yield columns, [list(r) for r in rows]
                offset += len(rows)
                if len(rows) < chunksize:
                    break

    def get_tables(self) -> List[str]:
        if self.connection is None:
            return []
        return self.connection.introspection.table_names()


# ---------------------------------------------------------------------------
# Peewee 适配器
# ---------------------------------------------------------------------------
class PeeweeAdapter:
    """Peewee 原生 SQL 分段执行适配器"""

    def __init__(self, database, params: Optional[Dict[str, Any]] = None):
        self.database = database
        self.params = params or {}
        self.connected = database is not None

    def read_chunked(
        self, sql: str, chunksize: int = 1000, params: Optional[Dict[str, Any]] = None
    ) -> Generator[Tuple[List[str], List[List[Any]]], None, None]:
        """使用 Peewee execute_sql 分段读取"""
        offset = 0
        while True:
            page_sql = f"{sql.rstrip().rstrip(';')} LIMIT {chunksize} OFFSET {offset}"
            cursor = self.database.execute_sql(page_sql, params or ())
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            if not rows:
                break
            yield columns, [list(r) for r in rows]
            offset += len(rows)
            if len(rows) < chunksize:
                break

    def get_tables(self) -> List[str]:
        try:
            return self.database.get_tables()
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Tortoise ORM 适配器（异步）
# ---------------------------------------------------------------------------
class TortoiseAdapter:
    """Tortoise ORM 原生 SQL 分段执行适配器（异步，需在 async 环境调用）"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self.connected = False

    async def read_chunked(
        self, sql: str, chunksize: int = 1000, params: Optional[Dict[str, Any]] = None
    ) -> Generator[Tuple[List[str], List[List[Any]]], None, None]:
        """使用 Tortoise execute_query 分段读取"""
        from tortoise import Tortoise  # type: ignore

        conn = Tortoise.get_connection(list(self.params.keys())[0] if self.params else None)
        offset = 0
        while True:
            page_sql = f"{sql.rstrip().rstrip(';')} LIMIT {chunksize} OFFSET {offset}"
            result = await conn.execute_query(page_sql, params or ())
            columns = result[1] if isinstance(result, tuple) and len(result) > 1 else []
            rows = result[0] if isinstance(result, tuple) and len(result) > 0 else result
            if not rows:
                break
            yield columns, [list(r) for r in rows]
            offset += len(rows)
            if len(rows) < chunksize:
                break
