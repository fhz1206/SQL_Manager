# SQL_Manager 架构设计文档

> 本文说明 SQL_Manager 的分层结构、模块职责、关键数据流与并发模型。
> 接口细节见 [api.md](api.md)，问题修复记录见 [changelog.md](changelog.md)。

## 1. 设计目标

1. **单机可用**：桌面客户端可独立连接本地 SQLite / MySQL / PostgreSQL。
2. **局域网可协作**：同一局域网内其他机器通过 REST 接口操控数据库。
3. **多节点高吞吐**：多台数据库组成"数据库组"，支持分片、负载均衡与跨节点同步。
4. **大结果集不卡顿**：所有查询强制分段加载，绝不一次性把全量结果读进内存。
5. **慢SQL可观测**：每次执行都返回 `is_slow_sql` 布尔值与 `io_cost_ms` IO 耗时。

## 2. 目录结构

```
SQL_Manager/
├── src/sql_manager/
│   ├── app.py                    # 桌面客户端入口
│   ├── core/                     # 与传输层无关的领域逻辑
│   │   ├── config.py             # 全局配置（分页大小、路径、超时）
│   │   ├── db_manager.py         # 数据库连接管理 + 线程安全 + 分页执行
│   │   ├── version.py            # 版本元信息
│   │   ├── shard_manager.py      # 分片元数据与路由
│   │   └── scheduler.py          # 慢SQL控制器 + 动态规划调度 + 负载均衡
│   ├── api/                      # 局域网转发层
│   │   ├── models.py             # Pydantic 请求/响应契约
│   │   ├── pool.py               # 多节点连接池 + 统计 + 路由
│   │   ├── server.py             # FastAPI 应用与端点
│   │   └── client.py             # Python 客户端封装
│   ├── drivers/                  # 数据库驱动族
│   │   ├── base.py               # BaseDriver 抽象基类
│   │   ├── registry.py           # DriverRegistry
│   │   ├── sql_drivers.py        # 关系型 + Pandas 分段读取
│   │   ├── nosql_drivers.py      # MongoDB/Redis/etcd/Neo4j/Cassandra/InfluxDB/HBase
│   │   ├── vector_drivers.py     # Milvus/Qdrant/Chroma/Weaviate/Pinecone
│   │   ├── search_drivers.py     # Elasticsearch
│   │   ├── opensearch_driver.py  # OpenSearch
│   │   ├── nebula_driver.py      # Nebula Graph
│   │   └── orm_adapters.py       # SQLAlchemy/Django/Peewee/Tortoise
│   └── ui/                       # PyQt6 表现层
│       ├── main_window.py        # 主窗口 + 异步任务
│       ├── components.py         # SearchLineEdit / VirtualTableWidget / TableModel
│       ├── dialogs.py            # 查询向导
│       ├── db_connect_dialog.py  # 网络库连接对话框
│       ├── custom_dialogs.py     # 自定义消息框
│       └── style.css             # 统一主题
├── docs/                         # 文档
├── tests/                        # 测试
└── .github/workflows/ci.yml
```

### 2.1 分层依赖规则

依赖必须自上而下，禁止反向与跨层跳跃：

```
ui      →  core, api, drivers
api     →  core
core    →  （不依赖 api）
drivers →  （不依赖 core/api）
```

`core/scheduler.py` 需要 `NodeStatus` 结构，历史实现曾 `from sql_manager.api.models import NodeStatus` 构成倒依赖，现已改为容错导入（`try: from ..api.models import ... except: NodeStatus = Any`），保证 `core` 可独立于 `api` 使用。

所有包内导入统一使用**相对导入**（`from .models import ...` / `from ..core.x import ...`），避免包名或运行目录变化时 `ImportError`。

## 3. core 层

### 3.1 `db_manager.DatabaseConnection`

统一的关系型连接封装，支持 `sqlite` / `mysql` / `postgres`。

关键设计：

- **`_lock: threading.RLock`** —— 连接对象会被主线程（树形浏览、刷新）与后台线程（`QRunnable` 任务）同时访问，所有游标操作与事务操作均在锁内执行。
- **`self.cursor` 仅供主线程使用**。后台线程必须调用 **`new_cursor()`** 获取独立游标。原因：`cursor.execute()` 会覆盖同一游标的上一个结果集，两个线程交替使用共享游标会导致结果错乱（实测会取到对方的行）。
- **`execute_page(sql, page_size, offset)`** —— 将原 SQL 包装为 `SELECT * FROM (<sql>) _paged LIMIT ? OFFSET ?`，只取一页。
- **`count_rows(sql)`** —— 以 `SELECT COUNT(*) FROM (<sql>) _cnt` 在库内统计总行数，不拉取任何数据行。

### 3.2 `scheduler.py`

| 组件 | 职责 |
| --- | --- |
| `SlowSqlController` | 记录每个节点的慢SQL次数、慢率、平均IO；`classify()` 返回 `(is_slow, io_cost_ms)` |
| `DynamicPlannerScheduler` | 动态规划/贪心混合调度；`_node_cost` = `avg_io_ms + qps*5 + slow_sql_count*50` |
| `LoadBalancer` | `round_robin` / `random` / `least_conn` / `dynamic` 四种策略 |

调度节点的字段名为 `node_id`（不是 `id`）。历史实现误用 `n.id` 会直接抛 `AttributeError`。

### 3.3 `shard_manager.py`

- 范围分片：`range_start`（含）~ `range_end`（不含）。
- 哈希分片：`md5(key) % hash_mod == hash_remainder`。`hash_mod <= 0` 会被跳过，避免除零。
- `auto_shard_table()` 对 `shard_size <= 0`、空 `node_ids` 均已做边界防护。

## 4. api 层

### 4.1 `pool.ConnectionPool`

维护 `_nodes: Dict[str, NodeStats]` 与 `_connections: Dict[str, DatabaseConnection]`，全部操作在 `self._lock` 保护下。

`execute_sql()` 是核心，**必须真分页**：

```
1. page/page_size 边界校正（page ≥ 1，page_size ≥ 1）
2. 开独立游标
3. SELECT/WITH/VALUES:
     a. 独立游标执行 COUNT(*) 得 total_rows
     b. 独立游标执行 SELECT * FROM (base) _paged LIMIT n OFFSET m
     c. has_more = (offset + loaded_rows) < total_rows
4. PRAGMA/EXPLAIN: 原样执行（无法包装为子查询）
5. 其他: 执行并 commit，返回 rowcount
6. 计算 io_cost_ms，写入节点统计，返回 is_slow_sql
```

**反模式（已修复）**：先 `fetchall()` 拿全量再切片。数据量大时内存与 IO 都会失控，违背"分段加载"要求。

### 4.2 `server.py`

FastAPI 应用，CORS 全开（局域网场景），监听 `0.0.0.0:8000` 供局域网访问。

全局组件：`pool` / `slow_controller` / `scheduler` / `balancer` / `shard_manager` / `_groups` / `_group_nodes`。

心跳线程每 10 秒探活一次。探活**必须使用独立游标**——早期实现复用 `conn.cursor` 执行 `SELECT 1`，会清空正在进行的查询结果集，导致健康节点被误判为离线。

## 5. ui 层

### 5.1 线程模型

- 所有耗时 DB 操作封装为 `QRunnable`（`QueryTask` / `TableDataTask`），交由 `QThreadPool.globalInstance()` 执行。
- 后台线程**只**通过 `pyqtSignal` 传回数据，**绝不直接触碰控件**。
- 槽函数在主线程执行，负责更新模型与标签。

### 5.2 表格模型

`TableModel` 继承 `QAbstractTableModel`：

- `_display_cache[(row, col)]` 缓存 `str()` 转换结果，避免视图反复调用 `data()` 时重复转换。
- 交替行背景色必须用 `QColor(r, g, b, a)` 构造。**`QColor('rgba(255,255,255,0.30)')` 是 CSS 语法，Qt 不支持，会得到无效颜色。**
- `add_data()` 追加数据后需清空显示缓存。

### 5.3 滚动加载

`VirtualTableWidget` 用 `_scroll_timer`（120ms 单次）节流滚动到底事件。

`_loading_more` 锁不能在触发回调后立即释放——加载是异步的，立即释放会导致滚动到底时重复触发。实现为：延时兜底解锁 + 数据到达后调用 `finish_loading()` 提前解锁。

## 6. 主题与样式

所有颜色集中在 `ui/style.css`，**不得在 Python 代码里写 `setStyleSheet` 硬编码色值**。

| 用途 | 色值 |
| --- | --- |
| 主色 | `#0984e3` |
| 主色 hover / pressed | `#0773c7` / `#0566b3` |
| 成功 | `#00b894` |
| 危险 | `#e74c3c` |
| 主文字 / 次文字 | `#2c3e50` / `#636e72` |
| 边框 | `rgba(255,255,255,0.65)` |

样式通过 `setObjectName` 与 CSS 选择器绑定：`#successButton`、`#dangerButton`、`#wizardButton`、`#formatButton`、`#countLabel`、`#titleLabel`、`#sqlEditor`、`QDialog#QueryWizardDialog`、`QDialog#DatabaseConnectDialog`、`QDialog#customMessageBox` 等。新增控件时务必同步在 `style.css` 中补齐对应选择器。

### 6.1 资源路径

`icon.ico` 与 `style.css` 位于 `ui/` 目录，而 `config.py` 位于 `core/` 目录，因此：

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))     # core/
UI_DIR   = os.path.normpath(os.path.join(BASE_DIR, os.pardir, 'ui'))
ICON_PATH = os.path.join(UI_DIR, 'icon.ico')
CSS_PATH  = os.path.join(UI_DIR, 'style.css')
```

**路径写错会导致启动即卡死**：样式加载失败时若弹模态 `QMessageBox`，构造函数会永久阻塞，无头环境、CI 与自动化启动全部挂起。样式加载失败必须降级为状态栏提示，不得阻塞启动。

## 7. 数据流示例

### 7.1 桌面端查询表数据

```
用户点击树节点
  → show_table_data(table)
  → TableDataTask(conn, table, PAGE_SIZE, 0) 提交线程池
      后台：new_cursor() → COUNT(*) → LIMIT/OFFSET → fetchall(仅一页)
  → 信号 query_finished(columns, total_rows, rows, error)
  → 主线程槽 on_finished()
      → TableModel.set_data(...) / add_data(...)
      → 更新"共 N 行（已加载 M 行）"标签
```

### 7.2 局域网执行 SQL

```
局域网客户端 POST /api/v1/sql/execute/balanced
  → _execute_with_strategy(req, "dynamic")
  → balancer.select(nodes, "dynamic")   # 依据 avg_io/qps/slow_count 选节点
  → pool.execute_sql(node_id, sql, page_size, page)
      → 独立游标 COUNT + LIMIT/OFFSET
      → io_cost_ms = (perf_counter - start) * 1000
      → is_slow_sql = io_cost_ms > slow_sql_threshold_ms
  → slow_controller.record(...)
  → 返回 { columns, rows, total_rows, has_more, io_cost_ms, is_slow_sql, ... }
```
