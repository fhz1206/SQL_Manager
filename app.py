import sys
from PyQt5.QtWidgets import QApplication
from main_window import DBManager


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    db_manager = DBManager()
    db_manager.show()
    sys.exit(app.exec_())