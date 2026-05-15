
import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QInputDialog, QTabWidget, QLabel, QLineEdit,
                             QComboBox, QFileDialog, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QMenu, QAction, QStatusBar, QToolBar, QTextEdit, QFrame,
                             QGridLayout, QSizePolicy, QAbstractItemView,
                             QDialog, QCheckBox, QGroupBox, QDialogButtonBox, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QKeySequence, QFont, QColor, QPalette, QPixmap, QPainter

# 现代化样式表
STYLESHEET = """
QMainWindow {
    background-color: #f5f6fa;
}

QToolBar {
    background-color: #2c3e50;
    border: none;
    padding: 6px 8px;
    spacing: 6px;
}

QToolBar QToolButton {
    background-color: #34495e;
    color: #ecf0f1;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: bold;
    min-width: 80px;
}

QToolBar QToolButton:hover {
    background-color: #3d566e;
}

QToolBar QToolButton:pressed {
    background-color: #1a252f;
}

QStatusBar {
    background-color: #2c3e50;
    color: #ecf0f1;
    font-size: 12px;
    padding: 4px 10px;
}

QSplitter::handle {
    background-color: #dcdde1;
    width: 3px;
}

QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    padding: 4px;
    font-size: 13px;
    outline: none;
}

QTreeWidget::item {
    padding: 5px 2px;
    border-radius: 4px;
}

QTreeWidget::item:selected {
    background-color: #3498db;
    color: #ffffff;
}

QTreeWidget::item:hover {
    background-color: #ebf5fb;
}

QTreeWidget::branch {
    background-color: transparent;
}

QTabWidget::pane {
    border: 1px solid #dcdde1;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
}

QTabBar::tab {
    background-color: #ecf0f1;
    color: #2c3e50;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 13px;
    font-weight: bold;
    min-width: 90px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
}

QTabBar::tab:hover:!selected {
    background-color: #dfe6e9;
}

QTableWidget {
    background-color: #ffffff;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    gridline-color: #f0f0f0;
    font-size: 13px;
    selection-background-color: #3498db;
    selection-color: #ffffff;
    outline: none;
}

QTableWidget::item {
    padding: 6px 10px;
}

QTableWidget::item:selected {
    background-color: #3498db;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #f8f9fa;
    color: #2c3e50;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #3498db;
    font-weight: bold;
    font-size: 13px;
}

QTextEdit {
    background-color: #2c3e50;
    color: #ecf0f1;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    padding: 10px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 14px;
    selection-background-color: #3498db;
    selection-color: #ffffff;
}

QPushButton {
    background-color: #3498db;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: bold;
    min-width: 70px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:pressed {
    background-color: #1f6da8;
}

QPushButton#dangerButton {
    background-color: #e74c3c;
}

QPushButton#dangerButton:hover {
    background-color: #c0392b;
}

QPushButton#successButton {
    background-color: #27ae60;
}

QPushButton#successButton:hover {
    background-color: #219a52;
}

QLineEdit {
    background-color: #ffffff;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #2c3e50;
    selection-background-color: #3498db;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border-color: #3498db;
}

QLineEdit::placeholder {
    color: #b2bec3;
}

QComboBox {
    background-color: #ffffff;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    color: #2c3e50;
    min-width: 100px;
}

QComboBox:focus {
    border-color: #3498db;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #dcdde1;
    border-radius: 4px;
    selection-background-color: #3498db;
    selection-color: #ffffff;
    outline: none;
}

QLabel {
    color: #2c3e50;
    font-size: 13px;
}

QLabel#titleLabel {
    color: #2c3e50;
    font-size: 15px;
    font-weight: bold;
}

QLabel#searchIcon {
    color: #b2bec3;
    font-size: 16px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    padding: 6px 0px;
}

QMenu::item {
    padding: 8px 30px;
    color: #2c3e50;
}

QMenu::item:selected {
    background-color: #3498db;
    color: #ffffff;
    border-radius: 4px;
}

QMenu::separator {
    height: 1px;
    background-color: #ecf0f1;
    margin: 4px 10px;
}

QScrollBar:vertical {
    background-color: #f5f6fa;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #b2bec3;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #636e72;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #f5f6fa;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #b2bec3;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #636e72;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #2c3e50;
    font-size: 14px;
}
"""


class SearchLineEdit(QLineEdit):
    """带搜索图标的输入框"""
    def __init__(self, placeholder='搜索...', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(36)


class QueryWizardDialog(QDialog):
    """查询向导对话框 - 帮助新手构建SQL查询"""
    def __init__(self, conn, current_table=None, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.current_table = current_table
        self.generated_sql = ''
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('🔍 查询向导')
        self.setMinimumSize(720, 750)
        self.setStyleSheet('''
            QDialog {
                background-color: #f5f6fa;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                color: #2c3e50;
                border: 2px solid #dcdde1;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
            QCheckBox {
                color: #2c3e50;
                font-size: 13px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid #b2bec3;
            }
            QCheckBox::indicator:checked {
                background-color: #3498db;
                border-color: #3498db;
            }
            QComboBox {
                min-height: 32px;
                font-size: 13px;
            }
            QLineEdit {
                min-height: 32px;
                font-size: 13px;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                min-height: 34px;
                font-size: 13px;
            }
        ''')

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 16, 16, 16)
        self.setLayout(main_layout)

        # 标题
        title_label = QLabel('🔍 查询向导 - 轻松构建查询')
        title_label.setStyleSheet('font-size: 18px; font-weight: bold; color: #2c3e50;')
        main_layout.addWidget(title_label)

        desc_label = QLabel('按照步骤选择表、列和条件，自动生成 SQL 查询语句')
        desc_label.setStyleSheet('font-size: 12px; color: #636e72; margin-bottom: 6px;')
        main_layout.addWidget(desc_label)

        # ===== 步骤1: 选择表 =====
        step1_group = QGroupBox('步骤1: 选择要查询的表')
        step1_layout = QHBoxLayout()
        step1_layout.setContentsMargins(10, 6, 10, 6)
        step1_group.setLayout(step1_layout)

        self.table_combo = QComboBox()
        self.table_combo.setMinimumHeight(34)
        self._load_tables()
        self.table_combo.currentTextChanged.connect(self._on_table_changed)
        step1_layout.addWidget(self.table_combo)

        main_layout.addWidget(step1_group)

        # ===== 步骤2: 选择列 =====
        step2_group = QGroupBox('步骤2: 选择要查询的列')
        step2_layout = QVBoxLayout()
        step2_layout.setContentsMargins(10, 6, 10, 6)
        step2_group.setLayout(step2_layout)

        # 全选/取消全选
        select_all_layout = QHBoxLayout()
        select_all_btn = QPushButton('全选')
        select_all_btn.setFixedSize(70, 32)
        select_all_btn.clicked.connect(self._select_all_columns)
        deselect_all_btn = QPushButton('取消全选')
        deselect_all_btn.setFixedSize(80, 32)
        deselect_all_btn.clicked.connect(self._deselect_all_columns)
        select_all_layout.addWidget(select_all_btn)
        select_all_layout.addWidget(deselect_all_btn)
        select_all_layout.addStretch()
        step2_layout.addLayout(select_all_layout)

        # 列选择区域（使用滚动区域）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(80)
        scroll_area.setMaximumHeight(130)
        scroll_area.setStyleSheet('''
            QScrollArea {
                border: 1px solid #dcdde1;
                border-radius: 6px;
                background-color: #ffffff;
            }
        ''')

        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout()
        self.columns_layout.setSpacing(16)
        self.columns_widget.setLayout(self.columns_layout)
        scroll_area.setWidget(self.columns_widget)
        step2_layout.addWidget(scroll_area)

        main_layout.addWidget(step2_group)

        # ===== 步骤3: 设置筛选条件 =====
        step3_group = QGroupBox('步骤3: 设置筛选条件（可选）')
        step3_layout = QVBoxLayout()
        step3_layout.setContentsMargins(10, 6, 10, 6)
        step3_layout.setSpacing(8)
        step3_group.setLayout(step3_layout)

        # 筛选条件行
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)

        filter_row.addWidget(QLabel('列:'))
        self.filter_column_combo = QComboBox()
        self.filter_column_combo.setMinimumWidth(120)
        self.filter_column_combo.setMinimumHeight(34)
        filter_row.addWidget(self.filter_column_combo)

        filter_row.addWidget(QLabel('条件:'))
        self.filter_op_combo = QComboBox()
        self.filter_op_combo.addItems([
            '等于 (=)',
            '不等于 (!=)',
            '大于 (>)',
            '大于等于 (>=)',
            '小于 (<)',
            '小于等于 (<=)',
            '包含 (LIKE)',
            '以...开头',
            '以...结尾',
            '为空 (IS NULL)',
            '不为空 (IS NOT NULL)',
        ])
        self.filter_op_combo.setMinimumWidth(140)
        self.filter_op_combo.setMinimumHeight(34)
        self.filter_op_combo.currentIndexChanged.connect(self._on_operator_changed)
        filter_row.addWidget(self.filter_op_combo)

        filter_row.addWidget(QLabel('值:'))
        self.filter_value_input = QLineEdit()
        self.filter_value_input.setPlaceholderText('输入筛选值...')
        self.filter_value_input.setMinimumWidth(150)
        self.filter_value_input.setMinimumHeight(34)
        filter_row.addWidget(self.filter_value_input)

        step3_layout.addLayout(filter_row)

        # 第二个筛选条件
        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(10)

        self.and_radio = QCheckBox('并且 (AND)')
        self.or_radio = QCheckBox('或者 (OR)')
        self.and_radio.stateChanged.connect(lambda: self.or_radio.setChecked(False) if self.and_radio.isChecked() else None)
        self.or_radio.stateChanged.connect(lambda: self.and_radio.setChecked(False) if self.or_radio.isChecked() else None)
        filter_row2.addWidget(self.and_radio)
        filter_row2.addWidget(self.or_radio)
        filter_row2.addStretch()

        step3_layout.addLayout(filter_row2)

        # 第二行条件
        filter_row3 = QHBoxLayout()
        filter_row3.setSpacing(10)

        filter_row3.addWidget(QLabel('列:'))
        self.filter_column_combo2 = QComboBox()
        self.filter_column_combo2.setMinimumWidth(120)
        self.filter_column_combo2.setMinimumHeight(34)
        filter_row3.addWidget(self.filter_column_combo2)

        filter_row3.addWidget(QLabel('条件:'))
        self.filter_op_combo2 = QComboBox()
        self.filter_op_combo2.addItems([
            '等于 (=)',
            '不等于 (!=)',
            '大于 (>)',
            '大于等于 (>=)',
            '小于 (<)',
            '小于等于 (<=)',
            '包含 (LIKE)',
            '以...开头',
            '以...结尾',
            '为空 (IS NULL)',
            '不为空 (IS NOT NULL)',
        ])
        self.filter_op_combo2.setMinimumWidth(140)
        self.filter_op_combo2.setMinimumHeight(34)
        self.filter_op_combo2.currentIndexChanged.connect(self._on_operator_changed2)
        filter_row3.addWidget(self.filter_op_combo2)

        filter_row3.addWidget(QLabel('值:'))
        self.filter_value_input2 = QLineEdit()
        self.filter_value_input2.setPlaceholderText('输入筛选值...')
        self.filter_value_input2.setMinimumWidth(150)
        self.filter_value_input2.setMinimumHeight(34)
        filter_row3.addWidget(self.filter_value_input2)

        step3_layout.addLayout(filter_row3)

        main_layout.addWidget(step3_group)

        # ===== 步骤4: 排序 =====
        step4_group = QGroupBox('步骤4: 排序（可选）')
        step4_layout = QHBoxLayout()
        step4_layout.setContentsMargins(10, 6, 10, 6)
        step4_group.setLayout(step4_layout)

        step4_layout.addWidget(QLabel('排序列:'))
        self.order_column_combo = QComboBox()
        self.order_column_combo.setMinimumWidth(120)
        self.order_column_combo.setMinimumHeight(34)
        step4_layout.addWidget(self.order_column_combo)

        step4_layout.addWidget(QLabel('排序方式:'))
        self.order_dir_combo = QComboBox()
        self.order_dir_combo.addItems(['升序 (ASC)', '降序 (DESC)'])
        self.order_dir_combo.setMinimumWidth(120)
        self.order_dir_combo.setMinimumHeight(34)
        step4_layout.addWidget(self.order_dir_combo)

        step4_layout.addStretch()
        main_layout.addWidget(step4_group)

        # ===== 预览SQL =====
        preview_group = QGroupBox('生成的 SQL 语句')
        preview_layout = QVBoxLayout()
        preview_layout.setContentsMargins(10, 6, 10, 6)
        preview_group.setLayout(preview_layout)

        self.sql_preview = QTextEdit()
        self.sql_preview.setReadOnly(True)
        self.sql_preview.setMinimumHeight(40)
        self.sql_preview.setMaximumHeight(65)
        self.sql_preview.setStyleSheet('''
            QTextEdit {
                background-color: #2c3e50;
                color: #2ecc71;
                border: 1px solid #dcdde1;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }
        ''')
        preview_layout.addWidget(self.sql_preview)

        main_layout.addWidget(preview_group)

        # ===== 按钮 =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        preview_btn = QPushButton('👁 预览SQL')
        preview_btn.setMinimumHeight(36)
        preview_btn.setMinimumWidth(90)
        preview_btn.clicked.connect(self._generate_sql)
        btn_layout.addWidget(preview_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton('取消')
        cancel_btn.setMinimumHeight(36)
        cancel_btn.setMinimumWidth(70)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        execute_btn = QPushButton('▶ 执行查询')
        execute_btn.setObjectName('successButton')
        execute_btn.setMinimumHeight(36)
        execute_btn.setMinimumWidth(100)
        execute_btn.setStyleSheet('''
            QPushButton {
                background-color: #27ae60;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 22px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
                min-height: 36px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        ''')
        execute_btn.clicked.connect(self._execute_query)
        btn_layout.addWidget(execute_btn)

        main_layout.addLayout(btn_layout)

        # 初始化列信息
        self._on_table_changed(self.table_combo.currentText())

    def _load_tables(self):
        """加载所有表名"""
        self.table_combo.clear()
        if not self.conn:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()
            for table in tables:
                self.table_combo.addItem(table[0])
            # 如果有当前表，默认选中
            if self.current_table:
                idx = self.table_combo.findText(self.current_table)
                if idx >= 0:
                    self.table_combo.setCurrentIndex(idx)
        except Exception:
            pass

    def _on_table_changed(self, table_name):
        """当选择的表变化时，更新列信息"""
        self._load_columns(table_name)
        self._generate_sql()

    def _load_columns(self, table_name):
        """加载指定表的列信息"""
        # 清除旧的列复选框
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 清除下拉框
        self.filter_column_combo.clear()
        self.filter_column_combo2.clear()
        self.order_column_combo.clear()

        if not self.conn or not table_name:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            # 创建列复选框
            col_widget = QWidget()
            col_inner = QVBoxLayout()
            col_inner.setSpacing(4)
            col_widget.setLayout(col_inner)

            self.column_checks = []
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_pk = '🔑 ' if col[5] else ''
                check = QCheckBox(f'{is_pk}{col_name} ({col_type})')
                check.setChecked(True)  # 默认全选
                check.col_name = col_name
                check.stateChanged.connect(self._generate_sql)
                self.column_checks.append(check)
                col_inner.addWidget(check)

            self.columns_layout.addWidget(col_widget)

            # 更新筛选列下拉框
            for col in columns:
                self.filter_column_combo.addItem(col[1])
                self.filter_column_combo2.addItem(col[1])
                self.order_column_combo.addItem(col[1])

        except Exception:
            pass

    def _select_all_columns(self):
        """全选列"""
        for check in self.column_checks:
            check.setChecked(True)

    def _deselect_all_columns(self):
        """取消全选列"""
        for check in self.column_checks:
            check.setChecked(False)

    def _on_operator_changed(self, idx):
        """当操作符变化时，控制值输入框的启用状态"""
        # IS NULL 和 IS NOT NULL 不需要输入值
        is_null_op = idx in (9, 10)
        self.filter_value_input.setEnabled(not is_null_op)
        if is_null_op:
            self.filter_value_input.clear()
            self.filter_value_input.setPlaceholderText('此条件无需输入值')
        else:
            self.filter_value_input.setPlaceholderText('输入筛选值...')
        self._generate_sql()

    def _on_operator_changed2(self, idx):
        """当第二个操作符变化时"""
        is_null_op = idx in (9, 10)
        self.filter_value_input2.setEnabled(not is_null_op)
        if is_null_op:
            self.filter_value_input2.clear()
            self.filter_value_input2.setPlaceholderText('此条件无需输入值')
        else:
            self.filter_value_input2.setPlaceholderText('输入筛选值...')
        self._generate_sql()

    def _build_condition(self, column, op_idx, value):
        """构建单个筛选条件"""
        ops = ['=', '!=', '>', '>=', '<', '<=', 'LIKE', 'LIKE', 'LIKE', 'IS NULL', 'IS NOT NULL']
        op = ops[op_idx] if op_idx < len(ops) else '='

        if op == 'IS NULL':
            return f'"{column}" IS NULL'
        elif op == 'IS NOT NULL':
            return f'"{column}" IS NOT NULL'
        elif op == 'LIKE' and op_idx == 7:  # 以...开头
            return f'"{column}" LIKE \'{value}%\''
        elif op == 'LIKE' and op_idx == 8:  # 以...结尾
            return f'"{column}" LIKE \'%{value}\''
        elif op == 'LIKE':  # 包含
            return f'"{column}" LIKE \'%{value}%\''
        else:
            return f'"{column}" {op} \'{value}\''

    def _generate_sql(self):
        """生成SQL语句"""
        table_name = self.table_combo.currentText()
        if not table_name:
            self.sql_preview.setPlainText('')
            return ''

        # 选择的列
        selected_cols = []
        for check in getattr(self, 'column_checks', []):
            if check.isChecked():
                selected_cols.append(f'"{check.col_name}"')

        if not selected_cols:
            selected_cols = ['*']

        # 构建SELECT
        sql = f'SELECT {", ".join(selected_cols)} FROM "{table_name}"'

        # 构建WHERE
        conditions = []
        filter_col = self.filter_column_combo.currentText()
        if filter_col:
            op_idx = self.filter_op_combo.currentIndex()
            value = self.filter_value_input.text()
            # IS NULL/IS NOT NULL 或有值时才添加条件
            if op_idx in (9, 10) or value:
                conditions.append(self._build_condition(filter_col, op_idx, value))

        # 第二个条件
        if self.and_radio.isChecked() or self.or_radio.isChecked():
            filter_col2 = self.filter_column_combo2.currentText()
            if filter_col2:
                op_idx2 = self.filter_op_combo2.currentIndex()
                value2 = self.filter_value_input2.text()
                if op_idx2 in (9, 10) or value2:
                    cond2 = self._build_condition(filter_col2, op_idx2, value2)
                    connector = 'AND' if self.and_radio.isChecked() else 'OR'
                    conditions.append(f'{connector} {cond2}')

        if conditions:
            sql += f' WHERE {" ".join(conditions)}'

        # 构建ORDER BY
        order_col = self.order_column_combo.currentText()
        if order_col:
            order_dir = 'ASC' if self.order_dir_combo.currentIndex() == 0 else 'DESC'
            sql += f' ORDER BY "{order_col}" {order_dir}'

        self.sql_preview.setPlainText(sql)
        self.generated_sql = sql
        return sql

    def _execute_query(self):
        """执行查询"""
        sql = self._generate_sql()
        if not sql:
            QMessageBox.warning(self, '警告', '请先选择表和列')
            return
        self.generated_sql = sql
        self.accept()


class DBManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_db = None
        self.conn = None
        self.current_table = None
        self.all_table_data = []  # 存储完整表数据用于搜索
        self.table_columns = []   # 存储表列信息
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SQLite 数据库管理工具')
        self.setGeometry(80, 80, 1300, 780)
        self.setStyleSheet(STYLESHEET)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 创建工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 打开数据库按钮
        open_db_action = QAction('📂 打开数据库', self)
        open_db_action.triggered.connect(self.open_database)
        toolbar.addAction(open_db_action)

        toolbar.addSeparator()

        # 新建数据库按钮
        new_db_action = QAction('➕ 新建数据库', self)
        new_db_action.triggered.connect(self.create_database)
        toolbar.addAction(new_db_action)

        toolbar.addSeparator()

        # 关闭数据库按钮
        close_db_action = QAction('✖ 关闭数据库', self)
        close_db_action.triggered.connect(self.close_database)
        toolbar.addAction(close_db_action)

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 创建主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(3)
        main_layout.addWidget(splitter)

        # ========== 左侧面板 - 数据库对象浏览器 ==========
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(6)
        left_panel.setLayout(left_layout)

        # 左侧标题
        left_title = QLabel('🗄️ 数据库对象')
        left_title.setObjectName('titleLabel')
        left_layout.addWidget(left_title)

        # 搜索框 - 过滤数据库对象树
        self.tree_search_input = SearchLineEdit('🔍 搜索表名...')
        self.tree_search_input.textChanged.connect(self.filter_db_tree)
        left_layout.addWidget(self.tree_search_input)

        # 数据库对象树
        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderLabels(['数据库对象'])
        self.db_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.db_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.db_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.db_tree.setIndentation(20)
        self.db_tree.setAnimated(True)
        left_layout.addWidget(self.db_tree)

        splitter.addWidget(left_panel)

        # ========== 右侧面板 - 数据表和SQL编辑器 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(0)
        right_panel.setLayout(right_layout)

        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)

        # ========== 数据表选项卡 ==========
        self.table_tab = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(6, 6, 6, 6)
        table_layout.setSpacing(8)
        self.table_tab.setLayout(table_layout)

        # 搜索栏区域
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(10, 6, 10, 6)
        search_layout.setSpacing(10)
        search_frame.setLayout(search_layout)

        # 当前表标签
        self.current_table_label = QLabel('📋 当前表: 无')
        self.current_table_label.setObjectName('titleLabel')
        search_layout.addWidget(self.current_table_label)

        search_layout.addStretch()

        # 搜索列选择
        search_layout.addWidget(QLabel('搜索列:'))
        self.search_column_combo = QComboBox()
        self.search_column_combo.addItem('所有列')
        self.search_column_combo.setMinimumWidth(120)
        search_layout.addWidget(self.search_column_combo)

        # 搜索关键词输入
        self.data_search_input = SearchLineEdit('🔍 输入关键词搜索数据...')
        self.data_search_input.setMinimumWidth(250)
        self.data_search_input.textChanged.connect(self.search_in_table)
        search_layout.addWidget(self.data_search_input)

        # 清除搜索按钮
        clear_search_btn = QPushButton('清除')
        clear_search_btn.setFixedWidth(60)
        clear_search_btn.clicked.connect(self.clear_data_search)
        search_layout.addWidget(clear_search_btn)

        table_layout.addWidget(search_frame)

        # 表格控件
        self.table_widget = QTableWidget()
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_table_context_menu)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f8f9fa;
            }
        """)
        table_layout.addWidget(self.table_widget)

        # 底部操作栏
        table_action_layout = QHBoxLayout()
        table_action_layout.setSpacing(10)

        self.row_count_label = QLabel('共 0 行')
        self.row_count_label.setStyleSheet('color: #636e72; font-size: 12px;')
        table_action_layout.addWidget(self.row_count_label)

        table_action_layout.addStretch()

        query_wizard_btn = QPushButton('🔍 查询向导')
        query_wizard_btn.setObjectName('queryWizardButton')
        query_wizard_btn.setStyleSheet('''
            QPushButton#queryWizardButton {
                background-color: #8e44ad;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
                min-width: 90px;
            }
            QPushButton#queryWizardButton:hover {
                background-color: #7d3c98;
            }
            QPushButton#queryWizardButton:pressed {
                background-color: #6c3483;
            }
        ''')
        query_wizard_btn.clicked.connect(self.open_query_wizard)
        table_action_layout.addWidget(query_wizard_btn)

        refresh_btn = QPushButton('🔄 刷新')
        refresh_btn.setObjectName('successButton')
        refresh_btn.clicked.connect(self.refresh_current_table)
        table_action_layout.addWidget(refresh_btn)

        table_layout.addLayout(table_action_layout)

        self.tab_widget.addTab(self.table_tab, '📊 数据表')

        # ========== SQL编辑器选项卡 ==========
        self.sql_tab = QWidget()
        sql_layout = QVBoxLayout()
        sql_layout.setContentsMargins(6, 6, 6, 6)
        sql_layout.setSpacing(8)
        self.sql_tab.setLayout(sql_layout)

        # SQL编辑器标签
        sql_title = QLabel('💻 SQL 查询编辑器')
        sql_title.setObjectName('titleLabel')
        sql_layout.addWidget(sql_title)

        # SQL编辑器
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText('输入 SQL 查询语句...\n\n例如: SELECT * FROM table_name WHERE id > 10')
        self.sql_editor.setMinimumHeight(150)
        sql_layout.addWidget(self.sql_editor)

        # 执行按钮行
        sql_btn_layout = QHBoxLayout()
        sql_btn_layout.setSpacing(10)

        execute_button = QPushButton('▶ 执行查询')
        execute_button.setObjectName('successButton')
        execute_button.clicked.connect(self.execute_sql)
        execute_button.setMinimumHeight(38)
        sql_btn_layout.addWidget(execute_button)

        clear_sql_btn = QPushButton('🗑 清空')
        clear_sql_btn.clicked.connect(lambda: self.sql_editor.clear())
        clear_sql_btn.setMinimumHeight(38)
        sql_btn_layout.addWidget(clear_sql_btn)

        sql_btn_layout.addStretch()
        sql_layout.addLayout(sql_btn_layout)

        # 查询结果标签
        result_title = QLabel('📋 查询结果')
        result_title.setObjectName('titleLabel')
        sql_layout.addWidget(result_title)

        # 查询结果表格
        self.result_table = QTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f8f9fa;
            }
        """)
        sql_layout.addWidget(self.result_table)

        self.tab_widget.addTab(self.sql_tab, '💻 SQL查询')

        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        # 初始状态
        self.update_ui_state()

    def update_ui_state(self):
        """更新UI状态"""
        has_db = self.conn is not None

        # 更新状态栏
        if has_db:
            self.status_bar.showMessage(f'当前数据库: {self.current_db}')
        else:
            self.status_bar.showMessage('未打开数据库 - 请打开或新建一个数据库文件')

    def open_database(self):
        """打开数据库"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "打开SQLite数据库", "", "SQLite数据库 (*.db *.sqlite *.sqlite3);;所有文件 (*)", options=options)

        if file_name:
            try:
                if self.conn:
                    self.conn.close()

                self.current_db = file_name
                self.conn = sqlite3.connect(file_name)
                self.refresh_db_tree()
                self.update_ui_state()
                self.status_bar.showMessage(f'已打开数据库: {file_name}', 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开数据库: {str(e)}")

    def create_database(self):
        """创建新数据库"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(
            self, "创建SQLite数据库", "", "SQLite数据库 (*.db);;所有文件 (*)", options=options)

        if file_name:
            try:
                if self.conn:
                    self.conn.close()

                self.current_db = file_name
                self.conn = sqlite3.connect(file_name)
                self.refresh_db_tree()
                self.update_ui_state()
                self.status_bar.showMessage(f'已创建数据库: {file_name}', 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建数据库: {str(e)}")

    def close_database(self):
        """关闭数据库"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.current_db = None
            self.current_table = None
            self.all_table_data = []
            self.table_columns = []
            self.refresh_db_tree()
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.search_column_combo.clear()
            self.search_column_combo.addItem('所有列')
            self.data_search_input.clear()
            self.current_table_label.setText('📋 当前表: 无')
            self.row_count_label.setText('共 0 行')
            self.update_ui_state()
            self.status_bar.showMessage('已关闭数据库', 3000)

    def refresh_db_tree(self):
        """刷新数据库对象树"""
        self.db_tree.clear()

        if not self.conn:
            return

        # 添加数据库节点
        import os
        db_display_name = os.path.basename(self.current_db) if self.current_db else '数据库'
        db_item = QTreeWidgetItem(self.db_tree)
        db_item.setText(0, f'💾 {db_display_name}')
        db_item.setData(0, Qt.UserRole, 'database')
        db_item.setData(0, Qt.UserRole + 1, self.current_db)  # 存储完整路径

        try:
            cursor = self.conn.cursor()

            # 添加表分组节点
            tables_group = QTreeWidgetItem(db_item)
            tables_group.setText(0, '📊 表')
            tables_group.setData(0, Qt.UserRole, 'tables_group')

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            for table in tables:
                table_name = table[0]
                table_item = QTreeWidgetItem(tables_group)
                table_item.setText(0, f'📋 {table_name}')
                table_item.setData(0, Qt.UserRole, 'table')
                table_item.setData(0, Qt.UserRole + 1, table_name)

                # 获取表的列信息
                cursor.execute(f"PRAGMA table_info('{table_name}')")
                columns = cursor.fetchall()

                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    is_pk = '🔑 ' if col[5] else ''
                    col_item = QTreeWidgetItem(table_item)
                    col_item.setText(0, f'{is_pk}{col_name} ({col_type})')
                    col_item.setData(0, Qt.UserRole, 'column')

            # 获取所有视图
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
            views = cursor.fetchall()

            if views:
                views_group = QTreeWidgetItem(db_item)
                views_group.setText(0, '👁 视图')
                views_group.setData(0, Qt.UserRole, 'views_group')

                for view in views:
                    view_name = view[0]
                    view_item = QTreeWidgetItem(views_group)
                    view_item.setText(0, f'👁 {view_name}')
                    view_item.setData(0, Qt.UserRole, 'view')
                    view_item.setData(0, Qt.UserRole + 1, view_name)

            self.db_tree.expandAll()

            # 应用当前搜索过滤
            self.filter_db_tree(self.tree_search_input.text())

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法刷新数据库对象树: {str(e)}")

    def filter_db_tree(self, search_text):
        """根据搜索文本过滤数据库对象树"""
        search_text = search_text.strip().lower()

        def process_items(parent):
            """递归处理树节点可见性，返回是否有可见子节点"""
            any_visible = False
            for i in range(parent.childCount()):
                child = parent.child(i)
                child_type = child.data(0, Qt.UserRole)

                # 如果是分组节点（表分组/视图分组），递归处理子节点
                if child_type in ('tables_group', 'views_group'):
                    has_visible = process_items(child)
                    child.setHidden(not has_visible)
                    if has_visible:
                        any_visible = True
                elif child_type == 'table':
                    # 获取纯表名
                    table_name = child.data(0, Qt.UserRole + 1) or child.text(0)
                    clean_name = table_name.lower()

                    # 检查表名是否匹配
                    name_match = not search_text or search_text in clean_name

                    # 检查列名是否匹配
                    col_match = False
                    for j in range(child.childCount()):
                        col_child = child.child(j)
                        col_text = col_child.text(0).lower()
                        if search_text and search_text in col_text:
                            col_match = True
                            break

                    # 表名或列名匹配则显示
                    if name_match or col_match:
                        child.setHidden(False)
                        any_visible = True
                        # 处理列的可见性
                        for j in range(child.childCount()):
                            col_child = child.child(j)
                            if not search_text:
                                col_child.setHidden(False)
                            else:
                                col_text = col_child.text(0).lower()
                                col_child.setHidden(search_text not in col_text and not name_match)
                    else:
                        child.setHidden(True)
                        for j in range(child.childCount()):
                            child.child(j).setHidden(True)

                elif child_type == 'view':
                    view_name = child.data(0, Qt.UserRole + 1) or child.text(0)
                    clean_name = view_name.lower()
                    if not search_text or search_text in clean_name:
                        child.setHidden(False)
                        any_visible = True
                    else:
                        child.setHidden(True)

                elif child_type == 'column':
                    # 列节点由父表节点控制，此处不单独处理
                    pass

                else:
                    # 其他类型节点（如database）
                    has_visible = process_items(child)
                    if has_visible:
                        any_visible = True

            return any_visible

        # 处理顶层节点
        for i in range(self.db_tree.topLevelItemCount()):
            top_item = self.db_tree.topLevelItem(i)
            has_visible = process_items(top_item)
            top_item.setHidden(not has_visible)

    def on_tree_item_clicked(self, item, column):
        """当树项被点击时"""
        item_type = item.data(0, Qt.UserRole)

        if item_type == 'table':
            # 优先使用存储的表名，否则从文本中提取
            table_name = item.data(0, Qt.UserRole + 1) or item.text(0)
            # 去掉可能的emoji前缀
            for emoji in ['📋 ']:
                table_name = table_name.replace(emoji, '')
            self.show_table_data(table_name)

    def show_table_data(self, table_name):
        """显示表数据"""
        if not self.conn:
            return

        try:
            self.current_table = table_name
            self.data_search_input.clear()
            cursor = self.conn.cursor()

            # 获取表结构
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()
            self.table_columns = columns

            # 更新搜索列下拉框
            self.search_column_combo.clear()
            self.search_column_combo.addItem('所有列')
            for col in columns:
                self.search_column_combo.addItem(col[1])

            # 设置表格列
            self.table_widget.setColumnCount(len(columns))
            self.table_widget.setHorizontalHeaderLabels([col[1] for col in columns])

            # 获取表数据
            cursor.execute(f"SELECT * FROM '{table_name}'")
            rows = cursor.fetchall()
            self.all_table_data = [list(row) for row in rows]

            # 填充表格数据
            self._fill_table_data(self.all_table_data)

            # 更新当前表标签
            self.current_table_label.setText(f'📋 当前表: {table_name}')
            self.row_count_label.setText(f'共 {len(rows)} 行')

            # 调整列宽
            self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            # 切换到数据表选项卡
            self.tab_widget.setCurrentWidget(self.table_tab)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法显示表数据: {str(e)}")

    def _fill_table_data(self, rows):
        """填充表格数据"""
        self.table_widget.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else '')
                self.table_widget.setItem(i, j, item)

    def search_in_table(self, search_text):
        """在当前表数据中搜索"""
        if not self.current_table or not self.all_table_data:
            return

        search_text = search_text.strip().lower()
        selected_column = self.search_column_combo.currentIndex() - 1  # -1表示所有列

        if not search_text:
            # 无搜索词，显示全部数据
            self._fill_table_data(self.all_table_data)
            self.row_count_label.setText(f'共 {len(self.all_table_data)} 行')
            return

        # 过滤数据
        filtered_rows = []
        for row in self.all_table_data:
            if selected_column == -1:
                # 搜索所有列
                for value in row:
                    if search_text in str(value).lower():
                        filtered_rows.append(row)
                        break
            else:
                # 搜索指定列
                if selected_column < len(row):
                    if search_text in str(row[selected_column]).lower():
                        filtered_rows.append(row)

        self._fill_table_data(filtered_rows)
        self.row_count_label.setText(f'找到 {len(filtered_rows)} / {len(self.all_table_data)} 行')

    def clear_data_search(self):
        """清除数据搜索"""
        self.data_search_input.clear()
        if self.all_table_data:
            self._fill_table_data(self.all_table_data)
            self.row_count_label.setText(f'共 {len(self.all_table_data)} 行')

    def refresh_current_table(self):
        """刷新当前表数据"""
        if self.current_table:
            self.show_table_data(self.current_table)
            self.status_bar.showMessage(f'已刷新表: {self.current_table}', 3000)

    def open_query_wizard(self):
        """打开查询向导"""
        if not self.conn:
            QMessageBox.warning(self, '警告', '请先打开数据库')
            return

        dialog = QueryWizardDialog(self.conn, self.current_table, self)
        if dialog.exec_() == QDialog.Accepted:
            sql = dialog.generated_sql
            if sql:
                # 将生成的SQL填入编辑器并执行
                self.sql_editor.setPlainText(sql)
                self.tab_widget.setCurrentWidget(self.sql_tab)
                self.execute_sql()
                self.status_bar.showMessage(f'查询向导已生成并执行查询', 3000)

    def show_tree_context_menu(self, position):
        """显示树形菜单的上下文菜单"""
        item = self.db_tree.itemAt(position)
        if not item:
            return

        item_type = item.data(0, Qt.UserRole)
        menu = QMenu()

        if item_type == 'database':
            refresh_action = QAction('🔄 刷新', self)
            refresh_action.triggered.connect(self.refresh_db_tree)
            menu.addAction(refresh_action)

            new_table_action = QAction('➕ 新建表', self)
            new_table_action.triggered.connect(self.create_table)
            menu.addAction(new_table_action)

        elif item_type == 'table':
            table_name = item.data(0, Qt.UserRole + 1) or item.text(0)
            for emoji in ['📋 ']:
                table_name = table_name.replace(emoji, '')

            view_data_action = QAction('📋 查看数据', self)
            view_data_action.triggered.connect(lambda: self.show_table_data(table_name))
            menu.addAction(view_data_action)

            edit_structure_action = QAction('✏ 编辑结构', self)
            edit_structure_action.triggered.connect(lambda: self.edit_table_structure(table_name))
            menu.addAction(edit_structure_action)

            rename_table_action = QAction('📝 重命名表', self)
            rename_table_action.triggered.connect(lambda: self.rename_table(table_name))
            menu.addAction(rename_table_action)

            menu.addSeparator()

            drop_table_action = QAction('🗑 删除表', self)
            drop_table_action.triggered.connect(lambda: self.drop_table(table_name))
            menu.addAction(drop_table_action)

        menu.exec_(self.db_tree.mapToGlobal(position))

    def show_table_context_menu(self, position):
        """显示表格的上下文菜单"""
        if not self.current_table:
            return

        menu = QMenu()

        insert_row_action = QAction('➕ 插入行', self)
        insert_row_action.triggered.connect(self.insert_row)
        menu.addAction(insert_row_action)

        delete_row_action = QAction('🗑 删除行', self)
        delete_row_action.triggered.connect(self.delete_row)
        menu.addAction(delete_row_action)

        menu.addSeparator()

        save_changes_action = QAction('💾 保存更改', self)
        save_changes_action.triggered.connect(self.save_table_changes)
        menu.addAction(save_changes_action)

        menu.exec_(self.table_widget.mapToGlobal(position))

    def create_table(self):
        """创建新表"""
        if not self.conn:
            QMessageBox.warning(self, "警告", "请先打开数据库")
            return

        table_name, ok = QInputDialog.getText(self, "创建表", "请输入表名:")
        if ok and table_name:
            try:
                cursor = self.conn.cursor()
                cursor.execute(f"CREATE TABLE '{table_name}' (id INTEGER PRIMARY KEY)")
                self.conn.commit()
                self.refresh_db_tree()
                self.status_bar.showMessage(f'已创建表: {table_name}', 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建表: {str(e)}")

    def edit_table_structure(self, table_name):
        """编辑表结构"""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            info = f'表 {table_name} 的结构:\n\n'
            for col in columns:
                pk_mark = '🔑 ' if col[5] else ''
                info += f"{pk_mark}列名: {col[1]}, 类型: {col[2]}, 主键: {'是' if col[5] else '否'}\n"

            QMessageBox.information(self, "表结构", info)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法获取表结构: {str(e)}")

    def rename_table(self, old_name):
        """重命名表"""
        if not self.conn:
            return

        new_name, ok = QInputDialog.getText(self, "重命名表", "请输入新表名:", text=old_name)
        if ok and new_name and new_name != old_name:
            try:
                cursor = self.conn.cursor()
                cursor.execute(f"ALTER TABLE '{old_name}' RENAME TO '{new_name}'")
                self.conn.commit()
                self.refresh_db_tree()
                self.status_bar.showMessage(f'已将表 {old_name} 重命名为 {new_name}', 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法重命名表: {str(e)}")

    def drop_table(self, table_name):
        """删除表"""
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除表 {table_name} 吗? 此操作不可撤销!",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                cursor = self.conn.cursor()
                cursor.execute(f"DROP TABLE '{table_name}'")
                self.conn.commit()
                self.refresh_db_tree()
                self.table_widget.setRowCount(0)
                self.table_widget.setColumnCount(0)
                self.current_table = None
                self.all_table_data = []
                self.table_columns = []
                self.current_table_label.setText('📋 当前表: 无')
                self.row_count_label.setText('共 0 行')
                self.status_bar.showMessage(f'已删除表: {table_name}', 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法删除表: {str(e)}")

    def insert_row(self):
        """插入新行"""
        if not self.current_table or not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()

            # 创建一个空行
            self.table_widget.insertRow(self.table_widget.rowCount())

            # 为每列创建一个空的表格项
            for i in range(len(columns)):
                item = QTableWidgetItem('')
                self.table_widget.setItem(self.table_widget.rowCount() - 1, i, item)

            self.status_bar.showMessage('已插入新行，请编辑数据后保存', 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法插入行: {str(e)}")

    def delete_row(self):
        """删除选中行"""
        if not self.current_table or not self.conn:
            return

        current_row = self.table_widget.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "警告", "请先选择要删除的行")
            return

        try:
            # 获取主键值
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()

            # 查找主键列
            pk_column = None
            for col in columns:
                if col[5]:  # col[5] 表示是否是主键
                    pk_column = col[1]
                    break

            if pk_column:
                # 获取主键值
                pk_value = self.table_widget.item(current_row, 0).text()
                cursor.execute(f"DELETE FROM {self.current_table} WHERE {pk_column} = ?", (pk_value,))
                self.conn.commit()
                self.table_widget.removeRow(current_row)
                self.status_bar.showMessage('已删除行', 3000)
            else:
                QMessageBox.warning(self, "警告", "无法删除行: 表没有主键")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法删除行: {str(e)}")

    def save_table_changes(self):
        """保存表格更改"""
        if not self.current_table or not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()

            # 查找主键列
            pk_column = None
            for col in columns:
                if col[5]:  # col[5] 表示是否是主键
                    pk_column = col[1]
                    break

            if not pk_column:
                QMessageBox.warning(self, "警告", "无法保存更改: 表没有主键")
                return

            # 遍历所有行，检查是否有更改
            for row in range(self.table_widget.rowCount()):
                pk_value = self.table_widget.item(row, 0).text()

                # 构建更新语句
                update_fields = []
                update_values = []

                for col in range(1, len(columns)):  # 跳过主键列
                    value = self.table_widget.item(row, col).text()
                    column_name = columns[col][1]
                    update_fields.append(f"{column_name} = ?")
                    update_values.append(value)

                if update_fields:
                    update_values.append(pk_value)
                    update_sql = f"UPDATE {self.current_table} SET {', '.join(update_fields)} WHERE {pk_column} = ?"
                    cursor.execute(update_sql, tuple(update_values))

            self.conn.commit()
            self.status_bar.showMessage('更改已保存', 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存更改: {str(e)}")

    def execute_sql(self):
        """执行SQL查询"""
        if not self.conn:
            QMessageBox.warning(self, "警告", "请先打开数据库")
            return

        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "警告", "请输入SQL查询语句")
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql)

            # 如果是SELECT查询，显示结果
            if sql.upper().lstrip().startswith('SELECT'):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]

                # 设置结果表格
                self.result_table.setColumnCount(len(columns))
                self.result_table.setHorizontalHeaderLabels(columns)
                self.result_table.setRowCount(len(rows))

                for i, row in enumerate(rows):
                    for j, value in enumerate(row):
                        item = QTableWidgetItem(str(value) if value is not None else '')
                        self.result_table.setItem(i, j, item)

                self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
                self.status_bar.showMessage(f'查询返回 {len(rows)} 行结果', 3000)
            else:
                # 对于非SELECT查询，提交更改并显示影响行数
                self.conn.commit()
                self.status_bar.showMessage(f'SQL执行成功，影响了 {cursor.rowcount} 行', 3000)
                # 刷新数据库树
                self.refresh_db_tree()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"SQL执行错误: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    db_manager = DBManager()
    db_manager.show()
    sys.exit(app.exec_())
