import sys
import os
import sqlite3
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QHeaderView, QMessageBox, QTabWidget, 
                             QLabel, QLineEdit, QComboBox, QFileDialog, QSplitter, 
                             QTreeWidget, QTreeWidgetItem, QMenu, QAction, QStatusBar, 
                             QToolBar, QTextEdit, QFrame, QSizePolicy, QAbstractItemView,
                             QCheckBox, QGroupBox, QScrollArea, QDialog)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from config import ICON_PATH, CSS_PATH, TABLE_PAGE_SIZE, SQL_RESULT_PROMPT_THRESHOLD
from components import SearchLineEdit, VirtualTableWidget
from dialogs import QueryWizardDialog

# ==================== Numba 加速工具（内置，无需单独文件） ====================
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    # 未安装Numba时自动降级为纯Python，不影响功能
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    NUMBA_AVAILABLE = False


@njit(cache=True, fastmath=True)
def _numba_search_rows(
    data,  # 二维列表，Numba自动推导类型
    search_text: str,
    selected_column: int
):
    """Numba加速的内存搜索核心逻辑，返回匹配行索引"""
    matched_indices = []
    total_rows = len(data)
    total_cols = len(data[0]) if total_rows > 0 else 0

    for row_idx in range(total_rows):
        row = data[row_idx]
        if selected_column == -1:
            # 全列搜索：任意列匹配即命中
            for col_idx in range(total_cols):
                cell = row[col_idx]
                if cell is not None and search_text in str(cell).lower():
                    matched_indices.append(row_idx)
                    break
        else:
            # 指定列搜索
            if selected_column < total_cols:
                cell = row[selected_column]
                if cell is not None and search_text in str(cell).lower():
                    matched_indices.append(row_idx)
    return matched_indices


def fast_search_in_memory(data, search_text: str, selected_column: int):
    """
    对外暴露的加速搜索接口，自动兼容Numba/纯Python模式
    """
    if not NUMBA_AVAILABLE or not search_text:
        # 降级为原纯Python逻辑
        if not search_text:
            return data
        filtered_rows = []
        for row in data:
            if selected_column == -1:
                for value in row:
                    if search_text in str(value).lower():
                        filtered_rows.append(row)
                        break
            else:
                if selected_column < len(row) and search_text in str(row[selected_column]).lower():
                    filtered_rows.append(row)
        return filtered_rows
    
    # 调用Numba加速
    search_text_lower = search_text.lower()
    matched_indices = _numba_search_rows(data, search_text_lower, selected_column)
    return [data[idx] for idx in matched_indices]


class DBManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_db = None
        self.conn = None
        self.current_table = None
        # 表数据相关
        self.table_total_rows = 0
        self.table_loaded_rows = 0
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
            cursor.execute(f"SELECT * FROM '{table_name}' LIMIT {TABLE_PAGE_SIZE}")
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
            cursor.execute(f"SELECT * FROM '{self.current_table}' LIMIT {TABLE_PAGE_SIZE} OFFSET {offset}")
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
                    sql = f'SELECT * FROM "{self.current_table}" WHERE {like_conditions} LIMIT {TABLE_PAGE_SIZE}'
                    cursor.execute(sql, [f'%{search_text}%'] * len(columns))
                else:
                    col_name = self.table_columns[selected_column]
                    sql = f'SELECT * FROM "{self.current_table}" WHERE "{col_name}" LIKE ? LIMIT {TABLE_PAGE_SIZE}'
                    cursor.execute(sql, [f'%{search_text}%'])
                
                rows = cursor.fetchall()
                # 获取匹配总数
                if selected_column == -1:
                    like_where = ' OR '.join([f'"{col}" LIKE ?' for col in columns])
                    count_sql = f'SELECT COUNT(*) FROM "{self.current_table}" WHERE {like_where}'
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
                # ========== 修改点：调用内置Numba加速的内存搜索 ==========
                filtered_rows = fast_search_in_memory(
                    data=self.table_widget.model._data,
                    search_text=search_text,
                    selected_column=selected_column
                )
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
                if total_rows > SQL_RESULT_PROMPT_THRESHOLD:
                    reply = QMessageBox.question(
                        self, '提示',
                        f'查询返回 {total_rows} 行数据，加载全部可能耗时较久，是否仅加载前{TABLE_PAGE_SIZE}行？',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        rows = rows[:TABLE_PAGE_SIZE]
                        total_rows = TABLE_PAGE_SIZE
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
            cursor.execute(f"{sql} LIMIT {TABLE_PAGE_SIZE} OFFSET {offset}")
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