
import sys
import sqlite3
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QInputDialog, QTabWidget, QLabel, QLineEdit, 
                             QComboBox, QFileDialog, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QMenu, QAction, QStatusBar, QToolBar, QTextEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence


class DBManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_db = None
        self.conn = None
        self.current_table = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('SQLite数据库管理工具')
        self.setGeometry(100, 100, 1200, 700)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 创建工具栏
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # 打开数据库按钮
        open_db_action = QAction('打开数据库', self)
        open_db_action.triggered.connect(self.open_database)
        toolbar.addAction(open_db_action)

        # 新建数据库按钮
        new_db_action = QAction('新建数据库', self)
        new_db_action.triggered.connect(self.create_database)
        toolbar.addAction(new_db_action)

        # 关闭数据库按钮
        close_db_action = QAction('关闭数据库', self)
        close_db_action.triggered.connect(self.close_database)
        toolbar.addAction(close_db_action)

        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 创建主布局
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # 左侧面板 - 数据库对象浏览器
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        # 数据库对象树
        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderLabels(['数据库对象'])
        self.db_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.db_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.db_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        left_layout.addWidget(self.db_tree)

        splitter.addWidget(left_panel)

        # 右侧面板 - 数据表和SQL编辑器
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)

        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        right_layout.addWidget(self.tab_widget)

        # 数据表选项卡
        self.table_tab = QWidget()
        table_layout = QVBoxLayout()
        self.table_tab.setLayout(table_layout)

        # 表格控件
        self.table_widget = QTableWidget()
        self.table_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_table_context_menu)
        table_layout.addWidget(self.table_widget)

        self.tab_widget.addTab(self.table_tab, '数据表')

        # SQL编辑器选项卡
        self.sql_tab = QWidget()
        sql_layout = QVBoxLayout()
        self.sql_tab.setLayout(sql_layout)

        # SQL编辑器
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText('输入SQL查询语句...')
        sql_layout.addWidget(self.sql_editor)

        # 执行按钮
        execute_button = QPushButton('执行')
        execute_button.clicked.connect(self.execute_sql)
        sql_layout.addWidget(execute_button)

        # 查询结果表格
        self.result_table = QTableWidget()
        sql_layout.addWidget(self.result_table)

        self.tab_widget.addTab(self.sql_tab, 'SQL查询')

        splitter.addWidget(right_panel)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        # 初始状态
        self.update_ui_state()

    def update_ui_state(self):
        """更新UI状态"""
        has_db = self.conn is not None

        # 更新状态栏
        if has_db:
            self.status_bar.showMessage(f'当前数据库: {self.current_db}')
        else:
            self.status_bar.showMessage('未打开数据库')

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
            self.refresh_db_tree()
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            self.update_ui_state()
            self.status_bar.showMessage('已关闭数据库', 3000)

    def refresh_db_tree(self):
        """刷新数据库对象树"""
        self.db_tree.clear()

        if not self.conn:
            return

        # 添加数据库节点
        db_item = QTreeWidgetItem(self.db_tree)
        db_item.setText(0, self.current_db)
        db_item.setData(0, Qt.UserRole, 'database')

        try:
            cursor = self.conn.cursor()

            # 获取所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            for table in tables:
                table_name = table[0]
                table_item = QTreeWidgetItem(db_item)
                table_item.setText(0, table_name)
                table_item.setData(0, Qt.UserRole, 'table')

                # 获取表的列信息
                cursor.execute(f"PRAGMA table_info('{table_name}')")
                columns = cursor.fetchall()

                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    col_item = QTreeWidgetItem(table_item)
                    col_item.setText(0, f"{col_name} ({col_type})")
                    col_item.setData(0, Qt.UserRole, 'column')

            # 获取所有视图
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
            views = cursor.fetchall()

            if views:
                views_item = QTreeWidgetItem(db_item)
                views_item.setText(0, "视图")
                views_item.setData(0, Qt.UserRole, 'views')

                for view in views:
                    view_name = view[0]
                    view_item = QTreeWidgetItem(views_item)
                    view_item.setText(0, view_name)
                    view_item.setData(0, Qt.UserRole, 'view')

            self.db_tree.expandAll()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法刷新数据库对象树: {str(e)}")

    def on_tree_item_clicked(self, item, column):
        """当树项被点击时"""
        item_type = item.data(0, Qt.UserRole)

        if item_type == 'table':
            table_name = item.text(0)
            self.show_table_data(table_name)

    def show_table_data(self, table_name):
        """显示表数据"""
        if not self.conn:
            return

        try:
            self.current_table = table_name
            cursor = self.conn.cursor()

            # 获取表结构
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            # 设置表格列
            self.table_widget.setColumnCount(len(columns))
            self.table_widget.setHorizontalHeaderLabels([col[1] for col in columns])

            # 获取表数据
            cursor.execute(f"SELECT * FROM '{table_name}'")
            rows = cursor.fetchall()

            # 填充表格数据
            self.table_widget.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else '')
                    self.table_widget.setItem(i, j, item)

            # 调整列宽
            self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

            # 切换到数据表选项卡
            self.tab_widget.setCurrentWidget(self.table_tab)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法显示表数据: {str(e)}")

    def show_tree_context_menu(self, position):
        """显示树形菜单的上下文菜单"""
        item = self.db_tree.itemAt(position)
        if not item:
            return

        item_type = item.data(0, Qt.UserRole)
        menu = QMenu()

        if item_type == 'database':
            refresh_action = QAction('刷新', self)
            refresh_action.triggered.connect(self.refresh_db_tree)
            menu.addAction(refresh_action)

            new_table_action = QAction('新建表', self)
            new_table_action.triggered.connect(self.create_table)
            menu.addAction(new_table_action)

        elif item_type == 'table':
            table_name = item.text(0)

            view_data_action = QAction('查看数据', self)
            view_data_action.triggered.connect(lambda: self.show_table_data(table_name))
            menu.addAction(view_data_action)

            edit_structure_action = QAction('编辑结构', self)
            edit_structure_action.triggered.connect(lambda: self.edit_table_structure(table_name))
            menu.addAction(edit_structure_action)

            rename_table_action = QAction('重命名表', self)
            rename_table_action.triggered.connect(lambda: self.rename_table(table_name))
            menu.addAction(rename_table_action)

            drop_table_action = QAction('删除表', self)
            drop_table_action.triggered.connect(lambda: self.drop_table(table_name))
            menu.addAction(drop_table_action)

        menu.exec_(self.db_tree.mapToGlobal(position))

    def show_table_context_menu(self, position):
        """显示表格的上下文菜单"""
        if not self.current_table:
            return

        menu = QMenu()

        insert_row_action = QAction('插入行', self)
        insert_row_action.triggered.connect(self.insert_row)
        menu.addAction(insert_row_action)

        delete_row_action = QAction('删除行', self)
        delete_row_action.triggered.connect(self.delete_row)
        menu.addAction(delete_row_action)

        save_changes_action = QAction('保存更改', self)
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

        # 这里可以添加一个更复杂的对话框来编辑表结构
        # 目前只显示表结构信息
        try:
            cursor = self.conn.cursor()
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            info = f"表 {table_name} 的结构:\n\n"
            for col in columns:
                info += f"列名: {col[1]}, 类型: {col[2]}, 主键: {'是' if col[5] else '否'}\n"

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
            if sql.upper().startswith('SELECT'):
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
        except Exception as e:
            QMessageBox.critical(self, "错误", f"SQL执行错误: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    db_manager = DBManager()
    db_manager.show()
    sys.exit(app.exec_())