import sys
import os  # 用于路径处理
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QTabWidget, QLabel, QLineEdit,
                             QComboBox, QFileDialog, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QMenu, QAction, QStatusBar, QToolBar, QTextEdit, QFrame,
                             QSizePolicy, QAbstractItemView,
                             QCheckBox, QGroupBox, QScrollArea, QDialog,
                             QTableView)  # 删除了错误的QAbstractTableModel导入
from PyQt5.QtCore import Qt, QSize, QAbstractTableModel, QModelIndex
from PyQt5.QtGui import QIcon, QColor

# 路径配置
ICON_PATH = os.path.join(os.path.dirname(__file__), 'icon.ico')
CSS_PATH = os.path.join(os.path.dirname(__file__), 'style.css')  # 样式文件路径


# ==================== 自定义组件区域 ====================
class SearchLineEdit(QLineEdit):
    """带搜索图标的输入框"""
    def __init__(self, placeholder='搜索...', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(32)


# ==================== 虚拟表格组件（解决大表格渲染卡顿问题） ====================
class TableModel(QAbstractTableModel):
    """虚拟表格数据模型，仅加载可视区域数据，支持分批加载"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # 当前已加载的数据
        self._columns = []  # 列名
        self._total_rows = 0  # 表总行数
        self._has_more = False  # 是否还有更多数据未加载
        self._alternating = True  # 是否开启交替行颜色

    def set_data(self, data, columns, total_rows, has_more=False):
        """设置模型数据"""
        self.beginResetModel()
        self._data = data
        self._columns = columns
        self._total_rows = total_rows
        self._has_more = has_more
        self.endResetModel()

    def add_data(self, new_data):
        """追加加载更多数据"""
        self.beginInsertRows(QModelIndex(), len(self._data), len(self._data) + len(new_data) - 1)
        self._data.extend(new_data)
        self._has_more = len(self._data) < self._total_rows
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None
        
        row, col = index.row(), index.column()
        value = self._data[row][col] if col < len(self._data[row]) else ''
        
        if role == Qt.DisplayRole:
            return str(value) if value is not None else ''
        elif role == Qt.BackgroundRole and self._alternating:
            return QColor('#f8f9fa') if row % 2 == 1 else QColor('#ffffff')
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._columns[section] if section < len(self._columns) else ''
        return None

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    @property
    def has_more(self):
        return self._has_more
    
    @property
    def loaded_count(self):
        return len(self._data)
    
    @property
    def total_rows(self):
        return self._total_rows


class VirtualTableWidget(QTableView):
    """虚拟表格控件，封装模型和加载更多逻辑"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = TableModel(self)
        self.setModel(self.model)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.load_more_signal = None  # 外部绑定加载更多回调

    def set_alternating(self, enabled):
        self.model._alternating = enabled
        self.model.layoutChanged.emit()

    def load_more(self):
        """触发加载更多回调"""
        if self.load_more_signal and self.model.has_more:
            self.load_more_signal()


# ==================== 查询向导弹窗 ====================
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
        # 弹窗独立样式（仅保留弹窗特有的样式，通用样式已在style.css中定义）
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
            QMessageBox.warning(self, '警告', '请先选择表和列')
            return
        self.generated_sql = sql
        self.accept()


# ==================== 主窗口类 ====================
class DBManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_db = None
        self.conn = None
        self.current_table = None
        # 表数据相关
        self.table_total_rows = 0
        self.table_loaded_rows = 0
        self.table_page_size = 1000
        self.table_columns = []
        # SQL查询相关
        self.sql_result_total = 0
        self.sql_result_loaded = 0
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SQLite 数据库查看工具')
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(80, 80, 1000, 650)
        self.setMinimumSize(800, 500)

        # 读取外部样式文件
        try:
            with open(CSS_PATH, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
        except Exception as e:
            QMessageBox.warning(self, '样式加载失败', f'无法加载style.css：{str(e)}\n请确保style.css和程序在同一目录下')

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 创建工具栏
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 打开数据库按钮
        open_db_action = QAction('📂 打开数据库', self)
        open_db_action.triggered.connect(self.open_database)
        toolbar.addAction(open_db_action)

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

        # 搜索框
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
        self.db_tree.itemExpanded.connect(self.on_tree_item_expanded)
        left_layout.addWidget(self.db_tree)

        splitter.addWidget(left_panel)

        # ========== 右侧面板 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(2, 0, 0, 0)
        right_layout.setSpacing(0)
        right_panel.setLayout(right_layout)

        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)

        # ========== 数据表选项卡 ==========
        self.table_tab = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(4, 4, 4, 4)
        table_layout.setSpacing(6)
        self.table_tab.setLayout(table_layout)

        # 搜索栏
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

        self.current_table_label = QLabel('📋 当前表: 无')
        self.current_table_label.setObjectName('titleLabel')
        search_layout.addWidget(self.current_table_label)

        search_layout.addStretch()

        search_layout.addWidget(QLabel('搜索列:'))
        self.search_column_combo = QComboBox()
        self.search_column_combo.addItem('所有列')
        self.search_column_combo.setMinimumWidth(100)
        search_layout.addWidget(self.search_column_combo)

        self.data_search_input = SearchLineEdit('🔍 输入关键词搜索数据...')
        self.data_search_input.setMinimumWidth(180)
        self.data_search_input.textChanged.connect(self.search_in_table)
        search_layout.addWidget(self.data_search_input)

        clear_search_btn = QPushButton('清除')
        clear_search_btn.setMinimumWidth(60)
        clear_search_btn.clicked.connect(self.clear_data_search)
        search_layout.addWidget(clear_search_btn)

        table_layout.addWidget(search_frame)

        # 虚拟表格
        self.table_widget = VirtualTableWidget()
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        table_layout.addWidget(self.table_widget)

        # 底部操作栏
        table_action_layout = QHBoxLayout()
        table_action_layout.setSpacing(8)

        self.row_count_label = QLabel('共 0 行')
        self.row_count_label.setStyleSheet('color: #636e72; font-size: 11px;')
        table_action_layout.addWidget(self.row_count_label)

        table_action_layout.addStretch()

        # 加载更多按钮
        self.table_load_more_btn = QPushButton('加载更多')
        self.table_load_more_btn.setObjectName('successButton')
        self.table_load_more_btn.setMinimumWidth(80)
        self.table_load_more_btn.clicked.connect(self.load_more_table_data)
        self.table_load_more_btn.setVisible(False)
        table_action_layout.addWidget(self.table_load_more_btn)

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

        # 标题+向导按钮
        sql_header_layout = QHBoxLayout()
        sql_title = QLabel('💻 SQL 查询编辑器')
        sql_title.setObjectName('titleLabel')
        sql_header_layout.addWidget(sql_title)

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

        # 查询结果
        result_title = QLabel('📋 查询结果')
        result_title.setObjectName('titleLabel')
        sql_layout.addWidget(result_title)

        self.result_table = VirtualTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sql_layout.addWidget(self.result_table)

        # 结果底部操作栏
        sql_result_action_layout = QHBoxLayout()
        sql_result_action_layout.setSpacing(8)
        self.sql_result_count_label = QLabel('共 0 行')
        self.sql_result_count_label.setStyleSheet('color: #636e72; font-size: 11px;')
        sql_result_action_layout.addWidget(self.sql_result_count_label)
        sql_result_action_layout.addStretch()
        self.sql_load_more_btn = QPushButton('加载更多')
        self.sql_load_more_btn.setObjectName('successButton')
        self.sql_load_more_btn.setMinimumWidth(80)
        self.sql_load_more_btn.clicked.connect(self.load_more_sql_result)
        self.sql_load_more_btn.setVisible(False)
        sql_result_action_layout.addWidget(self.sql_load_more_btn)
        sql_layout.addLayout(sql_result_action_layout)

        # 布局权重
        sql_layout.setStretchFactor(sql_title, 0)
        sql_layout.setStretchFactor(self.sql_editor, 1)
        sql_layout.setStretchFactor(sql_btn_layout, 0)
        sql_layout.setStretchFactor(result_title, 0)
        sql_layout.setStretchFactor(self.result_table, 3)

        self.tab_widget.addTab(self.sql_tab, '💻 SQL查询')

        splitter.addWidget(right_panel)

        # 分割器比例
        splitter.setSizes([200, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.update_ui_state()

    def on_tree_item_expanded(self, item):
        """树节点展开时懒加载列信息"""
        item_type = item.data(0, Qt.UserRole)
        if item_type == 'table':
            if item.data(0, Qt.UserRole + 2) == 'columns_loaded':
                return
            table_name = item.data(0, Qt.UserRole + 1)
            try:
                cursor = self.conn.cursor()
                cursor.execute(f"PRAGMA table_info('{table_name}')")
                columns = cursor.fetchall()
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    is_pk = '🔑 ' if col[5] else ''
                    col_item = QTreeWidgetItem(item)
                    col_item.setText(0, f'{is_pk}{col_name} ({col_type})')
                    col_item.setData(0, Qt.UserRole, 'column')
                item.setData(0, Qt.UserRole + 2, 'columns_loaded')
            except Exception:
                pass

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
            self.table_total_rows = 0
            self.table_loaded_rows = 0
            self.sql_result_total = 0
            self.sql_result_loaded = 0
            self.refresh_db_tree()
            self.table_widget.model.set_data([], [], 0)
            self.result_table.model.set_data([], [], 0)
            self.search_column_combo.clear()
            self.search_column_combo.addItem('所有列')
            self.data_search_input.clear()
            self.current_table_label.setText('📋 当前表: 无')
            self.row_count_label.setText('共 0 行')
            self.table_load_more_btn.setVisible(False)
            self.sql_result_count_label.setText('共 0 行')
            self.sql_load_more_btn.setVisible(False)
            self.update_ui_state()
            self.status_bar.showMessage('已关闭数据库', 3000)

    def refresh_db_tree(self):
        """刷新数据库树（懒加载，仅加载表名）"""
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
                table_item.setData(0, Qt.UserRole + 2, 'columns_not_loaded')

            self.db_tree.expandItem(db_item)
            self.filter_db_tree(self.tree_search_input.text())
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法刷新数据库对象树: {str(e)}")

    def filter_db_tree(self, search_text):
        """过滤数据库树"""
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
        """点击树节点加载表数据"""
        item_type = item.data(0, Qt.UserRole)
        if item_type == 'table':
            table_name = item.data(0, Qt.UserRole + 1) or item.text(0)
            for emoji in ['📋 ']:
                table_name = table_name.replace(emoji, '')
            self.show_table_data(table_name)

    def show_table_data(self, table_name):
        """显示表数据（懒加载，默认仅加载前1000行）"""
        if not self.conn:
            return
        try:
            self.current_table = table_name
            self.data_search_input.clear()
            cursor = self.conn.cursor()

            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()
            self.table_columns = [col[1] for col in columns]

            self.search_column_combo.clear()
            self.search_column_combo.addItem('所有列')
            for col in columns:
                self.search_column_combo.addItem(col[1])

            # 获取总行数
            cursor.execute(f"SELECT COUNT(*) FROM '{table_name}'")
            self.table_total_rows = cursor.fetchone()[0]
            self.table_loaded_rows = 0

            # 默认加载前1000行
            cursor.execute(f"SELECT * FROM '{table_name}' LIMIT {self.table_page_size}")
            rows = cursor.fetchall()
            self.table_loaded_rows = len(rows)
            has_more = self.table_loaded_rows < self.table_total_rows

            self.table_widget.model.set_data(
                data=[list(row) for row in rows],
                columns=self.table_columns,
                total_rows=self.table_total_rows,
                has_more=has_more
            )

            self.current_table_label.setText(f'📋 当前表: {table_name}')
            self.row_count_label.setText(f'共 {self.table_total_rows} 行（已加载 {self.table_loaded_rows} 行）')
            self.table_load_more_btn.setVisible(has_more)
            self.table_widget.load_more_signal = self.load_more_table_data

            self.tab_widget.setCurrentWidget(self.table_tab)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法显示表数据: {str(e)}")

    def load_more_table_data(self):
        """加载更多表数据"""
        if not self.current_table or not self.conn or self.table_loaded_rows >= self.table_total_rows:
            return
        self.table_load_more_btn.setEnabled(False)
        self.table_load_more_btn.setText('加载中...')
        try:
            cursor = self.conn.cursor()
            offset = self.table_loaded_rows
            cursor.execute(f"SELECT * FROM '{self.current_table}' LIMIT {self.table_page_size} OFFSET {offset}")
            new_rows = cursor.fetchall()
            if new_rows:
                self.table_widget.model.add_data([list(row) for row in new_rows])
                self.table_loaded_rows += len(new_rows)
                self.row_count_label.setText(f'共 {self.table_total_rows} 行（已加载 {self.table_loaded_rows} 行）')
            if self.table_loaded_rows >= self.table_total_rows:
                self.table_load_more_btn.setVisible(False)
            else:
                self.table_load_more_btn.setEnabled(True)
                self.table_load_more_btn.setText('加载更多')
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载更多数据失败: {str(e)}")
            self.table_load_more_btn.setEnabled(True)
            self.table_load_more_btn.setText('加载更多')

    def search_in_table(self, search_text):
        """搜索表数据（优先用数据库查询）"""
        if not self.current_table or not self.conn:
            return
        search_text = search_text.strip().lower()
        selected_column = self.search_column_combo.currentIndex() - 1

        if not search_text:
            self.show_table_data(self.current_table)
            return

        try:
            cursor = self.conn.cursor()
            if self.table_loaded_rows < self.table_total_rows:
                # 未加载全量，用数据库查询
                if selected_column == -1:
                    cursor.execute(f"PRAGMA table_info('{self.current_table}')")
                    columns = [col[1] for col in cursor.fetchall()]
                    like_conditions = ' OR '.join([f'"{col}" LIKE ?' for col in columns])
                    sql = f'SELECT * FROM "{self.current_table}" WHERE {like_conditions} LIMIT {self.table_page_size}'
                    cursor.execute(sql, [f'%{search_text}%'] * len(columns))
                else:
                    col_name = self.table_columns[selected_column]
                    sql = f'SELECT * FROM "{self.current_table}" WHERE "{col_name}" LIKE ? LIMIT {self.table_page_size}'
                    cursor.execute(sql, [f'%{search_text}%'])
                
                rows = cursor.fetchall()
                # 获取匹配总数
                if selected_column == -1:
                    count_sql = f"SELECT COUNT(*) FROM \"{self.current_table}\" WHERE {' OR '.join([f'\"{col}\" LIKE ?' for col in columns])}"
                    cursor.execute(count_sql, [f'%{search_text}%'] * len(columns))
                else:
                    col_name = self.table_columns[selected_column]
                    count_sql = f'SELECT COUNT(*) FROM "{self.current_table}" WHERE "{col_name}" LIKE ?'
                    cursor.execute(count_sql, [f'%{search_text}%'])
                total_match = cursor.fetchone()[0]

                self.table_widget.model.set_data(
                    data=[list(row) for row in rows],
                    columns=self.table_columns,
                    total_rows=total_match,
                    has_more=len(rows) < total_match
                )
                self.table_loaded_rows = len(rows)
                self.table_total_rows = total_match
                self.row_count_label.setText(f'找到 {total_match} 行（已加载 {len(rows)} 行）')
                self.table_load_more_btn.setVisible(len(rows) < total_match)
            else:
                # 已加载全量，内存搜索
                filtered_rows = []
                for row in self.table_widget.model._data:
                    if selected_column == -1:
                        for value in row:
                            if search_text in str(value).lower():
                                filtered_rows.append(row)
                                break
                    else:
                        if selected_column < len(row) and search_text in str(row[selected_column]).lower():
                            filtered_rows.append(row)
                self.table_widget.model.set_data(
                    data=filtered_rows,
                    columns=self.table_columns,
                    total_rows=len(filtered_rows),
                    has_more=False
                )
                self.row_count_label.setText(f'找到 {len(filtered_rows)} 行')
                self.table_load_more_btn.setVisible(False)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"搜索失败: {str(e)}")

    def clear_data_search(self):
        """清除搜索"""
        self.data_search_input.clear()
        if self.current_table:
            self.show_table_data(self.current_table)

    def refresh_current_table(self):
        """刷新当前表"""
        if self.current_table:
            self.show_table_data(self.current_table)
            self.status_bar.showMessage(f'已刷新表: {self.current_table}', 3000)

    def show_tree_context_menu(self, position):
        """树右键菜单"""
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
        """执行SQL（大结果提示+分批加载）"""
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
                total_rows = len(rows)
                self.sql_result_total = total_rows
                self.sql_result_loaded = 0

                # 大结果提示
                if total_rows > 1000:
                    reply = QMessageBox.question(
                        self, '提示',
                        f'查询返回 {total_rows} 行数据，加载全部可能耗时较久，是否仅加载前1000行？',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        rows = rows[:1000]
                        total_rows = 1000
                        has_more = True
                    else:
                        has_more = False
                else:
                    has_more = False

                self.result_table.model.set_data(
                    data=[list(row) for row in rows],
                    columns=columns,
                    total_rows=total_rows,
                    has_more=has_more
                )
                self.sql_result_loaded = len(rows)
                self.sql_result_count_label.setText(f'共 {total_rows} 行（已加载 {len(rows)} 行）')
                self.sql_load_more_btn.setVisible(has_more)
                self.result_table.load_more_signal = self.load_more_sql_result

                self.status_bar.showMessage(f'查询返回 {total_rows} 行结果', 3000)
            else:
                self.conn.commit()
                self.status_bar.showMessage(f'SQL执行成功，影响了 {cursor.rowcount} 行', 3000)
                self.refresh_db_tree()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"SQL执行错误: {str(e)}")

    def load_more_sql_result(self):
        """加载更多SQL结果"""
        if not self.conn or self.sql_result_loaded >= self.sql_result_total:
            return
        self.sql_load_more_btn.setEnabled(False)
        self.sql_load_more_btn.setText('加载中...')
        try:
            cursor = self.conn.cursor()
            sql = self.sql_editor.toPlainText().strip()
            offset = self.sql_result_loaded
            cursor.execute(f"{sql} LIMIT {self.table_page_size} OFFSET {offset}")
            new_rows = cursor.fetchall()
            if new_rows:
                self.result_table.model.add_data([list(row) for row in new_rows])
                self.sql_result_loaded += len(new_rows)
                self.sql_result_count_label.setText(f'共 {self.sql_result_total} 行（已加载 {self.sql_result_loaded} 行）')
            if self.sql_result_loaded >= self.sql_result_total:
                self.sql_load_more_btn.setVisible(False)
            else:
                self.sql_load_more_btn.setEnabled(True)
                self.sql_load_more_btn.setText('加载更多')
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载更多结果失败: {str(e)}")
            self.sql_load_more_btn.setEnabled(True)
            self.sql_load_more_btn.setText('加载更多')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    db_manager = DBManager()
    db_manager.show()
    sys.exit(app.exec_())