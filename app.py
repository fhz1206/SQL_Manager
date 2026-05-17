import sys
import os  # 用于处理图标路径
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QTabWidget, QLabel, QLineEdit,
                             QComboBox, QFileDialog, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QMenu, QAction, QStatusBar, QToolBar, QTextEdit, QFrame,
                             QSizePolicy, QAbstractItemView,
                             QCheckBox, QGroupBox, QScrollArea, QDialog)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

# 图标绝对路径拼接（避免相对路径找不到的问题）
ICON_PATH = os.path.join(os.path.dirname(__file__), 'icon.ico')

# 现代化样式表（适配小屏+弹窗样式）
STYLESHEET = """
QMainWindow {
    background-color: #f5f6fa;
}

QToolBar {
    background-color: #2c3e50;
    border: none;
    padding: 4px 6px;
    spacing: 6px;
}

QToolBar QToolButton {
    background-color: #34495e;
    color: #ecf0f1;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: bold;
    min-width: 60px;
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
    font-size: 11px;
    padding: 2px 8px;
}

QSplitter::handle {
    background-color: #dcdde1;
    width: 2px;
}

QTreeWidget {
    background-color: #ffffff;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    padding: 4px;
    font-size: 12px;
    outline: none;
}

QTreeWidget::item {
    padding: 4px 2px;
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
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-size: 12px;
    font-weight: bold;
    min-width: 80px;
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
    font-size: 12px;
    selection-background-color: #3498db;
    selection-color: #ffffff;
    outline: none;
}

QTableWidget::item {
    padding: 4px 8px;
}

QTableWidget::item:selected {
    background-color: #3498db;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #f8f9fa;
    color: #2c3e50;
    padding: 6px 8px;
    border: none;
    border-bottom: 2px solid #3498db;
    font-weight: bold;
    font-size: 12px;
}

QTextEdit {
    background-color: #2c3e50;
    color: #ecf0f1;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    padding: 8px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
    selection-background-color: #3498db;
    selection-color: #ffffff;
}

QPushButton {
    background-color: #3498db;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: bold;
    min-width: 60px;
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

QPushButton#wizardButton {
    background-color: #8e44ad;
}

QPushButton#wizardButton:hover {
    background-color: #7d3c98;
}

QPushButton#wizardButton:pressed {
    background-color: #6c3483;
}

QLineEdit {
    background-color: #ffffff;
    border: 2px solid #dcdde1;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
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
    padding: 5px 10px;
    font-size: 12px;
    color: #2c3e50;
    min-width: 80px;
}

QComboBox:focus {
    border-color: #3498db;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
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
    font-size: 12px;
}

QLabel#titleLabel {
    color: #2c3e50;
    font-size: 14px;
    font-weight: bold;
}

QLabel#searchIcon {
    color: #b2bec3;
    font-size: 14px;
}

QMenu {
    background-color: #ffffff;
    border: 1px solid #dcdde1;
    border-radius: 8px;
    padding: 4px 0px;
}

QMenu::item {
    padding: 6px 24px;
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
    margin: 3px 8px;
}

QScrollBar:vertical {
    background-color: #f5f6fa;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #b2bec3;
    border-radius: 4px;
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
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #b2bec3;
    border-radius: 4px;
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
    font-size: 13px;
}

/* 查询向导弹窗样式 */
QDialog {
    background-color: #f5f6fa;
}

QGroupBox {
    font-weight: bold;
    font-size: 12px;
    color: #2c3e50;
    border: 2px solid #dcdde1;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QCheckBox {
    color: #2c3e50;
    font-size: 12px;
    spacing: 4px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 2px solid #b2bec3;
}

QCheckBox::indicator:checked {
    background-color: #3498db;
    border-color: #3498db;
}
"""


class SearchLineEdit(QLineEdit):
    """带搜索图标的输入框"""
    def __init__(self, placeholder='搜索...', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(32)


class QueryWizardDialog(QDialog):
    """查询向导弹窗 - 生成SQL后自动填入编辑器"""
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.generated_sql = ''
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('🔍 查询向导')
        self.setWindowIcon(QIcon(ICON_PATH))  # 弹窗使用ico作为窗口图标
        self.setMinimumSize(700, 600)
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
        main_layout.setSpacing(12)
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
        step1_layout.setContentsMargins(12, 8, 12, 8)
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
        step2_layout.setContentsMargins(12, 8, 12, 8)
        step2_group.setLayout(step2_layout)

        # 全选/取消全选
        select_all_layout = QHBoxLayout()
        select_all_layout.setSpacing(8)
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
        scroll_area.setMaximumHeight(160)
        scroll_area.setStyleSheet('''
            QScrollArea {
                border: 1px solid #dcdde1;
                border-radius: 6px;
                background-color: #ffffff;
            }
        ''')

        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout()
        self.columns_layout.setSpacing(18)
        self.columns_widget.setLayout(self.columns_layout)
        scroll_area.setWidget(self.columns_widget)
        step2_layout.addWidget(scroll_area)

        main_layout.addWidget(step2_group)

        # ===== 步骤3: 设置筛选条件 =====
        step3_group = QGroupBox('步骤3: 设置筛选条件（可选）')
        step3_layout = QVBoxLayout()
        step3_layout.setContentsMargins(12, 8, 12, 8)
        step3_layout.setSpacing(10)
        step3_group.setLayout(step3_layout)

        # 筛选条件行
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        filter_row.addWidget(QLabel('列:'))
        self.filter_column_combo = QComboBox()
        self.filter_column_combo.setMinimumWidth(130)
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
        self.filter_op_combo.setMinimumWidth(150)
        self.filter_op_combo.setMinimumHeight(34)
        self.filter_op_combo.currentIndexChanged.connect(self._on_operator_changed)
        filter_row.addWidget(self.filter_op_combo)

        filter_row.addWidget(QLabel('值:'))
        self.filter_value_input = QLineEdit()
        self.filter_value_input.setPlaceholderText('输入筛选值...')
        self.filter_value_input.setMinimumWidth(160)
        self.filter_value_input.setMinimumHeight(34)
        filter_row.addWidget(self.filter_value_input)

        step3_layout.addLayout(filter_row)

        # 第二个筛选条件
        filter_row2 = QHBoxLayout()
        filter_row2.setSpacing(12)

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
        filter_row3.setSpacing(12)

        filter_row3.addWidget(QLabel('列:'))
        self.filter_column_combo2 = QComboBox()
        self.filter_column_combo2.setMinimumWidth(130)
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
        self.filter_op_combo2.setMinimumWidth(150)
        self.filter_op_combo2.setMinimumHeight(34)
        self.filter_op_combo2.currentIndexChanged.connect(self._on_operator_changed2)
        filter_row3.addWidget(self.filter_op_combo2)

        filter_row3.addWidget(QLabel('值:'))
        self.filter_value_input2 = QLineEdit()
        self.filter_value_input2.setPlaceholderText('输入筛选值...')
        self.filter_value_input2.setMinimumWidth(160)
        self.filter_value_input2.setMinimumHeight(34)
        filter_row3.addWidget(self.filter_value_input2)

        step3_layout.addLayout(filter_row3)

        main_layout.addWidget(step3_group)

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

        # 生成并执行按钮
        execute_btn = QPushButton('▶ 生成并执行')
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

        if not self.conn or not table_name:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            # 创建列复选框
            col_widget = QWidget()
            col_inner = QVBoxLayout()
            col_inner.setSpacing(6)
            col_widget.setLayout(col_inner)

            self.column_checks = []
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                is_pk = '🔑 ' if col[5] else ''
                check = QCheckBox(f'{is_pk}{col_name} ({col_type})')
                check.setChecked(True)
                check.col_name = col_name
                check.stateChanged.connect(self._generate_sql)
                self.column_checks.append(check)
                col_inner.addWidget(check)

            self.columns_layout.addWidget(col_widget)

            # 更新筛选列下拉框
            for col in columns:
                self.filter_column_combo.addItem(col[1])
                self.filter_column_combo2.addItem(col[1])

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
        is_null_op = idx in (9, 10)
        self.filter_value_input.setEnabled(not is_null_op)
        if is_null_op:
            self.filter_value_input.clear()
            self.filter_value_input.setPlaceholderText('此条件无需输入值')
        else:
            self.filter_value_input.setPlaceholderText('输入筛选值...')

    def _on_operator_changed2(self, idx):
        """当第二个操作符变化时"""
        is_null_op = idx in (9, 10)
        self.filter_value_input2.setEnabled(not is_null_op)
        if is_null_op:
            self.filter_value_input2.clear()
            self.filter_value_input2.setPlaceholderText('此条件无需输入值')
        else:
            self.filter_value_input2.setPlaceholderText('输入筛选值...')

    def _build_condition(self, column, op_idx, value):
        """构建单个筛选条件"""
        ops = ['=', '!=', '>', '>=', '<', '<=', 'LIKE', 'LIKE', 'LIKE', 'IS NULL', 'IS NOT NULL']
        op = ops[op_idx] if op_idx < len(ops) else '='

        if op == 'IS NULL':
            return f'"{column}" IS NULL'
        elif op == 'IS NOT NULL':
            return f'"{column}" IS NOT NULL'
        elif op == 'LIKE' and op_idx == 7:
            return f'"{column}" LIKE \'{value}%\''
        elif op == 'LIKE' and op_idx == 8:
            return f'"{column}" LIKE \'%{value}\''
        elif op == 'LIKE':
            return f'"{column}" LIKE \'%{value}%\''
        else:
            return f'"{column}" {op} \'{value}\''

    def _generate_sql(self):
        """生成SQL语句（已移除排序功能）"""
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

        self.sql_preview.setPlainText(sql)
        self.generated_sql = sql
        return sql

    def _execute_query(self):
        """生成并执行查询"""
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
        self.all_table_data = []
        self.table_columns = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SQLite 数据库查看工具')
        self.setWindowIcon(QIcon(ICON_PATH))  # 主窗口使用ico作为窗口图标
        self.setGeometry(80, 80, 1000, 650)
        self.setMinimumSize(800, 500)
        self.setStyleSheet(STYLESHEET)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 创建工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 打开数据库按钮（仅文字+emoji，不使用ico作为按钮图标）
        open_db_action = QAction('📂 打开数据库', self)
        open_db_action.triggered.connect(self.open_database)
        toolbar.addAction(open_db_action)

        toolbar.addSeparator()

        # 关闭数据库按钮（仅文字+emoji，不使用ico作为按钮图标）
        close_db_action = QAction('✖ 关闭数据库', self)
        close_db_action.triggered.connect(self.close_database)
        toolbar.addAction(close_db_action)

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 创建主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        main_layout.addWidget(splitter)

        # ========== 左侧面板 - 数据库对象浏览器 ==========
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)
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
        self.db_tree.setIndentation(16)
        self.db_tree.setAnimated(True)
        left_layout.addWidget(self.db_tree)

        splitter.addWidget(left_panel)

        # ========== 右侧面板 - 数据表和SQL编辑器 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(2, 0, 0, 0)
        right_layout.setSpacing(0)
        right_panel.setLayout(right_layout)

        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)

        # ========== 数据表选项卡 ==========
        self.table_tab = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(4, 4, 4, 4)
        table_layout.setSpacing(6)
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
        search_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(6)
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
        self.search_column_combo.setMinimumWidth(100)
        search_layout.addWidget(self.search_column_combo)

        # 搜索关键词输入
        self.data_search_input = SearchLineEdit('🔍 输入关键词搜索数据...')
        self.data_search_input.setMinimumWidth(180)
        self.data_search_input.textChanged.connect(self.search_in_table)
        search_layout.addWidget(self.data_search_input)

        # 清除搜索按钮
        clear_search_btn = QPushButton('清除')
        clear_search_btn.setMinimumWidth(60)
        clear_search_btn.clicked.connect(self.clear_data_search)
        search_layout.addWidget(clear_search_btn)

        table_layout.addWidget(search_frame)

        # 表格控件
        self.table_widget = QTableWidget()
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f8f9fa;
            }
        """)
        table_layout.addWidget(self.table_widget)

        # 底部操作栏
        table_action_layout = QHBoxLayout()
        table_action_layout.setSpacing(8)

        self.row_count_label = QLabel('共 0 行')
        self.row_count_label.setStyleSheet('color: #636e72; font-size: 11px;')
        table_action_layout.addWidget(self.row_count_label)

        table_action_layout.addStretch()

        refresh_btn = QPushButton('🔄 刷新')
        refresh_btn.setObjectName('successButton')
        refresh_btn.clicked.connect(self.refresh_current_table)
        table_action_layout.addWidget(refresh_btn)

        table_layout.addLayout(table_action_layout)
        table_layout.setStretchFactor(self.table_widget, 1)

        self.tab_widget.addTab(self.table_tab, '📊 数据表')

        # ========== SQL编辑器选项卡 ==========
        self.sql_tab = QWidget()
        sql_layout = QVBoxLayout()
        sql_layout.setContentsMargins(4, 4, 4, 4)
        sql_layout.setSpacing(6)
        self.sql_tab.setLayout(sql_layout)

        # SQL编辑器标签+向导按钮
        sql_header_layout = QHBoxLayout()
        sql_title = QLabel('💻 SQL 查询编辑器')
        sql_title.setObjectName('titleLabel')
        sql_header_layout.addWidget(sql_title)

        # 查询向导按钮（弹窗触发）
        query_wizard_btn = QPushButton('🔍 查询向导')
        query_wizard_btn.setObjectName('wizardButton')
        query_wizard_btn.setStyleSheet('''
            QPushButton#wizardButton {
                background-color: #8e44ad;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
                min-width: 90px;
            }
            QPushButton#wizardButton:hover {
                background-color: #7d3c98;
            }
            QPushButton#wizardButton:pressed {
                background-color: #6c3483;
            }
        ''')
        query_wizard_btn.clicked.connect(self.open_query_wizard)
        sql_header_layout.addWidget(query_wizard_btn)

        sql_header_layout.addStretch()
        sql_layout.addLayout(sql_header_layout)

        # SQL编辑器
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText('输入 SQL 查询语句...\n\n例如: SELECT * FROM table_name WHERE id > 10')
        self.sql_editor.setMinimumHeight(120)
        self.sql_editor.setMaximumHeight(400)
        self.sql_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sql_layout.addWidget(self.sql_editor)

        # 执行按钮行
        sql_btn_layout = QHBoxLayout()
        sql_btn_layout.setSpacing(8)

        execute_button = QPushButton('▶ 执行查询')
        execute_button.setObjectName('successButton')
        execute_button.clicked.connect(self.execute_sql)
        execute_button.setMinimumHeight(34)
        sql_btn_layout.addWidget(execute_button)

        clear_sql_btn = QPushButton('🗑 清空')
        clear_sql_btn.clicked.connect(lambda: self.sql_editor.clear())
        clear_sql_btn.setMinimumHeight(34)
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
        self.result_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_table.setStyleSheet("""
            QTableWidget {
                alternate-background-color: #f8f9fa;
            }
        """)
        sql_layout.addWidget(self.result_table)

        # 布局权重：结果表格占3份，编辑器占1份，其余固定
        sql_layout.setStretchFactor(sql_title, 0)
        sql_layout.setStretchFactor(self.sql_editor, 1)
        sql_layout.setStretchFactor(sql_btn_layout, 0)
        sql_layout.setStretchFactor(result_title, 0)
        sql_layout.setStretchFactor(self.result_table, 3)

        self.tab_widget.addTab(self.sql_tab, '💻 SQL查询')

        splitter.addWidget(right_panel)

        # 分割器比例：左侧固定200px，右侧自适应
        splitter.setSizes([200, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # 初始状态
        self.update_ui_state()

    def open_query_wizard(self):
        """打开查询向导弹窗"""
        if not self.conn:
            QMessageBox.warning(self, '警告', '请先打开数据库')
            return
        dialog = QueryWizardDialog(self.conn, self)
        if dialog.exec_() == QDialog.Accepted:
            sql = dialog.generated_sql
            if sql:
                self.sql_editor.setPlainText(sql)
                self.execute_sql()
                self.tab_widget.setCurrentWidget(self.sql_tab)
                self.status_bar.showMessage('查询向导已生成并执行查询', 3000)

    def update_ui_state(self):
        """更新UI状态"""
        has_db = self.conn is not None
        if has_db:
            self.status_bar.showMessage(f'当前数据库: {self.current_db}')
        else:
            self.status_bar.showMessage('未打开数据库 - 请打开一个数据库文件')

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

        db_display_name = os.path.basename(self.current_db) if self.current_db else '数据库'
        db_item = QTreeWidgetItem(self.db_tree)
        db_item.setText(0, f'💾 {db_display_name}')
        db_item.setData(0, Qt.UserRole, 'database')
        db_item.setData(0, Qt.UserRole + 1, self.current_db)

        try:
            cursor = self.conn.cursor()
            tables_group = QTreeWidgetItem(db_item)
            tables_group.setText(0, '📊 表')
            tables_group.setData(0, Qt.UserRole, 'tables_group')

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()
            for table in tables:
                table_name = table[0]
                table_item = QTreeWidgetItem(tables_group)
                table_item.setText(0, f'📋 {table_name}')
                table_item.setData(0, Qt.UserRole, 'table')
                table_item.setData(0, Qt.UserRole + 1, table_name)

                cursor.execute(f"PRAGMA table_info('{table_name}')")
                columns = cursor.fetchall()
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    is_pk = '🔑 ' if col[5] else ''
                    col_item = QTreeWidgetItem(table_item)
                    col_item.setText(0, f'{is_pk}{col_name} ({col_type})')
                    col_item.setData(0, Qt.UserRole, 'column')

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
            self.filter_db_tree(self.tree_search_input.text())
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法刷新数据库对象树: {str(e)}")

    def filter_db_tree(self, search_text):
        """根据搜索文本过滤数据库对象树"""
        search_text = search_text.strip().lower()

        def process_items(parent):
            any_visible = False
            for i in range(parent.childCount()):
                child = parent.child(i)
                child_type = child.data(0, Qt.UserRole)
                if child_type in ('tables_group', 'views_group'):
                    has_visible = process_items(child)
                    child.setHidden(not has_visible)
                    if has_visible:
                        any_visible = True
                elif child_type == 'table':
                    table_name = child.data(0, Qt.UserRole + 1) or child.text(0)
                    clean_name = table_name.lower()
                    name_match = not search_text or search_text in clean_name
                    col_match = False
                    for j in range(child.childCount()):
                        col_child = child.child(j)
                        col_text = col_child.text(0).lower()
                        if search_text and search_text in col_text:
                            col_match = True
                            break
                    if name_match or col_match:
                        child.setHidden(False)
                        any_visible = True
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
                    pass
                else:
                    has_visible = process_items(child)
                    if has_visible:
                        any_visible = True
            return any_visible

        for i in range(self.db_tree.topLevelItemCount()):
            top_item = self.db_tree.topLevelItem(i)
            has_visible = process_items(top_item)
            top_item.setHidden(not has_visible)

    def on_tree_item_clicked(self, item, column):
        """当树项被点击时"""
        item_type = item.data(0, Qt.UserRole)
        if item_type == 'table':
            table_name = item.data(0, Qt.UserRole + 1) or item.text(0)
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
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()
            self.table_columns = columns

            self.search_column_combo.clear()
            self.search_column_combo.addItem('所有列')
            for col in columns:
                self.search_column_combo.addItem(col[1])

            self.table_widget.setColumnCount(len(columns))
            self.table_widget.setHorizontalHeaderLabels([col[1] for col in columns])

            cursor.execute(f"SELECT * FROM '{table_name}'")
            rows = cursor.fetchall()
            self.all_table_data = [list(row) for row in rows]
            self._fill_table_data(self.all_table_data)

            self.current_table_label.setText(f'📋 当前表: {table_name}')
            self.row_count_label.setText(f'共 {len(rows)} 行')
            self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
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
        selected_column = self.search_column_combo.currentIndex() - 1
        if not search_text:
            self._fill_table_data(self.all_table_data)
            self.row_count_label.setText(f'共 {len(self.all_table_data)} 行')
            return
        filtered_rows = []
        for row in self.all_table_data:
            if selected_column == -1:
                for value in row:
                    if search_text in str(value).lower():
                        filtered_rows.append(row)
                        break
            else:
                if selected_column < len(row) and search_text in str(row[selected_column]).lower():
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
        menu.exec_(self.db_tree.mapToGlobal(position))

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
            if sql.upper().lstrip().startswith('SELECT'):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
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
                self.conn.commit()
                self.status_bar.showMessage(f'SQL执行成功，影响了 {cursor.rowcount} 行', 3000)
                self.refresh_db_tree()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"SQL执行错误: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    db_manager = DBManager()
    db_manager.show()
    sys.exit(app.exec_())