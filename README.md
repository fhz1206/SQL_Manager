# SQL_Manager · 数据库管理平台

单机桌面 SQL 管理器 → 局域网多人联网分布式数据库管理平台的演进版本。

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | 架构设计：分层结构、模块职责、线程模型、数据流、设计约束与反模式 |
| [docs/api.md](docs/api.md) | 局域网转发 API：全部端点的请求/响应字段、错误语义、curl 与 Python 示例 |
| [docs/changelog.md](docs/changelog.md) | 更新日志 / Bug 修复记录与已知限制 |
| [docs/web/index.html](docs/web/index.html) | 3D/2D 可交互网页展示 |

## 项目结构（标准化）

```
SQL_Manager/
├── src/sql_manager/
│   ├── __init__.py
│   ├── app.py                    # 桌面客户端入口 (PyQt6)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # 全局配置 (分页、Pragma、超时、并发)
│   │   ├── db_manager.py         # 数据库连接管理 (SQLite/MySQL/PostgreSQL)
│   │   ├── version.py            # 版本信息
│   │   ├── shard_manager.py      # 数据库分片管理器 (范围/哈希分片、单分片行数可配)
│   │   └── scheduler.py          # 动态规划调度器、慢SQL控制器、负载均衡器
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py             # 桌面客户端 HTTP API 客户端
│   │   ├── models.py             # Pydantic 请求/响应模型
│   │   ├── pool.py               # 多节点连接池 + 负载均衡路由 + 慢SQL/IO统计
│   │   └── server.py             # FastAPI 局域网转发服务器 (REST)
│   ├── drivers/
│   │   ├── __init__.py           # 驱动注册表 (自动注册全部驱动)
│   │   ├── base.py               # BaseDriver 抽象基类
│   │   ├── registry.py           # DriverRegistry 注册/创建驱动
│   │   ├── sql_drivers.py        # SQLite/MySQL/MariaDB/PostgreSQL/SQL Server/Oracle/
│   │   │                         # ClickHouse/Doris/StarRocks/TDengine/PGVector
│   │   │                         # + Pandas read_sql 分段读取辅助
│   │   ├── nosql_drivers.py      # MongoDB/Redis/etcd/Neo4j/Cassandra/InfluxDB/HBase
│   │   ├── vector_drivers.py     # Milvus/Qdrant/Chroma/Weaviate/Pinecone
│   │   ├── search_drivers.py     # Elasticsearch
│   │   ├── opensearch_driver.py  # OpenSearch
│   │   ├── nebula_driver.py      # Nebula Graph
│   │   └── orm_adapters.py       # SQLAlchemy/Django ORM/Peewee/Tortoise ORM 分段适配器
│   └── ui/
│       ├── __init__.py
│       ├── main_window.py        # 主窗口 (异步查询、分页、防抖搜索)
│       ├── components.py         # SearchLineEdit / VirtualTableWidget / TableModel
│       ├── dialogs.py            # 查询向导
│       ├── db_connect_dialog.py  # 多库连接对话框
│       ├── custom_dialogs.py     # 自定义消息框
│       ├── style.css             # 统一主题 (液态玻璃，统一颜色系统)
│       └── icon.ico
├── docs/
│   ├── architecture.md           # 架构设计（分层、数据流、并发模型）
│   ├── api.md                    # 局域网转发 API 文档
│   ├── changelog.md              # 更新日志 / Bug 修复记录
│   └── web/
│       └── index.html            # 3D/2D 可交互网页展示 (Three.js)
├── tests/
│   └── smoke_api.py              # API 冒烟测试（分页/慢SQL/IO耗时）
├── .github/workflows/ci.yml
└── requirements.txt
```

## 核心能力

### 1. UI 优化与统一颜色
- `style.css` 统一颜色系统：主色 `#0984e3`、成功 `#00b894`、危险 `#e74c3c`、文字 `#2c3e50`、边框 `rgba(255,255,255,0.65)`。
- 移除 `dialogs.py`、`db_connect_dialog.py`、`custom_dialogs.py`、`main_window.py` 中全部内联 `setStyleSheet` 硬编码，统一走表。
- 液态玻璃主题（半透明 + 细描边 + 大圆角）、玻璃药丸按钮、玻璃表格/树/选项卡/输入框/滚动条。

### 2. 性能优化
- 查询改为后台线程异步执行（`QThreadPool` + `pyqtSignal`），主线程不再阻塞。
- `TableModel.data()` 增加 `str()` 显示文本缓存，避免视图频繁重复转换。
- 滚动加载增加 120ms 节流，防止到底重复触发。
- 树搜索增加 150ms 防抖，避免每次按键遍历全树。
- SQL 查询与表数据加载均支持分段加载（`LIMIT/OFFSET`），不再一次性全量 `fetchall()`。

### 3. 局域网联网（多负载均衡 + 转发 API）
- `src/sql_manager/api/server.py`：FastAPI 服务器，监听 `0.0.0.0:8000`，局域网内其他机器可通过 HTTP 调用。
- `src/sql_manager/api/client.py`：桌面客户端 HTTP 客户端，封装 `/api/v1/*`。
- 接口：
  - `POST /api/v1/connect` 连接节点
  - `POST /api/v1/disconnect` 断开节点
  - `GET /api/v1/nodes` 节点状态
  - `POST /api/v1/sql/execute` 指定节点执行
  - `POST /api/v1/sql/execute/balanced` 动态调度自动路由
  - `POST /api/v1/sql/execute/random` / `/least_conn` 其他策略
  - `POST /api/v1/groups` 创建数据库组
  - `POST /api/v1/shards/auto` 自动分片
  - `POST /api/v1/sync` 跨组数据同步
  - `GET /api/v1/slowsql/stats` 慢SQL统计

### 4. 慢SQL管控（is_slow_sql + IO耗时）
- `SqlExecuteResponse` 返回字段：
  - `is_slow_sql: bool` — 是否超过慢SQL阈值
  - `io_cost_ms: float` — IO耗时(ms)
  - `page` / `page_size` / `has_more` — 分段加载
- `SlowSqlController` 记录每节点慢SQL次数、平均 IO、慢率，供调度器惩罚。

### 5. 数据库分片 / 分组 / 负载均衡
- `ShardManager`：范围分片 / 哈希分片，单分片最大行数 (`shard_size`) 可配，自动将表切分到多节点。
- `DynamicPlannerScheduler`：动态规划/贪心调度，按节点 `avg_io_ms`、`qps`、`slow_sql_count` 计算代价，最小化总 IO 耗时。
- `LoadBalancer`：`round_robin` / `random` / `least_conn` / `dynamic` 四种策略。

### 6. 跨服务器数据同步
- `POST /api/v1/sync`：基于调度器生成源组 → 目标组的同步计划（源/目标节点对、预估成本），生产环境可接入 Binlog/CDC。

### 7. 多数据库类型支持（26 种）
SQL 型：SQLite、MySQL、PostgreSQL、MariaDB、SQL Server、Oracle、ClickHouse、Apache Doris、StarRocks、TDengine、PGVector  
NoSQL：MongoDB、Redis、etcd、Neo4j、Cassandra、InfluxDB 2.x、HBase  
向量：Milvus、Qdrant、Chroma、Weaviate、Pinecone  
搜索：Elasticsearch、OpenSearch  
图：Nebula Graph  
ORM：SQLAlchemy、Django ORM、Peewee、Tortoise ORM（分段适配器）

完整注册类型（`sql_manager.drivers.list_types()` 返回 26 项）：
`cassandra, chroma, clickhouse, doris, elasticsearch, etcd, hbase, influxdb, mariadb, milvus, mongodb, mysql, nebulagraph, neo4j, opensearch, oracle, pgvector, pinecone, postgres, qdrant, redis, sqlite, sqlserver, starrocks, tdengine, weaviate`

Pandas `read_sql` 分段读取：`drivers/sql_drivers.py::read_sql_pandas_chunks()`，`chunksize` 控制每段行数，避免一次性全量加载。

## 运行方式

### 桌面客户端
```bash
cd src
python -m sql_manager.app
```

### API 服务器（局域网转发）
```bash
cd src
python -m uvicorn sql_manager.api.server:app --host 0.0.0.0 --port 8000
```
访问 `http://<服务器IP>:8000/docs` 查看交互式 API 文档。

### 3D/2D 网页展示
直接打开 `docs/web/index.html`（使用 Three.js 渲染数据库拓扑，支持点击节点查看详情、模拟慢SQL、负载再均衡、数据同步、SQL查询等）。

### 冒烟测试
```bash
# 1) 先启动服务器
cd src && python -m uvicorn sql_manager.api.server:app --host 127.0.0.1 --port 8124
# 2) 另开终端运行
python tests/smoke_api.py
```

## 依赖
```
PyQt6>=6.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
python-multipart>=0.0.6
requests>=2.31.0
```
各数据库驱动按需安装（如 `pymysql`、`psycopg2-binary`、`pymongo`、`redis` 等）。所有第三方驱动均为**惰性导入**，未安装时不影响程序启动，仅在实际连接时提示。

## 已知限制

- 26 个驱动仅验证了可导入与注册正确，未做真实连接测试（对应第三方库未安装）。
- `POST /api/v1/sync` 目前只生成同步**计划**（源/目标节点配对与预估成本），实际数据搬运需接入 Binlog / CDC。
- 桌面客户端尚未接入 `api/client.py`（无"通过局域网 API 连接"入口与服务器地址输入框）。
- `core/db_manager.DatabaseConnection` 目前只支持 sqlite / mysql / postgres，尚未委托给 `DriverRegistry`，因此 26 种驱动暂不能在现有 UI 中直接选用。
