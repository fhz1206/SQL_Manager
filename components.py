from PyQt6.QtWidgets import (QLineEdit, QTableView, QAbstractItemView, QHeaderView)
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor

from config import TABLE_PAGE_SIZE


class SearchLineEdit(QLineEdit):
    """带搜索图标的输入框"""
    def __init__(self, placeholder='搜索...', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(32)


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

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):  # 枚举全限定
        if not index.isValid() or index.row() >= len(self._data):
            return None
        
        row, col = index.row(), index.column()
        value = self._data[row][col] if col < len(self._data[row]) else ''
        
        if role == Qt.ItemDataRole.DisplayRole:  # 枚举全限定
            return str(value) if value is not None else ''
        elif role == Qt.ItemDataRole.BackgroundRole and self._alternating:  # 枚举全限定
            return QColor('#f8f9fa') if row % 2 == 1 else QColor('#ffffff')
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):  # 枚举全限定
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:  # 枚举全限定
            return self._columns[section] if section < len(self._columns) else ''
        return None

    def flags(self, index):
        # 枚举全限定
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

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
        # 枚举全限定
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)  # 枚举全限定
        # 枚举全限定
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.load_more_signal = None  # 外部绑定加载更多回调

    def set_alternating(self, enabled):
        self.model._alternating = enabled
        self.model.layoutChanged.emit()

    def load_more(self):
        """触发加载更多回调"""
        if self.load_more_signal and self.model.has_more:
            self.load_more_signal()