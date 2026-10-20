"""SQL 型数据库驱动

支持：SQLite、MySQL、PostgreSQL、MariaDB、SQL Server、Oracle、
ClickHouse、Apache Doris、StarRocks、TDengine、PGVector（PostgreSQL 扩展）

统一接口：
- connect / execute / fetchall / fetchone
- read_sql_chunked：基于 LIMIT/OFFSET 分段读取（配合 Pandas read_sql 使用）
- get_tables / get_table_info
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Tuple

from .base import BaseDriver


class SqlDriver(BaseDriver):
    """通用 SQL 数据库驱动，通过 db_type 区分具体数据库"""

    def connect(self) -> bool:
        db_type = self.params.get("type", "sqlite")
        try:
            if db_type == "sqlite":
                import sqlite3
                self.conn = sqlite3.connect(
                    self.params.get("database", ":memory:"),
                    timeout=self.params.get("timeout", 30),
                )
                self.cursor = self.conn.cursor()
            elif db_type in ("mysql", "mariadb"):
                try:
                    import pymysql
                except ImportError:
                    raise ImportError("请安装 pymysql: pip install pymysql")
                self.conn = pymysql.connect(
                    host=self.params.get("host", "localhost"),
                    port=self.params.get("port", 3306),
                    user=self.params.get("user", ""),
                    password=self.params.get("password", ""),
                    database=self.params.get("database", ""),
                    charset=self.params.get("charset", "utf8mb4"),
                    cursorclass=pymysql.cursors.Cursor,
                )
                self.cursor = self.conn.cursor()
            elif db_type == "postgres":
                try:
                    import psycopg2
                except ImportError:
                    raise ImportError("请安装 psycopg2-binary: pip install psycopg2-binary")
                import psycopg2.extras
                self.conn = psycopg2.connect(
                    host=self.params.get("host", "localhost"),
                    port=self.params.get("port", 5432),
                    user=self.params.get("user", ""),
                    password=self.params.get("password", ""),
                    database=self.params.get("database", ""),
                )
                self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            elif db_type == "sqlserver":
                try:
                    import pyodbc
                except ImportError:
                    raise ImportError("请安装 pyodbc: pip install pyodbc")
                conn_str = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={self.params.get('host','localhost')},{self.params.get('port',1433)};"
                    f"DATABASE={self.params.get('database','')};"
                    f"UID={self.params.get('user','')};PWD={self.params.get('password','')};"
                )
                self.conn = pyodbc.connect(conn_str, timeout=self.params.get("timeout", 30))
                self.cursor = self.conn.cursor()
            elif db_type == "oracle":
                try:
                    import oracledb
                except ImportError:
                    raise ImportError("请安装 oracledb: pip install oracledb")
                dsn = oracledb.makedsn(
                    self.params.get("host", "localhost"),
                    self.params.get("port", 1521),
                    service_name=self.params.get("database", ""),
                )
                self.conn = oracledb.connect(
                    user=self.params.get("user", ""),
                    password=self.params.get("password", ""),
                    dsn=dsn,
                )
                self.cursor = self.conn.cursor()
            elif db_type in ("clickhouse", "doris", "starrocks"):
                # 兼容 ClickHouse HTTP 原生协议 / MySQL 协议接口
                try:
                    import pymysql
                except ImportError:
                    raise ImportError("请安装 pymysql: pip install pymysql")
                self.conn = pymysql.connect(
                    host=self.params.get("host", "localhost"),
                    port=self.params.get("port", 9000 if db_type == "clickhouse" else 3306),
                    user=self.params.get("user", "default"),
                    password=self.params.get("password", ""),
                    database=self.params.get("database", "default"),
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.Cursor,
                )
                self.cursor = self.conn.cursor()
            elif db_type == "tdengine":
                try:
                    import taosws
                except ImportError:
                    raise ImportError("请安装 taosws: pip install taosws")
                self.conn = taosws.connect(
                    host=self.params.get("host", "localhost"),
                    port=self.params.get("port", 6030),
                    user=self.params.get("user", "root"),
                    password=self.params.get("password", "taosdata"),
                )
                self.cursor = self.conn.cursor()
            elif db_type == "pgvector":
                # PGVector 基于 PostgreSQL，复用 psycopg2
                try:
                    import psycopg2
                except ImportError:
                    raise ImportError("请安装 psycopg2-binary: pip install psycopg2-binary")
                import psycopg2.extras
                self.conn = psycopg2.connect(
                    host=self.params.get("host", "localhost"),
                    port=self.params.get("port", 5432),
                    user=self.params.get("user", ""),
                    password=self.params.get("password", ""),
                    database=self.params.get("database", ""),
                )
                self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                raise ValueError(f"不支持的 SQL 数据库类型: {db_type}")

            self.connected = True
            return True
        except Exception as e:
            self.connected = False
            print(f"[SqlDriver] 连接失败({db_type}): {e}")
            return False

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        if not self.connected or self.cursor is None:
            return False
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            return True
        except Exception as e:
            print(f"[SqlDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        if self.cursor is None:
            return []
        try:
            return self.cursor.fetchall()
        except Exception as e:
            print(f"[SqlDriver] fetchall 失败: {e}")
            return []

    def fetchone(self) -> Optional[Any]:
        if self.cursor is None:
            return None
        try:
            return self.cursor.fetchone()
        except Exception as e:
            print(f"[SqlDriver] fetchone 失败: {e}")
            return None

    def get_tables(self) -> List[str]:
        db_type = self.params.get("type", "sqlite")
        try:
            if db_type == "sqlite":
                self.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                return [r[0] for r in self.fetchall()]
            elif db_type in ("mysql", "mariadb", "clickhouse", "doris", "starrocks"):
                self.execute("SHOW TABLES")
                rows = self.fetchall()
                return [r[0] if isinstance(r, (list, tuple)) else list(r.values())[0] for r in rows]
            elif db_type == "postgres":
                self.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
                return [r[0] if isinstance(r, (list, tuple)) else r["tablename"] for r in self.fetchall()]
            elif db_type == "sqlserver":
                self.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
                return [r[0] for r in self.fetchall()]
            elif db_type == "oracle":
                self.execute("SELECT table_name FROM all_tables WHERE owner=USER ORDER BY table_name")
                return [r[0] for r in self.fetchall()]
            elif db_type == "tdengine":
                self.execute("SHOW TABLES")
                return [r[0] for r in self.fetchall()]
            elif db_type == "pgvector":
                self.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
                return [r[0] if isinstance(r, (list, tuple)) else r["tablename"] for r in self.fetchall()]
            else:
                return []
        except Exception as e:
            print(f"[SqlDriver] get_tables 失败: {e}")
            return []

    def get_table_info(self, table_name: str) -> List[Any]:
        db_type = self.params.get("type", "sqlite")
        try:
            if db_type == "sqlite":
                self.execute(f"PRAGMA table_info('{table_name}')")
            elif db_type in ("mysql", "mariadb", "clickhouse", "doris", "starrocks"):
                self.execute(f"DESCRIBE `{table_name}`")
            elif db_type in ("postgres", "pgvector"):
                self.execute(
                    "SELECT column_name, data_type, is_nullable, column_default "
                    f"FROM information_schema.columns WHERE table_name = '{table_name}' "
                    "ORDER BY ordinal_position"
                )
            elif db_type == "sqlserver":
                self.execute(
                    f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT "
                    f"FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' "
                    "ORDER BY ORDINAL_POSITION"
                )
            elif db_type == "oracle":
                self.execute(
                    f"SELECT column_name, data_type, nullable, data_default "
                    f"FROM all_tab_columns WHERE table_name = UPPER('{table_name}') "
                    "ORDER BY column_id"
                )
            elif db_type == "tdengine":
                self.execute(f"DESCRIBE `{table_name}`")
            else:
                return []
            return self.fetchall()
        except Exception as e:
            print(f"[SqlDriver] get_table_info 失败: {e}")
            return []

    def disconnect(self) -> None:
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
        except Exception:
            pass
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
        except Exception:
            pass
        self.connected = False


# Pandas 分段读取辅助（可选依赖 pandas）
def read_sql_pandas_chunks(
    engine_or_conn, sql: str, chunksize: int = 1000
) -> Generator[Any, None, None]:
    """使用 Pandas read_sql 分段读取，避免一次性加载全部数据到内存。

    Args:
        engine_or_conn: SQLAlchemy engine / 连接对象 或 原生 DBAPI 连接
        sql: SQL 语句
        chunksize: 每段行数

    Yields:
        pandas.DataFrame 分段
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("请安装 pandas: pip install pandas")
    for chunk in pd.read_sql(sql, engine_or_conn, chunksize=chunksize):
        yield chunk
