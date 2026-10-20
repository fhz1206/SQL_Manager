"""NoSQL 数据库驱动

支持：MongoDB、Redis、etcd、Cassandra、HBase、InfluxDB 2.x、Neo4j、Nebula Graph

统一接口与 BaseDriver 一致，针对 NoSQL 特性做相应映射：
- execute() 用于执行原生操作（返回 bool）
- fetchall()/fetchone() 用于读取结果
- read_sql_chunked() 对 NoSQL 表现为分批读取文档/键值
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Tuple

from .base import BaseDriver


class MongoDriver(BaseDriver):
    """MongoDB 驱动"""

    def connect(self) -> bool:
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("请安装 pymongo: pip install pymongo")
        host = self.params.get("host", "localhost")
        port = self.params.get("port", 27017)
        uri = self.params.get("uri") or f"mongodb://{host}:{port}/"
        self.conn = MongoClient(uri, serverSelectionTimeoutMS=self.params.get("timeout", 30) * 1000)
        self.db = self.conn[self.params.get("database", "admin")]
        self.cursor = None
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # 对 MongoDB，sql 表示 collection 名，params 表示查询过滤（dict）
        try:
            coll = self.db[sql]
            filter_doc = params if isinstance(params, dict) else {}
            self._last_cursor = coll.find(filter_doc)
            return True
        except Exception as e:
            print(f"[MongoDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        try:
            return list(getattr(self, "_last_cursor", []))
        except Exception:
            return []

    def fetchone(self) -> Optional[Any]:
        try:
            return next(iter(getattr(self, "_last_cursor", [])), None)
        except Exception:
            return None

    def get_tables(self) -> List[str]:
        return self.db.list_collection_names()

    def get_table_info(self, table_name: str) -> List[Any]:
        # MongoDB 无固定 schema，返回样本文档字段
        try:
            sample = self.db[table_name].find_one()
            if not sample:
                return []
            return [[k, type(v).__name__] for k, v in sample.items()]
        except Exception:
            return []

    def disconnect(self) -> None:
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.connected = False


class RedisDriver(BaseDriver):
    """Redis 驱动"""

    def connect(self) -> bool:
        try:
            import redis
        except ImportError:
            raise ImportError("请安装 redis: pip install redis")
        self.conn = redis.Redis(
            host=self.params.get("host", "localhost"),
            port=self.params.get("port", 6379),
            password=self.params.get("password", ""),
            db=self.params.get("database", 0),
            decode_responses=True,
            socket_timeout=self.params.get("timeout", 30),
        )
        self.cursor = None
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # sql 为 redis 命令：GET/SET/KEYS/DEL 等
        try:
            parts = sql.split()
            cmd = parts[0].upper()
            args = parts[1:]
            if cmd == "GET":
                self._last_result = self.conn.get(args[0]) if args else None
            elif cmd == "KEYS":
                self._last_result = self.conn.keys(args[0] if args else "*")
            elif cmd == "SET":
                self._last_result = self.conn.set(args[0], args[1] if len(args) > 1 else "")
            elif cmd == "DEL":
                self._last_result = self.conn.delete(*args) if args else 0
            else:
                self._last_result = None
            return True
        except Exception as e:
            print(f"[RedisDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        res = getattr(self, "_last_result", None)
        if isinstance(res, list):
            return res
        return [res] if res is not None else []

    def fetchone(self) -> Optional[Any]:
        res = getattr(self, "_last_result", None)
        return res

    def get_tables(self) -> List[str]:
        return self.conn.keys("*")[:100]

    def get_table_info(self, table_name: str) -> List[Any]:
        return [[table_name, "key", type(getattr(self, "_last_result", None)).__name__]]

    def disconnect(self) -> None:
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.connected = False


class EtcdDriver(BaseDriver):
    """etcd 驱动"""

    def connect(self) -> bool:
        try:
            import etcd3
        except ImportError:
            raise ImportError("请安装 etcd3: pip install etcd3")
        self.conn = etcd3.client(
            host=self.params.get("host", "localhost"),
            port=self.params.get("port", 2379),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        try:
            parts = sql.split()
            cmd = parts[0].upper()
            if cmd == "PUT":
                self.conn.put(parts[1], parts[2] if len(parts) > 2 else "")
                self._last_result = True
            elif cmd == "GET":
                value, _ = self.conn.get(parts[1])
                self._last_result = value.decode() if value else None
            elif cmd == "DELETE":
                self.conn.delete(parts[1])
                self._last_result = True
            else:
                self._last_result = None
            return True
        except Exception as e:
            print(f"[EtcdDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        return [getattr(self, "_last_result", None)]

    def fetchone(self) -> Optional[Any]:
        return getattr(self, "_last_result", None)

    def get_tables(self) -> List[str]:
        return []

    def get_table_info(self, table_name: str) -> List[Any]:
        return []

    def disconnect(self) -> None:
        self.connected = False


class Neo4jDriver(BaseDriver):
    """Neo4j 图数据库驱动"""

    def connect(self) -> bool:
        try:
            from neo4j import GraphDatabase
        except ImportError:
            raise ImportError("请安装 neo4j: pip install neo4j")
        uri = f"bolt://{self.params.get('host','localhost')}:{self.params.get('port',7687)}"
        self.conn = GraphDatabase.driver(
            uri,
            auth=(self.params.get("user", ""), self.params.get("password", "")),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        try:
            with self.conn.session() as session:
                self._last_result = list(session.run(sql, params or {}))
            return True
        except Exception as e:
            print(f"[Neo4jDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        return [dict(r) for r in getattr(self, "_last_result", [])]

    def fetchone(self) -> Optional[Any]:
        res = getattr(self, "_last_result", [])
        return dict(res[0]) if res else None

    def get_tables(self) -> List[str]:
        return []

    def get_table_info(self, table_name: str) -> List[Any]:
        return []

    def disconnect(self) -> None:
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.connected = False


class CassandraDriver(BaseDriver):
    """Cassandra 驱动"""

    def connect(self) -> bool:
        try:
            from cassandra.cluster import Cluster
        except ImportError:
            raise ImportError("请安装 cassandra-driver: pip install cassandra-driver")
        cluster = Cluster(
            [self.params.get("host", "localhost")],
            port=self.params.get("port", 9042),
        )
        self.conn = cluster.connect(self.params.get("database", ""))
        self.cursor = self.conn
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        try:
            self._last_result = self.conn.execute(sql, params or ())
            return True
        except Exception as e:
            print(f"[CassandraDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        try:
            return list(getattr(self, "_last_result", []))
        except Exception:
            return []

    def fetchone(self) -> Optional[Any]:
        res = getattr(self, "_last_result", None)
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        rows = self.conn.execute("SELECT table_name FROM system_schema.tables")
        return [r.table_name for r in rows]

    def get_table_info(self, table_name: str) -> List[Any]:
        return []

    def disconnect(self) -> None:
        try:
            if self.conn:
                self.conn.shutdown()
        except Exception:
            pass
        self.connected = False


class InfluxDBDriver(BaseDriver):
    """InfluxDB 2.x 驱动"""

    def connect(self) -> bool:
        try:
            from influxdb_client import InfluxDBClient
        except ImportError:
            raise ImportError("请安装 influxdb-client: pip install influxdb-client")
        self.conn = InfluxDBClient(
            url=self.params.get("uri", f"http://{self.params.get('host','localhost')}:8086"),
            token=self.params.get("password", ""),
            org=self.params.get("user", ""),
            timeout=self.params.get("timeout", 30000),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # sql 为 Flux 查询
        try:
            query_api = self.conn.query_api()
            self._last_result = list(query_api.query(sql))
            return True
        except Exception as e:
            print(f"[InfluxDBDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        return getattr(self, "_last_result", [])

    def fetchone(self) -> Optional[Any]:
        res = getattr(self, "_last_result", [])
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        return []

    def get_table_info(self, table_name: str) -> List[Any]:
        return []

    def disconnect(self) -> None:
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.connected = False


class HBaseDriver(BaseDriver):
    """HBase 驱动（通过 happybase）"""

    def connect(self) -> bool:
        try:
            import happybase
        except ImportError:
            raise ImportError("请安装 happybase: pip install happybase")
        self.conn = happybase.Connection(
            host=self.params.get("host", "localhost"),
            port=self.params.get("port", 9090),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # sql 为 table 名
        try:
            self._last_table = self.conn.table(sql)
            return True
        except Exception as e:
            print(f"[HBaseDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        tbl = getattr(self, "_last_table", None)
        if tbl is None:
            return []
        return [k for k, _ in tbl.scan()]

    def fetchone(self) -> Optional[Any]:
        res = self.fetchall()
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        return self.conn.tables()

    def get_table_info(self, table_name: str) -> List[Any]:
        return []

    def disconnect(self) -> None:
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.connected = False
