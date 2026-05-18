from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QPushButton, QCheckBox, QGroupBox, QScrollArea, QWidget)
from PyQt5.QtGui import QIcon

from config import ICON_PATH


class QueryWizardDialog(QDialog):
    """查询向导弹窗 - 生成SQL后自动填入编辑器"""
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.generated_sql = ''
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('🔍 查询向导')
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(700, 600)
        # 弹窗独立样式
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
            '等于 (=)', '不等于 (!=)', '大于 (>)', '大于等于 (>=)', 
            '小于 (<)', '小于等于 (<=)', '包含 (LIKE)', '以...开头', 
            '以...结尾', '为空 (IS NULL)', '不为空 (IS NOT NULL)',
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
            '等于 (=)', '不等于 (!=)', '大于 (>)', '大于等于 (>=)', 
            '小于 (<)', '小于等于 (<=)', '包含 (LIKE)', '以...开头', 
            '以...结尾', '为空 (IS NULL)', '不为空 (IS NOT NULL)',
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
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.filter_column_combo.clear()
        self.filter_column_combo2.clear()

        if not self.conn or not table_name:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

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
        """生成SQL语句"""
        table_name = self.table_combo.currentText()
        if not table_name:
            self.sql_preview.setPlainText('')
            return ''

        selected_cols = []
        for check in getattr(self, 'column_checks', []):
            if check.isChecked():
                selected_cols.append(f'"{check.col_name}"')

        if not selected_cols:
            selected_cols = ['*']

        sql = f'SELECT {", ".join(selected_cols)} FROM "{table_name}"'

        conditions = []
        filter_col = self.filter_column_combo.currentText()
        if filter_col:
            op_idx = self.filter_op_combo.currentIndex()
            value = self.filter_value_input.text()
            if op_idx in (9, 10) or value:
                conditions.append(self._build_condition(filter_col, op_idx, value))

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
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, '警告', '请先选择表和列')
            return
        self.generated_sql = sql
        self.accept()