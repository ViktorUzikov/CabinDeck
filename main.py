from Source.enter_point import Window
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show() # todo: close db

    sys.exit(app.exec())
