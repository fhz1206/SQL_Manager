"""CI 步骤本地复现：验证 UI 冒烟、驱动注册、API 路由。

运行: python tests/ci_local_check.py
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def check_ui():
    from PyQt6.QtWidgets import QApplication
    from sql_manager.ui import (main_window, components, dialogs,
                                 custom_dialogs, db_connect_dialog)
    from sql_manager.core import config, version
    app = QApplication([])
    win = main_window.DBManager()
    win.show()
    print("UI smoke OK, version:", version.VERSION)
    app.quit()


def check_drivers():
    from sql_manager.drivers import list_types
    types = list_types()
    assert len(types) >= 26, "驱动注册数量不足: %s" % len(types)
    print("Driver types OK:", len(types))


def check_api():
    from sql_manager.api.server import app
    paths = {r.path for r in app.routes}
    required = {
        "/api/v1/connect", "/api/v1/disconnect", "/api/v1/nodes",
        "/api/v1/sql/execute", "/api/v1/sql/execute/balanced",
        "/api/v1/slowsql/stats", "/api/v1/groups", "/api/v1/shards",
        "/api/v1/sync", "/api/v1/rebalance",
    }
    missing = required - paths
    assert not missing, "缺少端点: %s" % missing
    print("API routes OK:", len(paths))


if __name__ == "__main__":
    check_drivers()
    check_api()
    check_ui()
    print("=== ALL CI CHECKS PASSED ===")
