import sys
import os
import re
import sqlite3
import time
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QHeaderView, QMessageBox, QTabWidget, 
                             QLabel, QLineEdit, QComboBox, QFileDialog, QSplitter, 
                             QTreeWidget, QTreeWidgetItem, QMenu, QStatusBar, 
                             QToolBar, QTextEdit, QFrame, QSizePolicy, QAbstractItemView,
                             QCheckBox, QGroupBox, QScrollArea, QDialog)
from PyQt6.QtCore import Qt, QSize, QThreadPool, QRunnable, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from ..core.config import (ICON_PATH, CSS_PATH, TABLE_PAGE_SIZE, SQL_RESULT_PROMPT_THRESHOLD,
                   USE_PRAGMA_WAL, USE_PRAGMA_JOURNAL_MODE, USE_PRAGMA_SYNCHRONOUS,
                   USE_PRAGMA_TEMP_STORE, USE_PRAGMA_MMAP_SIZE, SQL_TIMEOUT,
                   MAX_CONCURRENT_QUERIES)
from .components import SearchLineEdit, VirtualTableWidget
from .dialogs import QueryWizardDialog
from .custom_dialogs import show_error, show_warning
from ..core.version import VERSION, VERSION_DESCRIPTION, BUILD_DATE, AUTHOR
from ..core.db_manager import DatabaseConnection
from .db_connect_dialog import DatabaseConnectDialog


class TableDataTask(QRunnable):
    """异步表格数据加载任务
    
    在后台线程完成列信息、总行数与分页查询，结果通过信号在主线程派发，
    避免点击树节点或滚动加载时阻塞UI。
    """
    query_finished = pyqtSignal(object, int, object, object)

    def __init__(self, conn, table_name, page_size, offset):
        super().__init__()
        self.conn = conn
        self.table_name = table_name
        self.page_size = page_size
        self.offset = offset
        self.setAutoDelete(True)

    def run(self):
        error = None
        columns = []
        rows = []
        total_rows = 0
        try:
            if isinstance(self.conn, DatabaseConnection):
                info = self.conn.get_table_info(self.table_name)
                columns = [col[0] for col in info]
                cursor = self.conn.cursor
            else:
                cursor = self.conn.cursor()
                cursor.execute(f"PRAGMA table_info('{self.table_name}')")
                columns = [col[1] for col in cursor.fetchall()]

            cursor.execute(f"SELECT COUNT(*) FROM '{self.table_name}'")
            total_rows = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT * FROM '{self.table_name}' LIMIT {self.page_size} OFFSET {self.offset}"
            )
            raw_rows = cursor.fetchall()
            rows = [list(r) for r in raw_rows]
        except Exception as e:
            error = str(e)
        self.query_finished.emit(columns, total_rows, rows, error)


class QueryTask(QRunnable):
    """异步查询任务类
    
    用于在后台线程执行SQL查询，避免阻塞UI。
    结果通过 query_finished 信号在主线程派发，避免跨线程操作UI。
    """
    query_finished = pyqtSignal(object, object, int, object)

    def __init__(self, conn, sql):
        super().__init__()
        self.conn = conn
        self.sql = sql
        self.setAutoDelete(True)

    def run(self):
        error = None
        try:
            if isinstance(self.conn, DatabaseConnection):
                cursor = self.conn.cursor
            else:
                cursor = self.conn.cursor()
            cursor.execute(self.sql)
            first_word = self.sql.split(None, 1)[0].upper() if self.sql.split() else ''
            if first_word in ('SELECT', 'WITH', 'PRAGMA', 'EXPLAIN', 'VALUES'):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                self.query_finished.emit([list(r) for r in rows], columns, len(rows), None)
            else:
                if hasattr(self.conn, 'commit'):
                    self.conn.commit()
                self.query_finished.emit(None, None, cursor.rowcount, None)
        except Exception as e:
            error = str(e)
            self.query_finished.emit(None, None, -1, error)


class DBManager(QMainWindow):
    """数据库管理器主窗口
    
    功能:
    - 打开/关闭数据库
    - 浏览数据库对象树
    - 查看和编辑表数据
    - 执行自定义SQL查询
    - 使用查询向导构建SQL
    - 支持虚拟表格和分批加载
    - 支持网络数据库连接
    """
    def __init__(self):
        super().__init__()
        self.current_db = None
        self.conn = None
        self.current_table = None
        self.table_total_rows = 0
        self.table_loaded_rows = 0
        self.table_columns = []
        self.sql_result_total = 0
        self.sql_result_loaded = 0
        self.sql_result_sql = ''
        
        # 性能优化相关初始化
        self.thread_pool = QThreadPool.globalInstance()
        self.active_queries = 0
        self.query_queue = []
        
        self.init_ui()

    def _close_current_connection(self):
        """关闭当前数据库连接

        兼容 sqlite3 连接（close方法）与 DatabaseConnection（disconnect方法），
        避免切换数据库时对网络数据库连接调用不存在的 close() 导致 AttributeError
        """
        if self.conn is None:
            return
        try:
            if hasattr(self.conn, 'disconnect'):
                self.conn.disconnect()
            else:
                self.conn.close()
        except Exception as e:
            print(f"关闭旧数据库连接失败: {str(e)}")
        self.conn = None

    def _get_cursor(self):
        """获取当前连接的游标

        兼容 sqlite3 连接（cursor为方法）与 DatabaseConnection（cursor为属性），
        修复连接网络数据库后 cursor() 被错误调用导致的 TypeError
        """
        if isinstance(self.conn, DatabaseConnection):
            return self.conn.cursor
        return self.conn.cursor()

    def init_ui(self):
        """初始化用户界面
        
        创建主窗口布局,包括:
        - 工具栏(打开/关闭数据库)
        - 左侧数据库对象树
        - 右侧数据表和SQL查询选项卡
        """
        self.setWindowTitle(f'SQLite 数据库查看工具 v{VERSION}')
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(80, 80, 1000, 650)
        self.setMinimumSize(800, 500)

        try:
            with open(CSS_PATH, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
        except Exception as e:
            QMessageBox.warning(self, '样式加载失败', f'无法加载style.css：{str(e)}\n请确保style.css和程序在同一目录下')

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        toolbar = QToolBar()
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.open_db_action = QAction('📂 打开数据库', self)
        self.open_db_action.triggered.connect(self.open_database)
        toolbar.addAction(self.open_db_action)

        self.open_net_db_action = QAction('🌐 连接网络数据库', self)
        self.open_net_db_action.triggered.connect(self.open_network_database)
        toolbar.addAction(self.open_net_db_action)

        toolbar.addSeparator()

        self.close_db_action = QAction('✖ 关闭数据库', self)
        self.close_db_action.setObjectName('dangerAction')
        self.close_db_action.triggered.connect(self.close_database)
        toolbar.addAction(self.close_db_action)

        toolbar.addSeparator()

        self.refresh_db_action = QAction('🔄 刷新', self)
        self.refresh_db_action.triggered.connect(self.refresh_current_table)
        toolbar.addAction(self.refresh_db_action)

        toolbar.addSeparator()

        about_action = QAction('ℹ 关于', self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)

        self._refresh_toolbar_state()

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        main_layout.addWidget(splitter)

        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(4)
        left_panel.setLayout(left_layout)

        left_title = QLabel('🗄️ 数据库对象')
        left_title.setObjectName('titleLabel')
        left_layout.addWidget(left_title)

        self.tree_search_input = SearchLineEdit('🔍 搜索表名...')
        self.tree_search_input.textChanged.connect(self._on_tree_search_changed)
        left_layout.addWidget(self.tree_search_input)

        # 树搜索防抖定时器，避免每次按键都遍历整棵树
        self._tree_search_timer = QTimer(self)
        self._tree_search_timer.setSingleShot(True)
        self._tree_search_timer.setInterval(150)
        self._tree_search_timer.timeout.connect(self.filter_db_tree)

        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderLabels(['数据库对象'])
        self.db_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.db_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.db_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.db_tree.setIndentation(16)
        self.db_tree.setAnimated(True)
        self.db_tree.itemExpanded.connect(self.on_tree_item_expanded)
        left_layout.addWidget(self.db_tree)

        splitter.addWidget(left_panel)

        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(2, 0, 0, 0)
        right_layout.setSpacing(0)
        right_panel.setLayout(right_layout)

        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)

        # 数据表选项卡
        self.table_tab = QWidget()
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(4, 4, 4, 4)
        table_layout.setSpacing(6)
        self.table_tab.setLayout(table_layout)

        search_frame = QFrame()
        search_frame.setObjectName('searchFrame')
        search_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(6)
        search_frame.setLayout(search_layout)

        self.current_table_label = QLabel('📋 当前表: 无')
        self.current_table_label.setObjectName('titleLabel')
        search_layout.addWidget(self.current_table_label)
        search_layout.addStretch()

        table_layout.addWidget(search_frame)

        self.table_widget = VirtualTableWidget()
        self.table_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table_layout.addWidget(self.table_widget)

        table_action_layout = QHBoxLayout()
        table_action_layout.setSpacing(8)

        self.row_count_label = QLabel('共 0 行')
        self.row_count_label.setObjectName('countLabel')
        table_action_layout.addWidget(self.row_count_label)
        table_action_layout.addStretch()

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

        # SQL编辑器选项卡（完全保留，无改动）
        self.sql_tab = QWidget()
        sql_layout = QVBoxLayout()
        sql_layout.setContentsMargins(4, 4, 4, 4)
        sql_layout.setSpacing(6)
        self.sql_tab.setLayout(sql_layout)

        sql_header_layout = QHBoxLayout()
        sql_header_layout.setSpacing(12)
        sql_title = QLabel('💻 SQL 查询编辑器')
        sql_title.setObjectName('titleLabel')
        sql_header_layout.addWidget(sql_title)
        
        # 添加SQL示例下拉菜单
        sql_examples = QComboBox()
        sql_examples.addItems([
            "选择SQL示例...",
            "SELECT * FROM table_name",
            "SELECT column1, column2 FROM table_name",
            "SELECT * FROM table_name WHERE condition",
            "SELECT * FROM table_name ORDER BY column",
            "SELECT COUNT(*) FROM table_name",
            "SELECT DISTINCT column FROM table_name",
            "SELECT column FROM table_name LIMIT 10"
        ])
        sql_examples.setMinimumWidth(180)
        sql_examples.currentIndexChanged.connect(self.on_sql_example_selected)
        sql_header_layout.addWidget(sql_examples)
        
        query_wizard_btn = QPushButton('🔍 查询向导')
        query_wizard_btn.setObjectName('wizardButton')
        query_wizard_btn.clicked.connect(self.open_query_wizard)
        sql_header_layout.addWidget(query_wizard_btn)
        
        # 添加格式化按钮
        format_btn = QPushButton('📝 格式化')
        format_btn.setObjectName('formatButton')
        format_btn.setMinimumWidth(80)
        format_btn.clicked.connect(self.format_sql)
        sql_header_layout.addWidget(format_btn)

        sql_header_layout.addStretch()
        sql_layout.addLayout(sql_header_layout)

        self.sql_editor = QTextEdit()
        self.sql_editor.setObjectName('sqlEditor')
        self.sql_editor.setPlaceholderText('输入 SQL 查询语句...\n\n例如: SELECT * FROM table_name WHERE id > 10')
        self.sql_editor.setMinimumHeight(120)
        self.sql_editor.setMaximumHeight(400)
        self.sql_editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sql_layout.addWidget(self.sql_editor)

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

        result_title = QLabel('📋 查询结果')
        result_title.setObjectName('titleLabel')
        sql_layout.addWidget(result_title)

        self.result_table = VirtualTableWidget()
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sql_layout.addWidget(self.result_table)

        sql_result_action_layout = QHBoxLayout()
        sql_result_action_layout.setSpacing(8)
        self.sql_result_count_label = QLabel('共 0 行')
        self.sql_result_count_label.setObjectName('countLabel')
        sql_result_action_layout.addWidget(self.sql_result_count_label)
        sql_result_action_layout.addStretch()
        self.sql_load_more_btn = QPushButton('加载更多')
        self.sql_load_more_btn.setObjectName('successButton')
        self.sql_load_more_btn.setMinimumWidth(80)
        self.sql_load_more_btn.clicked.connect(self.load_more_sql_result)
        self.sql_load_more_btn.setVisible(False)
        sql_result_action_layout.addWidget(self.sql_load_more_btn)
        sql_layout.addLayout(sql_result_action_layout)

        sql_layout.setStretchFactor(sql_title, 0)
        sql_layout.setStretchFactor(self.sql_editor, 1)
        sql_layout.setStretchFactor(sql_btn_layout, 0)
        sql_layout.setStretchFactor(result_title, 0)
        sql_layout.setStretchFactor(self.result_table, 3)

        self.tab_widget.addTab(self.sql_tab, '💻 SQL查询')

        splitter.addWidget(right_panel)
        splitter.setSizes([200, 800])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.update_ui_state()

    def on_tree_item_expanded(self, item):
        """当树形节点展开时加载列信息
        
        Args:
            item: 被展开的树形节点
        """
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == 'table':
            if item.data(0, Qt.ItemDataRole.UserRole + 2) == 'columns_loaded':
                return
            table_name = item.data(0, Qt.ItemDataRole.UserRole + 1)
            try:
                if isinstance(self.conn, DatabaseConnection):
                    columns = self.conn.get_table_info(table_name)
                    for col in columns:
                        col_item = QTreeWidgetItem(item)
                        col_item.setText(0, f'{col[0]} ({col[1]})')
                        col_item.setData(0, Qt.ItemDataRole.UserRole, 'column')
                else:
                    cursor = self._get_cursor()
                    cursor.execute(f"PRAGMA table_info('{table_name}')")
                    columns = cursor.fetchall()
                    for col in columns:
                        col_name = col[1]
                        col_type = col[2]
                        is_pk = '🔑 ' if col[5] else ''
                        col_item = QTreeWidgetItem(item)
                        col_item.setText(0, f'{is_pk}{col_name} ({col_type})')
                        col_item.setData(0, Qt.ItemDataRole.UserRole, 'column')
                item.setData(0, Qt.ItemDataRole.UserRole + 2, 'columns_loaded')
            except Exception:
                pass

    def open_query_wizard(self):
        """打开查询向导弹窗
        
        如果查询成功,将生成的SQL填入编辑器并执行
        """
        if not self.conn:
            QMessageBox.warning(self, '警告', '请先打开数据库')
            return
        dialog = QueryWizardDialog(self.conn, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            sql = dialog.generated_sql
            if sql:
                self.sql_editor.setPlainText(sql)
                self.execute_sql()
                self.tab_widget.setCurrentWidget(self.sql_tab)
                self.status_bar.showMessage('查询向导已生成并执行查询', 3000)

    def _refresh_toolbar_state(self):
        """根据数据库连接状态启用/禁用工具栏按钮"""
        has_db = self.conn is not None
        self.close_db_action.setEnabled(has_db)
        self.refresh_db_action.setEnabled(has_db)

    def update_ui_state(self):
        """根据数据库连接状态更新UI

        更新状态栏和控件可用性
        """
        self._refresh_toolbar_state()
        has_db = self.conn is not None
        if has_db:
            self.status_bar.showMessage(f'当前数据库: {self.current_db}')
        else:
            self.status_bar.showMessage('未打开数据库 - 请打开一个数据库文件')

    def open_database(self):
        """打开SQLite数据库文件
        
        支持格式: .db, .sqlite, .sqlite3
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self, "打开SQLite数据库", "", "SQLite数据库 (*.db *.sqlite *.sqlite3);;所有文件 (*)")
        
        if file_name:
            try:
                self._close_current_connection()
                self.current_db = file_name
                self.conn = sqlite3.connect(file_name)
                self.refresh_db_tree()
                self.update_ui_state()
                self.status_bar.showMessage(f'已打开数据库: {file_name}', 3000)
            except Exception as e:
                self.conn = None
                self.current_db = None
                show_error("错误", f"无法打开数据库: {str(e)}", self)

    def open_network_database(self):
        """打开网络数据库连接
        
        支持MySQL和PostgreSQL数据库
        """
        dialog = DatabaseConnectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            connection_params = dialog.get_connection_params()
            if connection_params:
                try:
                    self._close_current_connection()
                    
                    # 使用新的数据库连接管理器
                    db_type = connection_params["type"]
                    db_params = connection_params["params"]
                    
                    self.current_db = f"{db_type}://{db_params.get('host', 'localhost')}:{db_params.get('port', 3306)}/{db_params.get('database', '')}"
                    
                    # 创建数据库连接
                    self.conn = DatabaseConnection(db_type, db_params)
                    if self.conn.connect():
                        self.refresh_db_tree()
                        self.update_ui_state()
                        self.status_bar.showMessage(f"已连接到数据库: {self.current_db}", 3000)
                    else:
                        show_error("错误", "无法连接到数据库，请检查连接参数", self)
                        self.conn = None
                except Exception as e:
                    show_error("错误", f"无法连接到数据库: {str(e)}", self)

    def close_database(self):
        """关闭当前数据库连接
        
        清空所有数据和UI状态
        """
        if self.conn:
            # 使用数据库连接管理器的断开连接方法
            if hasattr(self.conn, "disconnect"):
                self.conn.disconnect()
            else:
                self.conn.close()
            self.conn = None
            self.current_db = None
            self.current_table = None
            self.table_total_rows = 0
            self.table_loaded_rows = 0
            self.sql_result_total = 0
            self.sql_result_loaded = 0
            self.sql_result_sql = ''
            self.refresh_db_tree()
            self.table_widget.model.set_data([], [], 0)
            self.result_table.model.set_data([], [], 0)
            self.current_table_label.setText('📋 当前表: 无')
            self.row_count_label.setText('共 0 行')
            self.table_load_more_btn.setVisible(False)
            self.sql_result_count_label.setText('共 0 行')
            self.sql_load_more_btn.setVisible(False)
            self.update_ui_state()
            self.status_bar.showMessage('已关闭数据库', 3000)

    def refresh_db_tree(self):
        """刷新数据库对象树
        
        重新加载所有表和视图
        """
        self.db_tree.clear()
        if not self.conn:
            return

        db_display_name = os.path.basename(self.current_db) if self.current_db else '数据库'
        db_item = QTreeWidgetItem(self.db_tree)
        db_item.setText(0, f'💾 {db_display_name}')
        db_item.setData(0, Qt.ItemDataRole.UserRole, 'database')
        db_item.setData(0, Qt.ItemDataRole.UserRole + 1, self.current_db)

        try:
            # 检查是否是新的数据库连接管理器
            if hasattr(self.conn, "get_tables"):
                # 使用新连接管理器的方法获取表列表
                tables = self.conn.get_tables()
                tables_group = QTreeWidgetItem(db_item)
                tables_group.setText(0, '📊 表')
                tables_group.setData(0, Qt.ItemDataRole.UserRole, 'tables_group')

                for table_name in tables:
                    table_item = QTreeWidgetItem(tables_group)
                    table_item.setText(0, f'📋 {table_name}')
                    table_item.setData(0, Qt.ItemDataRole.UserRole, 'table')
                    table_item.setData(0, Qt.ItemDataRole.UserRole + 1, table_name)
                    table_item.setData(0, Qt.ItemDataRole.UserRole + 2, 'columns_not_loaded')
            else:
                # 使用原有方法处理SQLite数据库
                cursor = self.conn.cursor()
                tables_group = QTreeWidgetItem(db_item)
                tables_group.setText(0, '📊 表')
                tables_group.setData(0, Qt.ItemDataRole.UserRole, 'tables_group')

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                tables = cursor.fetchall()
                for table in tables:
                    table_name = table[0]
                    table_item = QTreeWidgetItem(tables_group)
                    table_item.setText(0, f'📋 {table_name}')
                    table_item.setData(0, Qt.ItemDataRole.UserRole, 'table')
                    table_item.setData(0, Qt.ItemDataRole.UserRole + 1, table_name)
                    table_item.setData(0, Qt.ItemDataRole.UserRole + 2, 'columns_not_loaded')

            self.db_tree.expandItem(db_item)
            self.filter_db_tree(self.tree_search_input.text())
        except Exception as e:
            show_error("错误", f"无法刷新数据库对象树: {str(e)}", self)

    def _on_tree_search_changed(self):
        """树搜索文本变化时触发防抖"""
        self._tree_search_timer.start()

    def filter_db_tree(self, search_text):
        """根据搜索文本过滤数据库对象树
        
        Args:
            search_text: 搜索关键词
        """
        search_text = search_text.strip().lower()

        def process_items(parent):
            any_visible = False
            for i in range(parent.childCount()):
                child = parent.child(i)
                child_type = child.data(0, Qt.ItemDataRole.UserRole)
                if child_type in ('tables_group', 'views_group'):
                    has_visible = process_items(child)
                    child.setHidden(not has_visible)
                    if has_visible:
                        any_visible = True
                elif child_type == 'table':
                    table_name = child.data(0, Qt.ItemDataRole.UserRole + 1) or child.text(0)
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
                    view_name = child.data(0, Qt.ItemDataRole.UserRole + 1) or child.text(0)
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
        """处理树形节点点击事件
        
        Args:
            item: 被点击的节点
            column: 点击的列索引
        """
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        if item_type == 'table':
            table_name = item.data(0, Qt.ItemDataRole.UserRole + 1) or item.text(0)
            for emoji in ['📋 ']:
                table_name = table_name.replace(emoji, '')
            self.show_table_data(table_name)

    def show_table_data(self, table_name):
        """显示指定表的数据（异步，避免阻塞UI）
        
        Args:
            table_name: 表名
        """
        if not self.conn:
            return

        self.status_bar.showMessage(f'正在加载表 {table_name} ...', 0)
        self.table_load_more_btn.setVisible(False)

        def on_finished(columns, total_rows, rows, error):
            """表数据加载完成回调（在主线程执行）"""
            self.active_queries = max(0, self.active_queries - 1)
            self.status_bar.clearMessage()
            self.table_load_more_btn.setEnabled(True)

            if error is not None:
                show_error("错误", f"无法显示表数据: {error}", self)
                return

            self.current_table = table_name
            self.table_columns = columns
            self.table_total_rows = total_rows
            self.table_loaded_rows = len(rows)
            has_more = self.table_loaded_rows < self.table_total_rows

            self.table_widget.model.set_data(
                data=rows,
                columns=self.table_columns,
                total_rows=self.table_total_rows,
                has_more=has_more
            )

            self.current_table_label.setText(f'📋 当前表: {table_name}')
            self.row_count_label.setText(f'共 {self.table_total_rows} 行（已加载 {self.table_loaded_rows} 行）')
            self.table_load_more_btn.setVisible(has_more)
            self.table_widget.load_more_signal = self.load_more_table_data

            self.tab_widget.setCurrentWidget(self.table_tab)
            self.status_bar.showMessage(f'表 {table_name} 共 {total_rows} 行', 3000)

        query_task = TableDataTask(self.conn, table_name, TABLE_PAGE_SIZE, 0)
        query_task.query_finished.connect(on_finished)
        self.thread_pool.start(query_task)
        self.active_queries += 1

    def load_more_table_data(self):
        """异步加载更多表数据
        
        使用分页加载避免一次性加载大量数据
        """
        if not self.current_table or not self.conn or self.table_loaded_rows >= self.table_total_rows:
            return
        self.table_load_more_btn.setEnabled(False)
        self.table_load_more_btn.setText('加载中...')

        def on_finished(columns, total_rows, new_rows, error):
            self.table_load_more_btn.setEnabled(True)
            self.table_load_more_btn.setText('加载更多')
            if error is not None:
                show_error("错误", f"加载更多数据失败: {error}", self)
                return
            if new_rows:
                self.table_widget.model.add_data(new_rows)
                self.table_loaded_rows += len(new_rows)
                self.row_count_label.setText(f'共 {self.table_total_rows} 行（已加载 {self.table_loaded_rows} 行）')
            if self.table_loaded_rows >= self.table_total_rows:
                self.table_load_more_btn.setVisible(False)
            else:
                self.table_load_more_btn.setEnabled(True)
                self.table_load_more_btn.setText('加载更多')

        query_task = TableDataTask(self.conn, self.current_table, TABLE_PAGE_SIZE, self.table_loaded_rows)
        query_task.query_finished.connect(on_finished)
        self.thread_pool.start(query_task)
        self.active_queries += 1

    def refresh_current_table(self):
        """刷新当前表的数据
        
        重新加载当前表的所有数据
        """
        if self.current_table:
            self.show_table_data(self.current_table)
            self.status_bar.showMessage(f'已刷新表: {self.current_table}', 3000)

    def show_tree_context_menu(self, position):
        """显示树形节点的右键菜单
        
        Args:
            position: 鼠标点击位置
        """
        item = self.db_tree.itemAt(position)
        if not item:
            return
        item_type = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu()
        if item_type == 'database':
            refresh_action = QAction('🔄 刷新', self)
            refresh_action.triggered.connect(self.refresh_db_tree)
            menu.addAction(refresh_action)
        menu.exec(self.db_tree.mapToGlobal(position))

    def on_sql_example_selected(self, index):
        """处理SQL示例选择事件
        
        Args:
            index: 选择的索引
        """
        if index <= 0:  # 第一个是提示文本
            return
            
        examples = [
            "",  # 空字符串对应提示文本
            "SELECT * FROM table_name",
            "SELECT column1, column2 FROM table_name",
            "SELECT * FROM table_name WHERE condition",
            "SELECT * FROM table_name ORDER BY column",
            "SELECT COUNT(*) FROM table_name",
            "SELECT DISTINCT column FROM table_name",
            "SELECT column FROM table_name LIMIT 10"
        ]
        
        if index < len(examples):
            self.sql_editor.setPlainText(examples[index])
    
    def format_sql(self):
        """格式化SQL查询语句

        基于正则的SQL格式化:
        - 关键字大写(大小写不敏感,且不破坏字符串字面量与标识符)
        - 主要子句换行缩进,提升可读性
        """
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "警告", "请输入SQL查询语句")
            return

        # 保护字符串字面量,避免格式化破坏其内容
        strings = []

        def _protect(match):
            strings.append(match.group(0))
            return f'__SQLSTR_{len(strings) - 1}__'

        protected = re.sub(r"'(?:[^']|'')*'", _protect, sql)

        # 关键字大写(使用单词边界,大小写不敏感)
        keywords = ["SELECT", "FROM", "WHERE", "AND", "OR", "ORDER BY", "GROUP BY",
                    "HAVING", "LIMIT", "INSERT INTO", "VALUES", "UPDATE", "SET",
                    "DELETE FROM", "CREATE TABLE", "ALTER TABLE", "DROP TABLE",
                    "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN",
                    "JOIN", "UNION ALL", "UNION", "DISTINCT", "ON", "AS", "ASC", "DESC"]
        for keyword in keywords:
            pattern = re.compile(re.escape(keyword).replace(r'\ ', r'\s+'), re.IGNORECASE)
            protected = pattern.sub(keyword.upper(), protected)

        # 主要子句前换行
        protected = re.sub(r'\bFROM\b', '\nFROM', protected)
        protected = re.sub(r'\bWHERE\b', '\nWHERE', protected)
        protected = re.sub(r'\b(ORDER BY|GROUP BY|HAVING)\b', r'\n\1', protected)
        protected = re.sub(r'\b(LIMIT|OFFSET)\b', r'\n\1', protected)
        protected = protected.replace(',', ',\n    ')

        # 还原字符串字面量
        formatted_sql = protected
        for i, value in enumerate(strings):
            formatted_sql = formatted_sql.replace(f'__SQLSTR_{i}__', value)

        self.sql_editor.setPlainText(formatted_sql)
        self.status_bar.showMessage("SQL已格式化", 3000)
    
    def execute_sql(self):
        """执行SQL查询语句（异步，避免阻塞UI）
        
        支持SELECT查询,结果在下方表格中显示
        """
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "警告", "请输入SQL查询语句")
            return
        if not self.conn:
            QMessageBox.warning(self, "警告", "请先打开数据库")
            return

        # 设置加载中状态
        self.status_bar.showMessage('正在执行查询...', 0)
        self.sql_load_more_btn.setVisible(False)

        def on_finished(rows, columns, total_rows, error):
            """查询完成回调（在主线程执行）"""
            self.active_queries = max(0, self.active_queries - 1)
            self.status_bar.clearMessage()
            self.sql_load_more_btn.setEnabled(True)
            self.sql_load_more_btn.setText('加载更多')

            if error is not None:
                show_error("错误", f"SQL执行错误: {error}", self)
                return

            first_word = sql.split(None, 1)[0].upper() if sql.split() else ''
            if first_word in ('SELECT', 'WITH', 'PRAGMA', 'EXPLAIN', 'VALUES'):
                self.sql_result_total = total_rows
                self.sql_result_loaded = 0
                self.sql_result_sql = sql

                if total_rows > SQL_RESULT_PROMPT_THRESHOLD:
                    reply = QMessageBox.question(
                        self, '提示',
                        f'查询返回 {total_rows} 行数据，加载全部可能耗时较久，是否仅加载前{TABLE_PAGE_SIZE}行？',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        rows = rows[:TABLE_PAGE_SIZE]
                        has_more = True
                    else:
                        has_more = False
                else:
                    has_more = False

                self.result_table.model.set_data(
                    data=rows,
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
                self.status_bar.showMessage(f'SQL执行成功，影响了 {total_rows} 行', 3000)
                self.refresh_db_tree()

        query_task = QueryTask(self.conn, sql)
        query_task.query_finished.connect(on_finished)
        self.thread_pool.start(query_task)
        self.active_queries += 1

    def show_about(self):
        """显示关于对话框
        
        显示应用程序版本和相关信息
        """
        about_text = f"""<h2>SQLite 数据库查看工具 v{VERSION}</h2>
<p>{VERSION_DESCRIPTION}</p>

<p><b>版本:</b> {VERSION}</p>
<p><b>构建日期:</b> {BUILD_DATE}</p>
<p><b>作者:</b> {AUTHOR}</p>

<p>本程序是一个轻量级的SQLite数据库查看和管理工具，支持浏览数据库结构、查看表数据和执行SQL查询。</p>

<p>© 2023-2026 {AUTHOR}. 保留所有权利。</p>"""
        from custom_dialogs import show_info
        show_info("关于 SQLite 数据库查看工具", about_text, self)
    
    def load_more_sql_result(self):
        """异步加载更多SQL查询结果"""
        if not self.conn or self.sql_result_loaded >= self.sql_result_total:
            return
        self.sql_load_more_btn.setEnabled(False)
        self.sql_load_more_btn.setText('加载中...')

        def on_finished(rows, columns, total_rows, error):
            self.sql_load_more_btn.setEnabled(True)
            self.sql_load_more_btn.setText('加载更多')
            if error is not None:
                show_error("错误", f"加载更多结果失败: {error}", self)
                return
            if new_rows := rows:
                self.result_table.model.add_data(new_rows)
                self.sql_result_loaded += len(new_rows)
                self.sql_result_count_label.setText(f'共 {total_rows} 行（已加载 {self.sql_result_loaded} 行）')
            if self.sql_result_loaded >= self.sql_result_total:
                self.sql_load_more_btn.setVisible(False)
            else:
                self.sql_load_more_btn.setEnabled(True)
                self.sql_load_more_btn.setText('加载更多')

        sql = getattr(self, 'sql_result_sql', '') or self.sql_editor.toPlainText().strip()
        base_sql = sql.rstrip().rstrip(';')
        offset = self.sql_result_loaded
        page_sql = f"SELECT * FROM ({base_sql}) LIMIT {TABLE_PAGE_SIZE} OFFSET {offset}"

        query_task = QueryTask(self.conn, page_sql)
        query_task.query_finished.connect(on_finished)
        self.thread_pool.start(query_task)
        self.active_queries += 1