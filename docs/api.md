# SQL_Manager 局域网转发 API 文档

> 服务基于 FastAPI，启动后访问 `http://<服务器IP>:8000/docs` 可获得交互式文档（Swagger UI）。
> 本文给出每个端点的请求/响应字段与 curl 示例。

## 1. 启动

```bash
cd src
python -m uvicorn sql_manager.api.server:app --host 0.0.0.0 --port 8000
```

- `--host 0.0.0.0` 才会被局域网其他机器访问到；仅监听 `127.0.0.1` 时外部无法连接。
- 交互式文档：`http://<服务器IP>:8000/docs`
- 健康检查：`http://<服务器IP>:8000/api/v1/nodes`

## 2. 通用响应约定

所有 SQL 执行类端点返回 `SqlExecuteResponse`：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `success` | bool | 是否执行成功 |
| `message` | str | 状态描述；失败时为错误原因 |
| `node_id` | str | 实际执行该 SQL 的节点 |
| `sql` | str | 执行的原始 SQL |
| `columns` | list[str] | 结果列名 |
| `rows` | list[list] | **当前页**的数据行（不是全量） |
| `total_rows` | int | 库内统计的总行数 |
| `loaded_rows` | int | 本次实际返回的行数 |
| `has_more` | bool | 是否还有下一页 |
| `page` | int | 当前页码，从 1 开始 |
| `page_size` | int | 每页行数 |
| `io_cost_ms` | float | **IO 耗时（毫秒）** |
| `is_slow_sql` | bool | **是否属于慢SQL**（`io_cost_ms > slow_sql_threshold_ms`） |
| `executed_at` | str | 执行时间（ISO8601） |

> 分页语义：调用方循环 `page = 1, 2, 3...` 直到 `has_more == false`。
> 服务端使用 `LIMIT/OFFSET` 真分页，不会一次性加载全量结果。

## 3. 连接管理

### POST /api/v1/connect

连接一个数据库节点。

请求：

```json
{
  "node_id": "mysql-1",
  "params": {
    "type": "mysql",
    "host": "192.168.1.20",
    "port": 3306,
    "user": "app",
    "password": "secret",
    "database": "orders",
    "charset": "utf8mb4",
    "timeout": 30
  }
}
```

`params.type` 可取 `sqlite` / `mysql` / `postgres` 等；`sqlite` 时用 `database` 传文件路径（`:memory:` 表示内存库）。

响应：

```json
{
  "success": true,
  "message": "连接成功",
  "node_id": "mysql-1",
  "db_info": {"type": "mysql", "tables": ["orders", "items"], "version": "8.0.35"}
}
```

### POST /api/v1/disconnect

```json
{"node_id": "mysql-1"}
```

### GET /api/v1/nodes

列出全部节点及其运行状态。

```json
[
  {
    "node_id": "mysql-1",
    "type": "mysql",
    "host": "192.168.1.20",
    "port": 3306,
    "connected": true,
    "qps": 12.5,
    "avg_io_ms": 8.31,
    "slow_sql_count": 2,
    "last_heartbeat": "2026-10-21T10:00:00"
  }
]
```

## 4. SQL 执行

四种路由策略，任选其一：

| 端点 | 策略 | 说明 |
| --- | --- | --- |
| `POST /api/v1/sql/execute` | `round_robin` | 轮询；`node_id` 为空时自动选节点 |
| `POST /api/v1/sql/execute/balanced` | `dynamic` | **动态规划调度**，按 avg_io / qps / 慢SQL数选最优节点 |
| `POST /api/v1/sql/execute/random` | `random` | 随机 |
| `POST /api/v1/sql/execute/least_conn` | `least_conn` | 选当前 QPS 最低的节点 |

请求体（`SqlExecuteRequest`）：

| 字段 | 类型 | 默认 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `node_id` | str | — | 必填 | 目标节点；`/balanced` 场景可传空串由服务端路由 |
| `sql` | str | — | 必填 | 标准 SQL |
| `page_size` | int | 100 | 1 ≤ n ≤ 10000 | 每页行数 |
| `page` | int | 1 | n ≥ 1 | 页码，从 1 开始 |
| `slow_sql_threshold_ms` | int | 1000 | n ≥ 0 | 慢SQL阈值（毫秒），超过则 `is_slow_sql=true` |

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sql/execute \
  -H "Content-Type: application/json" \
  -d '{
        "node_id": "mysql-1",
        "sql": "SELECT * FROM orders WHERE status = 1",
        "page_size": 100,
        "page": 1,
        "slow_sql_threshold_ms": 500
      }'
```

响应片段：

```json
{
  "success": true,
  "message": "执行成功",
  "node_id": "mysql-1",
  "columns": ["id", "amount", "status"],
  "rows": [[1, 99.5, 1], [2, 20.0, 1]],
  "total_rows": 1024,
  "loaded_rows": 100,
  "has_more": true,
  "page": 1,
  "page_size": 100,
  "io_cost_ms": 12.37,
  "is_slow_sql": false,
  "executed_at": "2026-10-21T10:00:00.123456"
}
```

非 SELECT 语句（INSERT/UPDATE/DELETE/DDL）同样走该端点，返回 `rows` 为空、`total_rows` 为受影响行数。

## 5. 慢SQL监控

### GET /api/v1/slowsql/stats

不传 `node_id`：

```json
{"threshold_ms": 1000.0, "total_records": 42}
```

传 `?node_id=mysql-1`：

```json
{"node_id": "mysql-1", "slow_rate": 0.08, "avg_io_ms": 143.2, "threshold_ms": 1000.0}
```

- `slow_rate` —— 该节点近期慢SQL占比。
- `avg_io_ms` —— 该节点近期平均IO耗时。

## 6. 数据库组

数据库组 = 多个数据库节点的集合，用于提升整体吞吐。

### POST /api/v1/groups

```json
{
  "group_id": "orders-cluster",
  "description": "订单库集群",
  "shard_size": 1000000
}
```

`shard_size` 为**单分片最大行数**，默认 1000000。

### POST /api/v1/groups/{group_id}/nodes

```json
{"group_id": "orders-cluster", "node_id": "mysql-1"}
```

### GET /api/v1/groups/{group_id}/nodes

```json
{"group_id": "orders-cluster", "nodes": ["mysql-1", "mysql-2"]}
```

## 7. 分片

### POST /api/v1/shards/auto

为指定表自动切分分片。**Query 参数**（非 JSON body）。

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `table_name` | str | — | 表名（必填） |
| `group_id` | str | — | 目标组（必填），组内节点会被轮询分配 |
| `total_rows` | int | — | 表总行数（必填） |
| `shard_size` | int | 组配置值 | 单分片最大行数 |
| `strategy` | str | `range` | `range`（范围）或 `hash`（哈希） |

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/shards/auto?table_name=orders&group_id=orders-cluster&total_rows=5000000&shard_size=1000000&strategy=range"
```

响应：

```json
{
  "success": true,
  "table_name": "orders",
  "shard_count": 5,
  "shards": [
    {"shard_id": "orders_shard_1", "node_id": "mysql-1", "strategy": "range",
     "range_start": 0, "range_end": 1000000, "hash_mod": null, "hash_remainder": null}
  ]
}
```

### GET /api/v1/shards

可选 `?table_name=orders` 按表过滤。

### GET /api/v1/shards/locate

按分片键定位数据所在节点。

```
GET /api/v1/shards/locate?table_name=orders&shard_key=10086&strategy=hash
```

```json
{"shard_id": "orders_shard_3", "node_id": "mysql-2", "strategy": "hash"}
```

## 8. 负载均衡与数据同步

### POST /api/v1/rebalance

重置负载均衡状态，丢弃历史慢节点惩罚，下次请求按健康节点重新路由。

```json
{"success": true, "message": "负载均衡已重置，下次请求将按健康节点重新路由"}
```

### POST /api/v1/sync

跨服务器数据同步（生成源组 → 目标组的同步计划）。

请求：

```json
{
  "source_group": "orders-cluster",
  "target_group": "orders-replica",
  "tables": ["orders", "items"]
}
```

响应：

```json
{
  "success": true,
  "message": "组 orders-cluster -> orders-replica 同步计划生成（2 对）",
  "synced_tables": 2,
  "synced_rows": 200000,
  "cost_ms": 3.12
}
```

> 当前实现为**调度计划生成**：由动态规划调度器决定源节点与目标节点的配对及预估传输成本，表行数使用占位值。生产环境需接入 Binlog / CDC 完成实际数据搬运。

### POST /api/v1/schedule/batch

批量查询任务的节点分配（Query 参数）。

```
POST /api/v1/schedule/batch?query_count=100&strategy=dynamic
```

返回长度为 `query_count` 的 `node_id` 数组，`None` 表示无可用节点。

## 9. Python 客户端

```python
from sql_manager.api.client import ApiClient

client = ApiClient(base_url="http://192.168.1.10:8000")

client.connect("mysql-1", {
    "type": "mysql", "host": "192.168.1.20", "port": 3306,
    "user": "app", "password": "secret", "database": "orders",
})

resp = client.execute_sql(
    "SELECT * FROM orders",
    node_id="mysql-1",
    page_size=100,
    page=1,
)
print(resp.is_slow_sql, resp.io_cost_ms, resp.has_more, resp.total_rows)

# 自动路由（动态规划）
resp = client.execute_sql("SELECT 1", balanced=True)

client.create_group("orders-cluster", description="订单库集群", shard_size=1_000_000)
client.add_node_to_group("orders-cluster", "mysql-1")
client.list_shards(table_name="orders")
client.rebalance()
```

## 10. 错误语义

| HTTP | 场景 |
| --- | --- |
| 200 + `success: false` | 节点不可用、SQL 执行错误等（返回 `message` 说明原因） |
| 400 | 组已存在、组内没有可用节点 |
| 404 | 组不存在、未找到匹配分片 |
| 422 | 请求体字段校验失败（`page < 1`、`page_size` 超范围等） |

慢SQL与IO耗时在**成功与失败两种情况下都会返回**（失败时 `io_cost_ms` 反映出错前的耗时）。
