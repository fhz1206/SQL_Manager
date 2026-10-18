"""数据库连接对话框

用于连接不同类型的数据库，包括SQLite、MySQL和PostgreSQL
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                            QPushButton, QLineEdit, QGroupBox, QFormLayout,
                            QMessageBox, QCheckBox, QSpinBox)
from PyQt6.QtGui import QIcon
from ..core.config import ICON_PATH
from ..core.db_manager import test_connection
from .custom_dialogs import show_error, show_info


class DatabaseConnectDialog(QDialog):
    """数据库连接对话框

    提供界面让用户连接不同类型的数据库
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('DatabaseConnectDialog')
        self.setWindowTitle("🔗 连接数据库")
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumWidth(500)
        self.setMaximumWidth(600)
        self.setModal(True)

        # 创建布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)
        self.setLayout(main_layout)

        # 标题
        title_label = QLabel("🔗 连接数据库")
        title_label.setObjectName("connectTitle")
        main_layout.addWidget(title_label)

        desc_label = QLabel("选择数据库类型并输入连接参数")
        desc_label.setObjectName("connectDesc")
        main_layout.addWidget(desc_label)

        # 数据库类型选择
        type_group = QGroupBox("数据库类型")
        type_layout = QHBoxLayout()
        type_group.setLayout(type_layout)

        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["SQLite", "MySQL", "PostgreSQL"])
        self.db_type_combo.currentIndexChanged.connect(self._on_db_type_changed)
        type_layout.addWidget(self.db_type_combo)

        main_layout.addWidget(type_group)

        # SQLite连接参数
        self.sqlite_group = QGroupBox("SQLite连接参数")
        sqlite_form = QFormLayout()
        sqlite_form.setSpacing(8)
        self.sqlite_group.setLayout(sqlite_form)

        self.db_path_input = QLineEdit()
        self.db_path_input.setPlaceholderText("选择SQLite数据库文件...")
        sqlite_form.addRow("数据库文件:", self.db_path_input)

        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(self._browse_db_file)
        sqlite_form.addRow("", browse_btn)

        # MySQL连接参数
        self.mysql_group = QGroupBox("MySQL连接参数")
        mysql_form = QFormLayout()
        mysql_form.setSpacing(8)
        self.mysql_group.setLayout(mysql_form)
        self.mysql_group.setVisible(False)

        self.mysql_host_input = QLineEdit()
        self.mysql_host_input.setPlaceholderText("localhost")
        mysql_form.addRow("服务器地址:", self.mysql_host_input)

        self.mysql_port_input = QSpinBox()
        self.mysql_port_input.setRange(1, 65535)
        self.mysql_port_input.setValue(3306)
        mysql_form.addRow("端口:", self.mysql_port_input)

        self.mysql_user_input = QLineEdit()
        self.mysql_user_input.setPlaceholderText("用户名")
        mysql_form.addRow("用户名:", self.mysql_user_input)

        self.mysql_pass_input = QLineEdit()
        self.mysql_pass_input.setPlaceholderText("密码")
        self.mysql_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        mysql_form.addRow("密码:", self.mysql_pass_input)

        self.mysql_db_input = QLineEdit()
        self.mysql_db_input.setPlaceholderText("数据库名")
        mysql_form.addRow("数据库名:", self.mysql_db_input)

        self.mysql_charset_input = QLineEdit()
        self.mysql_charset_input.setPlaceholderText("utf8mb4")
        mysql_form.addRow("字符集:", self.mysql_charset_input)

        # PostgreSQL连接参数
        self.postgres_group = QGroupBox("PostgreSQL连接参数")
        postgres_form = QFormLayout()
        postgres_form.setSpacing(8)
        self.postgres_group.setLayout(postgres_form)
        self.postgres_group.setVisible(False)

        self.postgres_host_input = QLineEdit()
        self.postgres_host_input.setPlaceholderText("localhost")
        postgres_form.addRow("服务器地址:", self.postgres_host_input)

        self.postgres_port_input = QSpinBox()
        self.postgres_port_input.setRange(1, 65535)
        self.postgres_port_input.setValue(5432)
        postgres_form.addRow("端口:", self.postgres_port_input)

        self.postgres_user_input = QLineEdit()
        self.postgres_user_input.setPlaceholderText("用户名")
        postgres_form.addRow("用户名:", self.postgres_user_input)

        self.postgres_pass_input = QLineEdit()
        self.postgres_pass_input.setPlaceholderText("密码")
        self.postgres_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        postgres_form.addRow("密码:", self.postgres_pass_input)

        self.postgres_db_input = QLineEdit()
        self.postgres_db_input.setPlaceholderText("数据库名")
        postgres_form.addRow("数据库名:", self.postgres_db_input)

        # 添加数据库组到主布局
        main_layout.addWidget(self.sqlite_group)
        main_layout.addWidget(self.mysql_group)
        main_layout.addWidget(self.postgres_group)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self._test_connection)
        btn_layout.addWidget(test_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        connect_btn = QPushButton("连接")
        connect_btn.setObjectName("successButton")
        connect_btn.clicked.connect(self._accept_connection)
        btn_layout.addWidget(connect_btn)

        main_layout.addLayout(btn_layout)

        # 初始化
        self._on_db_type_changed(0)

    def _on_db_type_changed(self, index):
        """当数据库类型变化时"""
        db_type = self.db_type_combo.currentText().lower()

        if db_type == "sqlite":
            self.sqlite_group.setVisible(True)
            self.mysql_group.setVisible(False)
            self.postgres_group.setVisible(False)
        elif db_type == "mysql":
            self.sqlite_group.setVisible(False)
            self.mysql_group.setVisible(True)
            self.postgres_group.setVisible(False)
        elif db_type == "postgresql":
            self.sqlite_group.setVisible(False)
            self.mysql_group.setVisible(False)
            self.postgres_group.setVisible(True)

    def _browse_db_file(self):
        """浏览数据库文件"""
        from PyQt6.QtWidgets import QFileDialog
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择SQLite数据库", "", "SQLite数据库 (*.db *.sqlite *.sqlite3);;所有文件 (*)")
        if file_name:
            self.db_path_input.setText(file_name)

    def _test_connection(self):
        """测试数据库连接"""
        db_type = self.db_type_combo.currentText().lower()
        connection_params = self._get_connection_params(db_type)

        if not connection_params:
            show_error("错误", "请填写所有必填字段", self)
            return

        result = test_connection(db_type, connection_params)

        if result["success"]:
            db_info = result.get("db_info", {})
            tables = db_info.get("tables", [])
            version = db_info.get("version", "Unknown")

            message = f"连接成功!\n\n数据库类型: {db_type}\n版本: {version}\n表数量: {len(tables)}"
            if tables:
                message += f"\n表: {', '.join(tables[:5])}"
                if len(tables) > 5:
                    message += "..."

            show_info("连接测试", message, self)
        else:
            show_error("连接测试失败", result["message"], self)

    def _get_connection_params(self, db_type):
        """获取连接参数"""
        if db_type == "sqlite":
            db_path = self.db_path_input.text().strip()
            if not db_path:
                return None
            return {"database": db_path}

        elif db_type == "mysql":
            host = self.mysql_host_input.text().strip()
            user = self.mysql_user_input.text().strip()
            password = self.mysql_pass_input.text()
            database = self.mysql_db_input.text().strip()
            port = self.mysql_port_input.value()
            charset = self.mysql_charset_input.text().strip() or "utf8mb4"

            if not all([host, user, database]):
                return None

            return {
                "host": host,
                "user": user,
                "password": password,
                "database": database,
                "port": port,
                "charset": charset
            }

        elif db_type == "postgresql":
            host = self.postgres_host_input.text().strip()
            user = self.postgres_user_input.text().strip()
            password = self.postgres_pass_input.text()
            database = self.postgres_db_input.text().strip()
            port = self.postgres_port_input.value()

            if not all([host, user, database]):
                return None

            return {
                "host": host,
                "user": user,
                "password": password,
                "database": database,
                "port": port
            }

        return None

    def _accept_connection(self):
        """接受连接"""
        db_type = self.db_type_combo.currentText().lower()
        connection_params = self._get_connection_params(db_type)

        if not connection_params:
            show_error("错误", "请填写所有必填字段", self)
            return

        # 测试连接
        result = test_connection(db_type, connection_params)
        if not result["success"]:
            show_error("连接失败", result["message"], self)
            return

        # 保存连接参数
        self.connection_params = {
            "type": db_type,
            "params": connection_params
        }

        self.accept()

    def get_connection_params(self):
        """获取连接参数

        Returns:
            dict: 包含类型和参数的字典
        """
        return getattr(self, "connection_params", None)
