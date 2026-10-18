"""向量数据库驱动

支持：Milvus、Qdrant、Chroma、Weaviate、Pinecone

统一接口与 BaseDriver 一致，针对向量检索特性：
- execute(sql)：sql 为集合/索引名，params 为查询向量或过滤条件
- fetchall()：返回检索结果列表
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional, Tuple

from sql_manager.drivers.base import BaseDriver


class MilvusDriver(BaseDriver):
    """Milvus 向量数据库驱动"""

    def connect(self) -> bool:
        try:
            from pymilvus import MilvusClient
        except ImportError:
            raise ImportError("请安装 pymilvus: pip install pymilvus")
        uri = self.params.get("uri") or f"http://{self.params.get('host','localhost')}:{self.params.get('port',19530)}"
        self.conn = MilvusClient(uri=uri)
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # sql = collection 名，params = {'vector': [...], 'limit': N, 'filter': '...'}
        try:
            if not isinstance(params, dict):
                params = {}
            vector = params.get("vector")
            limit = params.get("limit", 10)
            filter_expr = params.get("filter", "")
            kwargs = {"collection_name": sql, "limit": limit}
            if vector is not None:
                kwargs["data"] = [vector]
            if filter_expr:
                kwargs["filter"] = filter_expr
            self._last_result = self.conn.search(**kwargs) if vector is not None else self.conn.query(**kwargs)
            return True
        except Exception as e:
            print(f"[MilvusDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        return getattr(self, "_last_result", [])

    def fetchone(self) -> Optional[Any]:
        res = getattr(self, "_last_result", [])
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        return self.conn.list_collections()

    def get_table_info(self, table_name: str) -> List[Any]:
        try:
            return [self.conn.describe_collection(table_name)]
        except Exception:
            return []

    def disconnect(self) -> None:
        self.connected = False


class QdrantDriver(BaseDriver):
    """Qdrant 向量数据库驱动"""

    def connect(self) -> bool:
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            raise ImportError("请安装 qdrant-client: pip install qdrant-client")
        self.conn = QdrantClient(
            host=self.params.get("host", "localhost"),
            port=self.params.get("port", 6333),
            api_key=self.params.get("password", ""),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        try:
            if not isinstance(params, dict):
                params = {}
            vector = params.get("vector")
            limit = params.get("limit", 10)
            self._last_result = self.conn.search(
                collection_name=sql,
                query_vector=vector or [],
                limit=limit,
            )
            return True
        except Exception as e:
            print(f"[QdrantDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        return getattr(self, "_last_result", [])

    def fetchone(self) -> Optional[Any]:
        res = getattr(self, "_last_result", [])
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        return [c.name for c in self.conn.get_collections().collections]

    def get_table_info(self, table_name: str) -> List[Any]:
        try:
            return [self.conn.get_collection(table_name)]
        except Exception:
            return []

    def disconnect(self) -> None:
        self.connected = False


class ChromaDriver(BaseDriver):
    """Chroma 向量数据库驱动"""

    def connect(self) -> bool:
        try:
            import chromadb
        except ImportError:
            raise ImportError("请安装 chromadb: pip install chromadb")
        self.conn = chromadb.PersistentClient(path=self.params.get("database", "./chroma_db"))
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        try:
            if not isinstance(params, dict):
                params = {}
            collection = self.conn.get_or_create_collection(sql)
            query_embeddings = params.get("vector")
            n_results = params.get("limit", 10)
            self._last_result = collection.query(
                query_embeddings=[query_embeddings] if query_embeddings is not None else None,
                n_results=n_results,
            )
            return True
        except Exception as e:
            print(f"[ChromaDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        return [getattr(self, "_last_result", {})]

    def fetchone(self) -> Optional[Any]:
        res = getattr(self, "_last_result", None)
        return res

    def get_tables(self) -> List[str]:
        return [c.name for c in self.conn.list_collections()]

    def get_table_info(self, table_name: str) -> List[Any]:
        return [[table_name, "collection"]]

    def disconnect(self) -> None:
        self.connected = False


class WeaviateDriver(BaseDriver):
    """Weaviate 向量数据库驱动"""

    def connect(self) -> bool:
        try:
            import weaviate
        except ImportError:
            raise ImportError("请安装 weaviate-client: pip install weaviate-client")
        url = f"http://{self.params.get('host','localhost')}:{self.params.get('port',8080)}"
        self.conn = weaviate.Client(url)
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        # sql = class 名，params = {'near_vector': {...}, 'limit': N}
        try:
            if not isinstance(params, dict):
                params = {}
            query = self.conn.query.get(sql, ["*"])
            if params.get("near_vector"):
                query = query.with_near_vector(params["near_vector"])
            query = query.with_limit(params.get("limit", 10))
            self._last_result = query.do()
            return True
        except Exception as e:
            print(f"[WeaviateDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        return [getattr(self, "_last_result", {})]

    def fetchone(self) -> Optional[Any]:
        return getattr(self, "_last_result", None)

    def get_tables(self) -> List[str]:
        try:
            schema = self.conn.schema.get()
            return [c["class"] for c in schema.get("classes", [])]
        except Exception:
            return []

    def get_table_info(self, table_name: str) -> List[Any]:
        return [[table_name, "class"]]

    def disconnect(self) -> None:
        self.connected = False


class PineconeDriver(BaseDriver):
    """Pinecone 向量数据库驱动"""

    def connect(self) -> bool:
        try:
            import pinecone
        except ImportError:
            raise ImportError("请安装 pinecone-client: pip install pinecone-client")
        pinecone.init(
            api_key=self.params.get("password", ""),
            environment=self.params.get("database", ""),
        )
        self.connected = True
        return True

    def execute(self, sql: str, params: Optional[Tuple] = None) -> bool:
        try:
            if not isinstance(params, dict):
                params = {}
            index = pinecone.Index(sql)
            vector = params.get("vector", [])
            top_k = params.get("limit", 10)
            self._last_result = index.query(vector=vector, top_k=top_k)
            return True
        except Exception as e:
            print(f"[PineconeDriver] 执行失败: {e}")
            return False

    def fetchall(self) -> List[Any]:
        res = getattr(self, "_last_result", {})
        return res.get("matches", []) if isinstance(res, dict) else []

    def fetchone(self) -> Optional[Any]:
        res = self.fetchall()
        return res[0] if res else None

    def get_tables(self) -> List[str]:
        try:
            return pinecone.list_indexes()
        except Exception:
            return []

    def get_table_info(self, table_name: str) -> List[Any]:
        return [[table_name, "index"]]

    def disconnect(self) -> None:
        self.connected = False
