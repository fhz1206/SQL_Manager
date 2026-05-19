import sys
from PyQt6.QtWidgets import QApplication
from main_window import DBManager


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    db_manager = DBManager()
    db_manager.show()
    # PyQt6中exec_()改为exec()
    sys.exit(app.exec())