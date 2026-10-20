"""API 冒烟测试：验证分段加载、慢SQL标记、IO耗时。

运行前需先启动服务器：
    python -m uvicorn sql_manager.api.server:app --host 127.0.0.1 --port 8124
"""

import json
import sys
import urllib.request

# Windows 控制台默认 GBK，输出中文 message 会乱码，统一切到 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://127.0.0.1:8124"


def post(path, obj):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(obj).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req).read().decode("utf-8"))


def main():
    post("/api/v1/connect", {"node_id": "g1", "params": {"type": "sqlite", "database": ":memory:"}})
    post("/api/v1/sql/execute", {"node_id": "g1", "sql": "CREATE TABLE big(id INTEGER, v TEXT)"})
    post("/api/v1/sql/execute", {
        "node_id": "g1",
        "sql": "INSERT INTO big WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x<250)"
               " SELECT x, 'v' || x FROM c",
    })

    p1 = post("/api/v1/sql/execute", {"node_id": "g1", "sql": "SELECT * FROM big", "page_size": 100, "page": 1})
    print("PAGE1 loaded=%s total=%s has_more=%s io=%s slow=%s" % (
        p1["loaded_rows"], p1["total_rows"], p1["has_more"], p1["io_cost_ms"], p1["is_slow_sql"]))

    p3 = post("/api/v1/sql/execute", {"node_id": "g1", "sql": "SELECT * FROM big", "page_size": 100, "page": 3})
    print("PAGE3 loaded=%s has_more=%s" % (p3["loaded_rows"], p3["has_more"]))

    thr0 = post("/api/v1/sql/execute", {
        "node_id": "g1", "sql": "SELECT * FROM big", "slow_sql_threshold_ms": 0})
    print("THRESHOLD0 slow=%s io=%s" % (thr0["is_slow_sql"], thr0["io_cost_ms"]))

    # 非 SELECT（写操作）
    w = post("/api/v1/sql/execute", {"node_id": "g1", "sql": "INSERT INTO big VALUES(999,'x')"})
    print("WRITE success=%s total_rows=%s" % (w["success"], w["total_rows"]))

    # 不存在的节点
    bad = post("/api/v1/sql/execute", {"node_id": "nope", "sql": "SELECT 1"})
    print("BAD_NODE success=%s message=%s" % (bad["success"], bad["message"]))


if __name__ == "__main__":
    main()
