"""SQLite数据库管理工具 - 主程序入口

本文件是应用程序的主入口点,负责:
- 创建QApplication实例
- 初始化主窗口
- 启动事件循环

运行方式:
    python app.py
"""

import sys
from PyQt6.QtWidgets import QApplication
from main_window import DBManager
from version import VERSION


if __name__ == '__main__':
    print(f"正在启动 SQLite 数据库查看工具 v{VERSION}...")
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    db_manager = DBManager()
    db_manager.show()
    # PyQt6中exec_()改为exec()
    sys.exit(app.exec())