from PyQt6.QtWidgets import QMainWindow, QApplication, QDialog, QMessageBox, QDialogButtonBox, QFileDialog, QSizePolicy, \
    QLabel, QPushButton
from PyQt6.QtCore import QDateTime, Qt
from .interface import Ui_MainWindow
from .flight_dialog_interface import Ui_Dialog as FlightDialogUI
from .passenger_dialog_interface import Ui_Dialog as PassengerDialogUI
import sys
from .db import Database
from datetime import datetime
from .consts import *
from PyQt6.QtGui import QPixmap, QStandardItemModel, QStandardItem
from os.path import join, basename, abspath
from sqlite3 import IntegrityError


def setup_photo_label(label: QLabel):
    label.setScaledContents(False)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
    label.setMinimumSize(1, 1)


def show_pixmap(label: QLabel, pixmap: QPixmap):
    if pixmap is None or pixmap.isNull():
        label.clear()

        return

    label.setPixmap(pixmap.scaled(
        label.size(),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    ))


def ask_image(widget, choose_text: str):
    try:
        photo_path, _ = QFileDialog.getOpenFileName(widget, choose_text,
                                                    'C:/Users/',
                                                    'Изображения (*.png *.jpg *.jpeg)')

        photo_pixmap = QPixmap(photo_path)

        photo_pixmap.save(join(join('Source', 'Images'), basename(photo_path)))

        return photo_pixmap, abspath(join(join('Source', 'Images'), basename(photo_path)))
    except:
        QMessageBox.critical(widget, 'Ошибка', 'Произошла ошибка обработки картинки')

        return False


class FlightDialog(QDialog, FlightDialogUI):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)

        self.setWindowTitle("Новый рейс")

        self.date_time.setDateTime(QDateTime.currentDateTime())
        self.date_time.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_time.setCalendarPopup(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText('Добавить')
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText('Отменить')

    def accept(self):
        if not all(field.text().strip() for field in (self.arrival, self.departure, self.number)):
            QMessageBox.warning(self, 'Ошибка', 'Заполните все поля')

            return

        super().accept()

    def get_data(self):
        return (self.number.text().strip(), self.departure.text().strip(), self.arrival.text().strip(),
                self.date_time.dateTime().toString('yyyy-MM-dd HH:mm'))


class PassengerDialog(QDialog, PassengerDialogUI):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setupUi(self)

        self.setWindowTitle("Новый пассажир")

        self.place.addItems([seat for row in cabin for seat in row if seat])

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText('Добавить')
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText('Отменить')

        self.add_photo.clicked.connect(self.choose_photo)

        setup_photo_label(self.photo)

        self.photo_path = None
        self.photo_pixmap = None  # todo: deleted unused photos

    def choose_photo(self):
        pixmap = ask_image(self, f'Выберете фото для {self.name.text()}')

        if pixmap == False:
            self.photo_path = None
            self.photo_pixmap = None

            return

        self.photo_pixmap, self.photo_path = pixmap

        show_pixmap(self.photo, self.photo_pixmap)

    def accept(self):
        if not self.name.text().strip():
            QMessageBox.warning(self, 'Ошибка', 'Заполните все поля')

            return

        super().accept()

    def get_data(self):
        return (self.place.currentText().strip(), self.name.text().strip(), self.class_choice.currentText().strip(),
                self.photo_pixmap, self.photo_path)


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self.setupUi(self)

        self.db = Database('database.db')

        self.setWindowTitle('CabinDeck')

        self.seat_buttons = dict()

        setup_photo_label(self.photo)
        setup_photo_label(self.photo_in_passengers)

        self.new_flight.clicked.connect(self.show_flight_dialog)
        self.add_passenger.clicked.connect(self.show_passenger_dialog)
        self.listView.clicked.connect(self.on_passenger_selected)
        self.new_photo_in_passengers.clicked.connect(
            self.new_photo_callback)
        self.new_photo.clicked.connect(self.new_photo_callback)

        self.flight_choice.currentIndexChanged.connect(self.on_flight_changed)

        self.model = QStandardItemModel()

        self.listView.setModel(self.model)

        self.current_flight_id = -1
        self.current_passenger_in_list = -1

        self.build_scheme()

        self.rebuild_choice()

    def build_scheme(self):
        for row_i, row in enumerate(cabin):
            for seat_i, seat in enumerate(row):
                grid_col = seat_i if seat_i < 3 else seat_i + 1

                btn = QPushButton(seat)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
                btn.setMinimumSize(30, 30)
                btn.clicked.connect(lambda _, s=seat: self.on_seat_clicked(s))

                self.scheme.addWidget(btn, row_i, grid_col)
                self.seat_buttons[seat] = btn

        self.scheme.setColumnMinimumWidth(3, 20)
        self.scheme.setColumnStretch(3, 0)

    def refresh_scheme(self):
        taken = dict()

        if self.current_flight_id != -1:
            taken = {p[3]: p for p in self.db.get_passengers(self.current_flight_id)}

        for seat, button in self.seat_buttons.items():
            if seat in taken:
                button.setStyleSheet('background-color: #e57373;')
                button.setToolTip(taken[seat][2])
            else:
                button.setStyleSheet('background-color: #81c784;')
                button.setToolTip('Свободно')

    def on_seat_clicked(self, seat):
        if self.current_flight_id == -1:
            return

        person = self.db.get_passenger_by_seat(self.current_flight_id, seat)

        if person is None:
            self.clear_labels()

            self.place.setText(seat)

            return

        self.refresh_passenger(person[0])

        for row in range(self.model.rowCount()):
            item = self.model.item(row)

            if item.data(Qt.ItemDataRole.UserRole) == person[0]:
                self.listView.setCurrentIndex(item.index())

                break

        # todo: when selected -> border on button

    def refresh_passenger(self, passenger_id: int):
        self.current_passenger_in_list = passenger_id

        _, _, name, seat, service_path, photo_path = self.db.get_passenger(passenger_id)

        self.place_in_passengers.setText(seat)
        self.name_in_passengers.setText(name)
        self.class_in_passengers.setText(service_path)

        self.place.setText(seat)
        self.name.setText(name)
        self.class_serv.setText(service_path)

        pixmap = QPixmap(photo_path)

        show_pixmap(self.photo_in_passengers, pixmap)
        show_pixmap(self.photo, pixmap)

    def new_photo_callback(self):
        if self.current_passenger_in_list == -1:
            QMessageBox.warning(self, 'Ошибка', 'Не выбран пользователь')

            return

        pixmap = ask_image(self, f'Выберете фото для {self.name_in_passengers.text()}')

        if pixmap == False:
            return

        photo_pixmap, photo_path = pixmap

        show_pixmap(self.photo_in_passengers, photo_pixmap)
        show_pixmap(self.photo, photo_pixmap)

        self.db.change_passenger(self.current_passenger_in_list, photo_path=photo_path)

    def add_passenger_item(self, passenger_id: int, name: str):
        item = QStandardItem(name)
        item.setData(passenger_id, Qt.ItemDataRole.UserRole)
        item.setEditable(False)

        self.model.appendRow(item)

        return item

    def load_passengers(self):
        self.model.clear()

        if self.current_flight_id == -1:
            return

        for person in self.db.get_passengers(self.current_flight_id):
            self.add_passenger_item(person[0], person[2])

    def on_passenger_selected(self, index):
        self.refresh_passenger(index.data(Qt.ItemDataRole.UserRole))

    def clear_labels(self):
        self.current_passenger_in_list = -1

        for label in (self.place_in_passengers, self.name_in_passengers, self.class_in_passengers, self.class_serv,
                      self.place, self.name, self.photo, self.photo_in_passengers):
            label.clear()

    def show_flight_dialog(self):
        dialog = FlightDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            flight_id = self.db.add_flight(*dialog.get_data())

            self.rebuild_choice(flight_id)

    def show_passenger_dialog(self):
        dialog = PassengerDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.current_flight_id == -1:
                QMessageBox.warning(self, 'Ошибка', 'Нету рейсов')

                return

            place, name, class_, pixmap, photo_path = dialog.get_data()

            try:
                passenger_id = self.db.add_passenger(self.current_flight_id, name, place, class_, photo_path)
            except IntegrityError:
                QMessageBox.warning(self, 'Ошибка', 'Место занято')

                return

            index = self.model.indexFromItem(self.add_passenger_item(passenger_id, name))

            self.on_passenger_selected(index)

            self.refresh_scheme()

    def on_flight_changed(self):
        self.current_flight_id = self.flight_choice.currentData()

        self.load_passengers()
        self.refresh_scheme()
        self.select_first_passenger()

    def select_first_passenger(self):
        if not self.model.rowCount():
            self.clear_labels()
        else:
            index = self.model.index(0, 0)

            self.current_passenger_in_list = index

            self.listView.setCurrentIndex(index)

            self.on_passenger_selected(index)

    def rebuild_choice(self, select_id: int | None = None):
        self.flight_choice.blockSignals(True)
        self.flight_choice.clear()

        for f in self.db.get_flights():
            dt = datetime.strptime(f[4], '%Y-%m-%d %H:%M').strftime('%d.%m.%Y %H:%M')

            self.flight_choice.addItem(f'{f[1]}  {f[2]} -> {f[3]}  {dt}', f[0])

        if select_id is not None:
            index = self.flight_choice.findData(select_id)

            if index != -1:
                self.flight_choice.setCurrentIndex(index)

        self.flight_choice.blockSignals(False)

        self.on_flight_changed()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Window()
    window.show()

    sys.exit(app.exec())
