"""数据库驱动包

自动注册所有已实现的驱动：
SQL 型: sqlite, mysql, postgres, mariadb, sqlserver, oracle, clickhouse, doris, starrocks, tdengine, pgvector
NoSQL: mongodb, redis, etcd, cassandra, hbase, influxdb, neo4j, nebulagraph
向量: milvus, qdrant, chroma, weaviate, pinecone
搜索: elasticsearch, opensearch
"""

from .registry import DriverRegistry, register_driver
from .sql_drivers import SqlDriver
from .nosql_drivers import (
    MongoDriver, RedisDriver, EtcdDriver, Neo4jDriver,
    CassandraDriver, InfluxDBDriver, HBaseDriver,
)
from .vector_drivers import (
    MilvusDriver, QdrantDriver, ChromaDriver, WeaviateDriver, PineconeDriver,
)
from .search_drivers import ElasticsearchDriver
from .opensearch_driver import OpenSearchDriver
from .nebula_driver import NebulaGraphDriver
from .base import BaseDriver

# ---------- SQL 型 ----------
DriverRegistry.register("sqlite", SqlDriver)
DriverRegistry.register("mysql", SqlDriver)
DriverRegistry.register("postgres", SqlDriver)
DriverRegistry.register("mariadb", SqlDriver)
DriverRegistry.register("sqlserver", SqlDriver)
DriverRegistry.register("oracle", SqlDriver)
DriverRegistry.register("clickhouse", SqlDriver)
DriverRegistry.register("doris", SqlDriver)
DriverRegistry.register("starrocks", SqlDriver)
DriverRegistry.register("tdengine", SqlDriver)
DriverRegistry.register("pgvector", SqlDriver)

# ---------- NoSQL ----------
DriverRegistry.register("mongodb", MongoDriver)
DriverRegistry.register("redis", RedisDriver)
DriverRegistry.register("etcd", EtcdDriver)
DriverRegistry.register("neo4j", Neo4jDriver)
DriverRegistry.register("cassandra", CassandraDriver)
DriverRegistry.register("influxdb", InfluxDBDriver)
DriverRegistry.register("hbase", HBaseDriver)

# ---------- 向量数据库 ----------
DriverRegistry.register("milvus", MilvusDriver)
DriverRegistry.register("qdrant", QdrantDriver)
DriverRegistry.register("chroma", ChromaDriver)
DriverRegistry.register("weaviate", WeaviateDriver)
DriverRegistry.register("pinecone", PineconeDriver)

# ---------- 搜索引擎 ----------
DriverRegistry.register("elasticsearch", ElasticsearchDriver)
DriverRegistry.register("opensearch", OpenSearchDriver)

# ---------- 图数据库 ----------
DriverRegistry.register("nebulagraph", NebulaGraphDriver)

__all__ = [
    "DriverRegistry",
    "register_driver",
    "BaseDriver",
    "SqlDriver",
    "list_types",
]


def list_types() -> list:
    return DriverRegistry.list_types()
