# coding=utf-8
import datetime
import sqlite3
import sys
import traceback
import csv
from datetime import date

from im_theory_ui import Ui_ImageTheory
from graphs_ui import Ui_Graph
from PyQt5.QtGui import QPixmap
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QApplication, QWidget, QAction, QInputDialog, QDialog
from PyQt5.QtWidgets import QMainWindow


# Вход
class LogInWindow(QWidget):
    def __init__(self):
        super(LogInWindow, self).__init__()
        uic.loadUi("login.ui", self)
        self.log_btn.clicked.connect(self.log_in)
        self.reg_btn.clicked.connect(self.registration)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()

    def log_in(self):
        login = self.login.text()
        password = self.password.text()
        # Чтение csv-файла для подтверждения аккаунта
        with open("logins.csv", mode="r", encoding="utf8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for elem in reader:
                if login == elem['login'] and password == elem['password']:
                    if elem["type"] == "Ученик":
                        # Запуск окна для ученика
                        self.msmw = MainStudentModeWindow(elem["type"])
                        self.msmw.show()
                        self.hide()
                        # Ввод в БД никнейм ученика и настоящую дату
                        # для календаря посещаемости
                        d = str(date.today()).split("-")
                        t = str(datetime.datetime.now().time())
                        self.cur.execute(
                            """INSERT INTO 
                            calendar(year, month, day, time, username)
                            VALUES(?, ?, ?, ?, ?)""",
                            (d[0], d[1], d[2], t, elem["login"])
                        )
                        self.con.commit()
                    elif elem["type"] == "Учитель":
                        # Запуск окна для учителя
                        self.mtmw = MainTeacherModeWindow(elem["type"])
                        self.mtmw.show()
                        self.hide()
                else:
                    self.login_error.setText("Пользователь не найден")

    # Регистрация нового аккаунта
    def registration(self):
        data = {"login": self.reg_login.text(),
                "password": self.reg_password.text(),
                "type": self.reg_type.currentText()}
        # Проверка пароля
        if len(data["password"]) < 8:
            self.reg_error.setText("Слишком короткий пароль")
        if not data["password"].isalnum():
            self.reg_error.setText(
                "В пароле должны присутствовать латиница и цифры")
        else:
            with open("logins.csv", mode="a", encoding="utf8", newline="") \
                    as f:
                # Запись нового аккаунта в csv-таблицу
                writer = csv.DictWriter(
                    f, fieldnames=["login", "password", "type"],
                    delimiter=";", quoting=csv.QUOTE_NONNUMERIC
                )
                writer.writerow(data)
                # Вход в программу в зависимости от выбранного типа
                if data["type"] == "Ученик":
                    d = str(date.today()).split("-")
                    t = str(datetime.datetime.now().time())
                    self.cur.execute(
                        """INSERT INTO 
                        calendar(year, month, day, time, username)
                        VALUES(?, ?, ?, ?, ?)""",
                        (d[0], d[1], d[2], t, data["login"])
                    )
                    self.msmw = MainStudentModeWindow(data["type"])
                    self.msmw.show()
                    self.hide()
                elif data["type"] == "Учитель":
                    self.mtmw = MainTeacherModeWindow(data["type"])
                    self.mtmw.show()
                    self.hide()


# Режим ученика
class MainStudentModeWindow(QMainWindow):
    def __init__(self, user_type):
        super(MainStudentModeWindow, self).__init__()
        uic.loadUi("main_window.ui", self)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.setFixedSize(805, 605)
        self.ex_output.setFontPointSize(12)
        self.data_output.setFontPointSize(12)
        self.ex_output.setReadOnly(True)
        self.data_output.setReadOnly(True)
        # Выбор темы
        titles = self.cur.execute(
            """SELECT title FROM theory"""
        )
        for elem in titles:
            title, = elem
            self.themes.addItem(title)
            self.ex_themes.addItem(title)
        # Кнопки
        self.upload_btn.clicked.connect(self.upload_theme)
        self.ex_upload_nums_btn.clicked.connect(self.ex_upload_nums)
        self.output_btn.clicked.connect(self.exercise_output)
        self.answer_btn.clicked.connect(self.answer_output)
        self.images_theory_btn.clicked.connect(self.show_theory_image)
        self.im_practice_btn.clicked.connect(self.show_practice_image)
        self.graph_btn.clicked.connect(self.show_graph)
        # Меню
        self.help = HelpWindow(user_type)
        show_help_btn = QAction("Открыть", self.help)
        show_help_btn.setShortcut("Ctrl+H")
        show_help_btn.setStatusTip("Открыть Справку")
        show_help_btn.triggered.connect(self.help.show)
        self.help_menu.addAction(show_help_btn)

    # Загрузка текста урока в QTextEdit
    def upload_theme(self):
        text = self.cur.execute(
            """SELECT data FROM theory WHERE title = ?""",
            (self.themes.currentText(),)
        ).fetchall()
        res, = text[0]
        self.data_output.setText(res)

    # Номера задач в теме
    def ex_upload_nums(self):
        self.ex_nums.clear()
        self.ex_output.clear()
        self.result.clear()
        # Получение названий задач только по данной теме
        nums = self.cur.execute(
            """SELECT title FROM practice WHERE theme = ?""",
            (self.ex_themes.currentText(),)
        ).fetchall()
        # Вывод вариантов в QComboBox
        for elem in nums:
            res, = elem
            self.ex_nums.addItem(res)

    # Вывод задания в QTextEdit
    def exercise_output(self):
        # Очистка предыдущих вариантов
        self.result.clear()
        # Сортировка по запросу
        text = self.cur.execute(
            """SELECT data FROM practice WHERE title = ?""",
            (self.ex_nums.currentText(),)
        ).fetchall()
        if len(text) == 0:
            self.res_output.setText("Сначала выберите задачу")
        else:
            res, = text[0]
            choices = self.cur.execute(
                """SELECT choices FROM practice 
                WHERE title = ?""", (self.ex_nums.currentText(),)
            ).fetchall()
            sec_res, = choices[0]
            sec_res = sec_res.split("_")
            # Вывод
            for elem in sec_res:
                self.result.addItem(elem)
            self.ex_output.setText(res)

    # Правильно ли выполнена задача
    def answer_output(self):
        answer = self.result.currentText()
        right_answer = self.cur.execute(
            """SELECT answer FROM practice WHERE title = ?""",
            (self.ex_nums.currentText(),)
        ).fetchall()
        if len(answer) == 0:
            self.res_output.setText("Сначала выберите задачу")
        else:
            res, = right_answer[0]
            if answer == res:
                self.res_output.setText("Good job!")
            else:
                self.res_output.setText("Try again!")

    # Рисунки для теории
    def show_theory_image(self):
        self.move(400, 250)
        self.im_theory = ImageTheoryWindow(self.themes.currentText())
        self.im_theory.show()

    # рисунки для практики
    def show_practice_image(self):
        if len(self.cur.execute(
                """SELECT title FROM images_practice WHERE title = ?""",
                (self.ex_nums.currentText(),)
        ).fetchall()):
            self.move(400, 250)
            self.ipw = ImagePracticeWindow(self.ex_nums.currentText())
            self.ipw.show()
        else:
            self.res_output.setText("Для данной задачи нет рисунков")

    # Графики
    def show_graph(self):
        if len(self.cur.execute(
                """SELECT data FROM graphs WHERE title = ?""",
                (self.ex_nums.currentText(),)
        ).fetchall()):
            self.move(400, 250)
            self.gw = GraphWindow(self.ex_nums.currentText())
            self.gw.show()
        else:
            self.res_output.setText("Для данной задачи нет графиков")


# Режим учителя
class MainTeacherModeWindow(QMainWindow):
    def __init__(self, user_type):
        super(MainTeacherModeWindow, self).__init__()
        uic.loadUi("main_teacher_window.ui", self)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.setFixedSize(805, 605)
        self.ex_output.setFontPointSize(12)
        self.data_output.setFontPointSize(12)
        self.ex_output.setReadOnly(True)
        self.data_output.setReadOnly(True)
        # Выбор темы
        titles = self.cur.execute(
            """SELECT title FROM theory"""
        ).fetchall()
        for elem in titles:
            title, = elem
            self.themes.addItem(title)
            self.ex_themes.addItem(title)
            self.app_theme.addItem(title)
        # Кнопки
        self.upload_btn.clicked.connect(self.upload_theme)
        self.ex_upload_nums_btn.clicked.connect(self.ex_upload_nums)
        self.output_btn.clicked.connect(self.exercise_output)
        self.answer_btn.clicked.connect(self.answer_output)
        self.images_theory_btn.clicked.connect(self.show_theory_image)
        self.redact_theory_btn.clicked.connect(self.redacting_theory)
        self.redact_practice_btn.clicked.connect(self.redacting_practice)
        self.del_practice_btn.clicked.connect(self.delete_practice_obj)
        self.del_theory_btn.clicked.connect(self.delete_theory_obj)
        self.graph_btn.clicked.connect(self.show_graph)
        self.app_btn.clicked.connect(self.append_smth)
        self.im_practice_btn.clicked.connect(self.show_practice_image)
        self.theory_update_btn.clicked.connect(self.update_theory)
        self.practice_update_btn.clicked.connect(self.update_practice)
        # Меню
        self.cal = CalendarWindow()
        show_cal_btn = QAction("Открыть", self.cal)
        show_cal_btn.setShortcut("Ctrl+O")
        show_cal_btn.setStatusTip("Открыть календать посещаемости")
        show_cal_btn.triggered.connect(self.cal.show)
        self.calendar_menu.addAction(show_cal_btn)

        self.help = HelpWindow(user_type)
        show_help_btn = QAction("Открыть", self.help)
        show_help_btn.setShortcut("Ctrl+H")
        show_help_btn.setStatusTip("Открыть Справку")
        show_help_btn.triggered.connect(self.help.show)
        self.help_menu.addAction(show_help_btn)

    # Загрузка текста урока в QTextEdit
    def upload_theme(self):
        text = self.cur.execute(
            """SELECT data FROM theory WHERE title = ?""",
            (self.themes.currentText(),)
        ).fetchall()
        if len(text) == 0:
            self.theory_alert.setText(
                "Скорее всего, вы выбрали тему, которой больше не существует."
            )
        else:
            res, = text[0]
            self.data_output.setText(res)

    # Номера задач в теме
    def ex_upload_nums(self):
        self.ex_nums.clear()
        self.ex_output.clear()
        self.result.clear()
        nums = self.cur.execute(
            """SELECT title FROM practice WHERE theme = ?""",
            (self.ex_themes.currentText(),)
        ).fetchall()
        for elem in nums:
            res, = elem
            self.ex_nums.addItem(res)

    # Вывод задачи в QTextEdit
    def exercise_output(self):
        self.result.clear()
        text = self.cur.execute(
            """SELECT data FROM practice WHERE title = ?""",
            (self.ex_nums.currentText(),)
        ).fetchall()
        if len(text) == 0:
            self.res_output.setText("Сначала выберите задачу")
        else:
            res, = text[0]
            choices = self.cur.execute(
                """SELECT choices FROM practice WHERE title = ?""",
                (self.ex_nums.currentText(),)
            ).fetchall()
            sec_res, = choices[0]
            sec_res = sec_res.split("_")
            for elem in sec_res:
                self.result.addItem(elem)
            self.ex_output.setText(res)

    # Правильно ли выполнена задача
    def answer_output(self):
        answer = self.result.currentText()
        right_answer = self.cur.execute(
            """SELECT answer FROM practice WHERE title = ?""",
            (self.ex_nums.currentText(),)
        ).fetchall()
        if len(answer) == 0:
            self.res_output.setText("Сначала выберите задачу")
        else:
            res, = right_answer[0]
            if answer == res:
                self.res_output.setText("Good job!")
            else:
                self.res_output.setText("Try again!")

    # Редактирование задачи
    def redacting_theory(self):
        theme = self.themes.currentText()
        self.rtmw = RedactTheoryModeWindow(theme)
        self.rtmw.show()

    # Редактирование теории
    def redacting_practice(self):
        if len(self.ex_nums.currentText()) == 0:
            self.res_output.setText("Сначала выберите задачу")
        else:
            number = self.ex_nums.currentText()
            self.rpmw = RedactPracticeModeWindow(number)
            self.rpmw.show()

    # Рисунки для теории
    def show_theory_image(self):
        self.move(400, 250)
        self.itw = ImageTheoryWindow(self.themes.currentText())
        self.itw.show()

    # Рисунки для практики
    def show_practice_image(self):
        # Проверка на наличие рисунков к задаче
        if len(self.cur.execute(
                """SELECT title FROM images_practice WHERE exercise = ?""",
                (self.ex_nums.currentText(),)
        ).fetchall()):
            self.move(400, 250)
            self.ipw = ImagePracticeWindow(self.ex_nums.currentText())
            self.ipw.show()
        else:
            self.res_output.setText("Для данной задачи нет рисунков")

    # Графики
    def show_graph(self):
        # Прверка на наличие графиков у задачи
        if len(self.cur.execute(
                """SELECT data FROM graphs WHERE title = ?""",
                (self.ex_nums.currentText(),)
        ).fetchall()):
            self.move(400, 250)
            self.gw = GraphWindow(self.ex_nums.currentText())
            self.gw.show()
        else:
            self.res_output.setText("Для данной задачи нет графиков")

    # Удаление теоретической части
    def delete_practice_obj(self):
        if len(self.ex_nums.currentText()) == 0:
            self.res_output.setText("Сначала выберите задачу")
        else:
            self.confirm = ConfirmDeletePracticeDialog(self.ex_nums.currentText())
            self.confirm.show()

    # Удаление практической части
    def delete_theory_obj(self):
        self.confirm = ConfirmDeleteTheoryDialog(self.themes.currentText())
        self.confirm.show()

    # Добавление
    def append_smth(self):
        # Для теории
        if self.app_type.currentText() == "Теория":
            # Проверка на наличие данных
            if len(self.app_title.text()) == 0 or \
                    len(self.app_data.toPlainText()) == 0:
                self.error.setText("Необходимые поля не заполнены.")
            else:
                title = self.app_title.text()
                data = self.app_data.toPlainText()
                self.cur.execute(
                    """INSERT INTO theory(title, data) VALUES(?, ?)""",
                    (title, data)
                )
                self.error.setText("""Добавление завершено успешно.""")
                self.con.commit()
        # Для практики
        elif self.app_type.currentText() == "Практика":
            # Проверка на наличие данных
            if len(self.app_title.text()) == 0 or \
                    len(self.app_data.toPlainText()) == 0 or \
                    len(self.app_variants.text()) == 0 or \
                    len(self.app_answer.text()) == 0:
                self.error.setText("Необходимые поля не заполнены.")
            else:
                title = self.app_title.text()
                theme = self.app_theme.currentText()
                data = self.app_data.toPlainText()
                choices = self.app_variants.text()
                answer = self.app_answer.text()
                self.cur.execute(
                    """INSERT INTO
                    practice(title, theme, data, choices, answer)
                    VALUES(?, ?, ?, ?, ?)""",
                    (title, theme, data, choices, answer)
                )
                self.error.setText("""Добавление завершено успешно.""")
                self.con.commit()

    def update_theory(self):
        self.themes.clear()
        self.data_output.clear()
        themes = self.cur.execute(
            """SELECT title FROM theory"""
        ).fetchall()
        for elem in themes:
            res, = elem
            self.themes.addItem(res)

    def update_practice(self):
        self.ex_themes.clear()
        self.ex_output.clear()
        self.result.clear()
        themes = self.cur.execute(
            """SELECT title FROM theory"""
        ).fetchall()
        for elem in themes:
            res, = elem
            self.ex_themes.addItem(res)


# Редактирование теории
class RedactTheoryModeWindow(QWidget):
    def __init__(self, theme):
        super(RedactTheoryModeWindow, self).__init__()
        uic.loadUi("redact_theory.ui", self)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.theme = theme
        data = self.cur.execute(
            """SELECT data FROM theory WHERE title = ?""",
            (self.theme,)
        ).fetchall()
        data, = data[0]
        self.title.setText(self.theme)
        self.data.setText(data)
        # Кнопки
        self.res_btn.clicked.connect(self.redact)

    def redact(self):
        if len(self.title.text()) == 0 or len(self.data.toPlainText()) == 0:
            self.error.setText("Вы не полностью заполнили поля ввода")
        else:
            self.cur.execute(
                """UPDATE theory SET data = ? WHERE title = ?""",
                (self.data.toPlainText(), self.theme)
            )
            self.cur.execute(
                """UPDATE theory SET title = ? WHERE title = ?""",
                (self.title.text(), self.theme)
            )
            self.con.commit()
            self.hide()


# Редактирование практики
class RedactPracticeModeWindow(QWidget):
    def __init__(self, number):
        super(RedactPracticeModeWindow, self).__init__()
        uic.loadUi("redact_practice.ui", self)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.number = number
        self.title.setText(self.number)

        theme = self.cur.execute(
            """SELECT title FROM theory"""
        ).fetchall()
        for elem in theme:
            res, = elem
            self.theme.addItem(res)

        data = self.cur.execute(
            """SELECT data FROM practice WHERE title = ?""",
            (self.number,)
        ).fetchall()
        data, = data[0]
        self.data.setText(data)

        choices = self.cur.execute(
            """SELECT choices FROM practice WHERE title = ?""",
            (self.number,)
        ).fetchall()
        choices, = choices[0]
        self.choices.setText(choices)

        answer = self.cur.execute(
            """SELECT answer FROM practice WHERE title = ?""",
            (self.number,)
        ).fetchall()
        answer, = answer[0]
        self.answer.setText(answer)
        # Кнопки
        self.res_btn.clicked.connect(self.redact)

    # Обновление данных
    def redact(self):
        if len(self.title.text()) == 0 or len(self.data.toPlainText()) == 0 or len(self.choices.text()) == 0 or len(
                self.answer.text()) == 0:
            self.error.setText("Вы не полностью заполнили поля ввода")
        else:
            self.cur.execute(
                """UPDATE practice SET theme = ?, data = ?, choices = ?, answer = ?
                 WHERE title = ?""",
                (self.theme.currentText(), self.data.toPlainText(),
                 self.choices.text(), self.answer.text(), self.number)
            )
            self.cur.execute(
                """UPDATE practice SET title = ? WHERE title = ?""",
                (self.title.text(), self.number)
            )
            self.con.commit()
            self.hide()


# Виджет с рисунками для теории
class ImageTheoryWindow(QWidget, Ui_ImageTheory):
    def __init__(self, theme):
        super(ImageTheoryWindow, self).__init__()
        self.setupUi(self)
        self.move(1205, 250)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.theme = theme
        titles = self.cur.execute(
            """SELECT title FROM images_theory WHERE theme = ?""",
            (theme,)
        ).fetchall()
        for elem in titles:
            res, = elem
            self.choose_im.addItem(res)
        # Кнопки
        self.btn.clicked.connect(self.upload_im)

    # Вывод рисунка
    def upload_im(self):
        path = self.cur.execute(
            """SELECT path FROM images_theory WHERE title = ?""",
            (self.choose_im.currentText(),)
        ).fetchall()
        res, = path[0]
        self.pixmap = QPixmap(res)
        self.image.setPixmap(self.pixmap)


# Виджет с рисунками для практики
class ImagePracticeWindow(QWidget):
    def __init__(self, number):
        super(ImagePracticeWindow, self).__init__()
        uic.loadUi("im_practice.ui", self)
        self.move(1205, 250)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.number = number
        titles = self.cur.execute(
            """SELECT title FROM images_practice WHERE exercise = ?""",
            (number,)
        ).fetchall()
        for elem in titles:
            res, = elem
            self.choose_im_practice.addItem(res)
        # Кнопки
        self.res_btn_practice.clicked.connect(self.upload_im)

    # Вывод рисунка
    def upload_im(self):
        path = self.cur.execute(
            """SELECT path FROM images_practice WHERE title = ?""",
            (self.choose_im_practice.currentText(),)
        ).fetchall()
        res, = path[0]
        self.pixmap = QPixmap(res)
        self.image_practice.setPixmap(self.pixmap)


# Графики
class GraphWindow(QWidget, Ui_Graph):
    def __init__(self, number):
        super(GraphWindow, self).__init__()
        self.setupUi(self)
        self.move(1205, 250)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        answers = self.cur.execute(
            """SELECT answer FROM graphs WHERE title = ?""",
            (number,)
        ).fetchall()
        for elem in answers:
            res, = elem
            self.variants.addItem(res)
        self.btn.clicked.connect(self.build_func)

    def build_func(self):
        self.graph.clear()
        self.nums = self.cur.execute(
            """SELECT data FROM graphs WHERE answer = ?""",
            (self.variants.currentText(),)
        ).fetchall()
        for elem in self.nums:
            res, = elem
            res = res.split()
        self.graph.plot([0, int(res[0])], [0, int(res[1])])


# Календарь посещаемости
class CalendarWindow(QWidget):
    def __init__(self):
        super(CalendarWindow, self).__init__()
        uic.loadUi("calendar.ui", self)
        self.output.setReadOnly(True)
        self.res_btn.clicked.connect(self.example)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()

    def example(self):
        y = self.calendarWidget.selectedDate().year()
        m = self.calendarWidget.selectedDate().month()
        d = self.calendarWidget.selectedDate().day()
        data = self.cur.execute(
            """SELECT username, time FROM calendar
            WHERE year = ? AND month = ? AND day = ?""",
            (y, m, d)
        )
        result = []
        for elem in data:
            name, time = elem
            result.append(name + "\t" + time[:8])
        self.output.setText("\n".join(result))


# Справка
class HelpWindow(QWidget):
    def __init__(self, user_type):
        super(HelpWindow, self).__init__()
        uic.loadUi("help.ui", self)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.output.setReadOnly(True)
        self.output.setFontPointSize(12)
        # Названия из БД
        if user_type == "Ученик":
            self.titles = self.cur.execute(
                """SELECT title FROM help WHERE only_for_teachers = 0"""
            ).fetchall()
        elif user_type == "Учитель":
            self.titles = self.cur.execute(
                """SELECT title FROM help"""
            ).fetchall()
        for elem in self.titles:
            res, = elem
            self.elements.addItem(res)
        self.res_btn.clicked.connect(self.upload_info)

    def upload_info(self):
        data = self.cur.execute(
            """SELECT data FROM help WHERE title = ?""",
            (self.elements.currentText(),)
        ).fetchall()[0]
        data, = data
        self.output.setText(data)


# Подтверждение удаления(Диалог)
class ConfirmDeletePracticeDialog(QDialog):
    def __init__(self, name):
        super().__init__()
        uic.loadUi("confirm.ui", self)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.name = name
        self.btn_box.accepted.connect(self.agreement)
        self.btn_box.rejected.connect(self.refusal)

    def agreement(self):
        self.cur.execute(
            """DELETE FROM practice WHERE title = ?""",
            (self.name,)
        )
        self.con.commit()
        self.close()

    def refusal(self):
        self.close()


# Подтверждение удаления(Диалог)
class ConfirmDeleteTheoryDialog(QDialog):
    def __init__(self, name):
        super().__init__()
        uic.loadUi("confirm.ui", self)
        self.con = sqlite3.connect("main_db.sqlite3")
        self.cur = self.con.cursor()
        self.name = name
        self.btn_box.accepted.connect(self.agreement)
        self.btn_box.rejected.connect(self.refusal)

    def agreement(self):
        self.cur.execute(
            """DELETE FROM theory WHERE title = ?""",
            (self.name,)
        )
        self.con.commit()
        self.close()

    def refusal(self):
        self.close()


def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("Oбнаружена ошибка !:", tb)
    QtWidgets.QApplication.quit()


if __name__ == '__main__':
    sys.excepthook = excepthook
    app = QApplication(sys.argv)
    ex = LogInWindow()
    ex.show()
    sys.exit(app.exec())
