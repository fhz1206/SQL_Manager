from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QIcon
from ..core.config import ICON_PATH


class CustomMessageBox(QDialog):
    """自定义消息框

    提供更宽的消息显示区域，适用于长错误消息
    """
    def __init__(self, title, message, icon_type='warning', parent=None):
        super().__init__(parent)
        self.setObjectName('customMessageBox')
        self.setWindowTitle(title)
        self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumWidth(500)  # 设置最小宽度
        self.setMaximumWidth(600)  # 设置最大宽度
        self.setModal(True)

        # 创建布局
        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # 添加图标和消息
        message_layout = QHBoxLayout()

        # 添加图标
        if icon_type == 'warning':
            icon_label = QLabel('⚠️')
        elif icon_type == 'error':
            icon_label = QLabel('❌')
        elif icon_type == 'info':
            icon_label = QLabel('ℹ️')
        else:
            icon_label = QLabel('•')

        icon_label.setStyleSheet('font-size: 24px;')
        message_layout.addWidget(icon_label)

        # 添加消息
        message_label = QLabel(message)
        message_label.setWordWrap(True)  # 允许文本换行
        message_layout.addWidget(message_label)
        message_layout.addStretch()

        layout.addLayout(message_layout)

        # 添加确定按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton('确定')
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)


def show_error(title, message, parent=None):
    """显示错误消息框"""
    dialog = CustomMessageBox(title, message, 'error', parent)
    return dialog.exec()


def show_warning(title, message, parent=None):
    """显示警告消息框"""
    dialog = CustomMessageBox(title, message, 'warning', parent)
    return dialog.exec()


def show_info(title, message, parent=None):
    """显示信息消息框"""
    dialog = CustomMessageBox(title, message, 'info', parent)
    return dialog.exec()
