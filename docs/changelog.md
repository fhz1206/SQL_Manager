# 更新日志 / Bug 修复记录

## v2.1.0 —— Bug 大清理与文档补全

### 修复：并发与资源

| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `core/db_manager.py` | `DatabaseConnection` 全局共享单个 `self.cursor`，主线程与后台 `QRunnable` 任务交替使用会互相覆盖结果集 | 引入 `threading.RLock`；新增 `new_cursor()` 返回独立游标；`execute/fetchall/fetchone/commit/rollback` 全部加锁 |
| `ui/main_window.py` | `QueryTask` / `TableDataTask` 复用 `self.conn.cursor` | 改用 `conn.new_cursor()`，并在 `finally` 中关闭游标 |
| `api/server.py` | 心跳探活复用 `conn.cursor` 执行 `SELECT 1`，清空进行中的结果集，导致健康节点被误判离线（实测 n1–n4 全部掉线） | 探活改用独立游标，失败才置离线 |

### 修复：分段加载

| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `api/pool.py` | `execute_sql` 先 `fetchall()` 取全量再切片，内存与 IO 不可控 | 改为库内 `COUNT(*)` + `LIMIT/OFFSET` 真分页；`page`/`page_size` 边界校正（page ≥ 1，page_size ≥ 1） |
| `ui/main_window.py` | `QueryTask` 一次性拉取全部结果；且把"当前页行数"当作总行数，导致 `has_more` 恒为 false、"加载更多"功能失效 | `QueryTask` 新增 `page_size`/`offset` 参数；总行数改用库内 COUNT |
| `ui/main_window.py` | "加载全部"分支的 `has_more` 判定依赖用户是否点击确认 | 改为始终只加载第一页并提示，其余通过"加载更多"按需拉取 |
| `core/db_manager.py` | 无分页执行能力 | 新增 `execute_page(sql, page_size, offset)` 与 `count_rows(sql)` |

### 修复：崩溃类

| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `core/scheduler.py` | 使用 `n.id` 取节点 ID，但 `NodeStatus` 字段名为 `node_id` → `AttributeError`（4 处：`schedule_nodes` × 3、`schedule_sync` × 1） | 全部改为 `n.node_id` |
| `core/shard_manager.py` | `digest % shard.hash_mod` 在 `hash_mod = 0` 时 `ZeroDivisionError` | 跳过 `hash_mod <= 0` 的非法分片 |
| `core/shard_manager.py` | `auto_shard_table` 在 `node_ids` 为空或 `shard_size <= 0` 时取模/整除除零 | 增加边界防护，空节点列表直接返回空列表 |
| `ui/components.py` | `QColor('rgba(255, 255, 255, 0.30)')` 使用 CSS 语法，Qt 的 `QColor` 不支持，得到无效颜色 | 改为 `QColor(255, 255, 255, 76)` |
| `ui/components.py` | `_loading_more` 在触发回调后立即释放，异步加载未返回即解锁，滚动到底会重复触发加载 | 改为延时兜底解锁 + 新增 `finish_loading()`，数据到达时提前解锁 |

### 修复：导入与架构

| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `ui/dialogs.py` | 残留旧绝对导入 `from custom_dialogs import show_warning` → `ModuleNotFoundError` | 改为 `from .custom_dialogs import show_warning` |
| `ui/main_window.py` | 残留旧绝对导入 `from custom_dialogs import show_info` | 改为相对导入 |
| `drivers/*.py`（9 个文件） | 使用 `from sql_manager.drivers.base import BaseDriver` 绝对导入，包名或运行目录变化即 `ImportError` | 统一改为相对导入 `from .base import BaseDriver` |
| `api/pool.py`、`api/client.py` | 同上，使用 `sql_manager.*` 绝对导入 | 统一改为相对导入 |
| `core/scheduler.py` | 反向依赖 `api.models`（core 不应依赖 api） | 改为容错导入 `try: from ..api.models import NodeStatus / except: NodeStatus = Any` |
| `api/client.py` | 顶层 `import requests`，未安装时整个包导入失败 | 改为惰性导入，并在 `ApiClient.__init__` 中校验并给出安装提示 |

### 修复：API 逻辑
| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `api/server.py` | `sync_data` 用 `vars(n)` 处理 pydantic v2 模型取字段，不可靠 | 直接复用 `NodeStatus` 实例，并只调用一次 `_nodes_status()` |
| `api/server.py` | `rebalance()` 重建的 scheduler 只赋给局部变量，全局 `scheduler` 未更新，策略不生效 | 加 `global` 声明，并同步 `balancer.scheduler` |
| `api/server.py` | `locate_shard` 的 `shard_key: Any` 无法生成请求校验 | 改为 `str` |
| `api/server.py` | 阻塞型 DB 操作使用同步 `def` 端点，会阻塞事件循环 | 保持现状（连接池内有锁保护），后续可迁 `def` → `async def` + 线程池 |

### 其他

- `requirements.txt` 补充 `requests>=2.31.0`（`api/client.py` 依赖）。
- 新增 `tests/smoke_api.py` 冒烟测试，覆盖分段加载、`has_more`、`is_slow_sql`、`io_cost_ms`。
- 新增 `docs/architecture.md`、`docs/api.md`、`docs/changelog.md`。

### 验证结果

服务器首次成功启动并实测通过：

```
PAGE1     loaded=100 total=250 has_more=True  io=0.15 slow=False
PAGE3     loaded=50            has_more=False
THRESHOLD0                    slow=True  io=0.11
WRITE      success=True total_rows=1
BAD_NODE   success=False message=节点 nope 不可用
```

全部 28 个 Python 文件语法检查通过。

### 修复：资源路径（严重，启动即卡死）

目录重构后 `core/config.py` 的 `BASE_DIR` 指向 `core/`，而 `icon.ico` 与 `style.css` 实际位于 `ui/` 目录：

| 文件 | 问题 | 修复 |
| --- | --- | --- |
| `core/config.py` | `ICON_PATH` / `CSS_PATH` 指向 `core/`，资源全部找不到 | 新增 `UI_DIR`，路径改为 `ui/` 目录 |
| `ui/main_window.py` | 样式加载失败时弹出**模态** `QMessageBox`，构造函数永久阻塞——无头环境、CI、自动化启动全部挂死 | 改为记录错误并在状态栏提示，不阻塞启动 |

该问题导致 `DBManager()` 实例化时卡在模态对话框上，进程无法退出。

### 文档

- 新增 `docs/architecture.md`：分层结构与依赖规则、模块职责、线程模型、分页实现、主题规范、数据流示例。
- 新增 `docs/api.md`：全部 REST 端点的请求/响应字段表、错误语义、curl 与 Python 示例。
- 新增 `docs/changelog.md`（本文档）。
- `README.md`：新增文档索引、准确的驱动清单（26 项）、运行方式、已知限制。
- `.github/workflows/ci.yml`：更新为新 `src/` 结构；新增驱动注册与 API 路由断言；新增 `tests/ci_local_check.py` 本地复现脚本。

### 已知限制

- 26 个数据库驱动仅验证了**可导入**与注册正确，未做真实连接测试（对应第三方库未安装）。
- `POST /api/v1/sync` 目前只生成同步**计划**（源/目标节点配对与预估成本），表行数使用占位值 100000；实际数据搬运需接入 Binlog / CDC。
- 桌面客户端尚未接入 `api/client.py`（无"通过局域网 API 连接"入口与服务器地址输入框）。
- `core/db_manager.DatabaseConnection` 目前只支持 sqlite / mysql / postgres，未委托给 `DriverRegistry`，因此 26 种驱动暂不能在现有 UI 中直接选用。

---

## v2.0.0 —— 架构重构

- 项目结构标准化：代码拆分为 `ui/` / `core/` / `api/` / `drivers/` 四层，新增 `docs/`、`tests/`、`.github/`。
- 新增局域网转发 API（FastAPI）：连接管理、SQL 执行、负载均衡、慢SQL检测、数据库组、分片、跨节点同步。
- 新增 26 种数据库驱动：SQL 型、NoSQL、向量库、搜索引擎、图数据库、ORM 适配器。
- 新增分片管理器与动态规划调度器。
- 新增 3D/2D 可交互网页展示（`docs/web/index.html`）。
- UI 统一颜色系统（`ui/style.css`），移除全部内联 `setStyleSheet` 硬编码。
- 性能优化：查询后台线程化、显示文本缓存、滚动节流、搜索防抖、分段加载。

## v2.1.1 及更早

见 `git log`。
