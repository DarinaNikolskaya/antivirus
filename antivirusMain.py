import sys
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PySide6 import QtCore
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QPushButton, QLabel, QWidget, QPlainTextEdit, QListView, QHBoxLayout, QVBoxLayout, QLineEdit, QFileDialog, QTableWidget, QTableWidgetItem
import time

from PySide6.QtCore import Qt, QAbstractListModel
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem

import sqlite3
from datetime import datetime

quarantine_location = '/home/ok/Рабочий стол/qrt'
stop_words = ['rvhnjvnjvbjfvib123jsfbjkfvjkvbjr^%bxbvcg$%bnndxhcbhndbc']


conn = sqlite3.connect('my.db', check_same_thread=False)
cur = conn.cursor()

cur.execute(
    '''CREATE TABLE IF NOT EXISTS files
       (id INTEGER PRIMARY KEY,
        date VARCHAR,
        path VARCHAR,
        file_name VARCHAR,
        event VARCHAR)'''
    )
conn.commit()
conn.close()


class FileModifiedHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                print(event)
            some_root = "/".join(event.src_path.split("/")[:-1])
            some_name = event.src_path.split("/")[-1]
            if some_name[0] == ".":
                some_name = some_name[1:]
            if len(some_name.split(".")) == 3:
                some_name = ".".join(some_name.split(".")[:2])
            new_path = some_root + "/" + some_name
            ##if ".part" in some_name:
                ##some_name = some_name.replace(".part","")
            create_message_box(new_path)
            time.sleep(5)

def create_message_box(file_path):
            filename = get_file_name(file_path)
            msgBox = QMessageBox()
            msgBox.setText(f"Файл {filename} был изменён.")
            msgBox.setInformativeText("Это вы внесли изменения?")
            msgBox.setStandardButtons(QMessageBox.Yes| QMessageBox.No)
            buttonY = msgBox.button(QMessageBox.Yes)
            buttonY.setText('Да')
            buttonN = msgBox.button(QMessageBox.No)
            buttonN.setText('Нет')
            msgBox.setDefaultButton(QMessageBox.Yes)
            ret = msgBox.exec()

            global window
            date = get_date()
            file_name = get_file_name(file_path)


            if msgBox.clickedButton() == buttonY:

                conn = sqlite3.connect('my.db', check_same_thread=False)
                cur = conn.cursor()
                date = get_date()
                event = 'проверен'
                cur.execute("INSERT INTO files (date, path, file_name, event) VALUES(?, ?, ?, ?)", (date, file_path, file_name, event))

                window.insert_row_table(date, file_name, event)
                conn.commit()
                conn.close()
                print('файл проверен')
                msgBox.close()

            elif msgBox.clickedButton() == buttonN:
                move_file_to_quarantine(file_path)

                conn = sqlite3.connect('my.db', check_same_thread=False)
                cur = conn.cursor()

                event = 'отправлен в карантин'
                cur.execute("INSERT INTO files (date, path, file_name, event) VALUES(?, ?, ?, ?)", (date, file_path, file_name, event ))
                conn.commit()
                conn.close()

                window.insert_row_table(date,file_name,event)
                window.update_file_model()
                msgBox.close()


def get_file_name(file_path):
    return file_path.split('/')[-1]

def get_date():
    now = datetime.now()
    return now.strftime("%d/%m/%Y %H:%M:%S")

def move_file_to_quarantine(file_path):
    if not os.path.exists(quarantine_location):
        os.mkdir(quarantine_location)

    filename = get_file_name(file_path)
    # новый файл просто заменяет старый в папке карантина, если их названия одинаковы
    new_file_path = os.path.join(quarantine_location, filename)
    print(new_file_path)
    os.replace(file_path, new_file_path)
    mode = 0
    os.chmod(new_file_path, mode)


def search_stop_words(file_path):
    for root,dirs,files in os.walk(file_path):
        for file_ in files:
            filep = root + "/" + file_
            with open(filep, 'r') as file:
                text = file.read()
                if any(word in text for word in stop_words):
                    move_file_to_quarantine(filep)


def get_db_data():
    conn = sqlite3.connect('my.db', check_same_thread=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM files")
    rows = cur.fetchall()
    conn.close()
    return rows

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Antivirus")

        #Создаёт журнал событий
        log_label = QLabel("Журнал событий:")
        log_label.setFont(QFont("Arial", 14))
        self.log_table = QTableWidget()
        self.log_table.setFixedSize(400, 500)
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(['Дата', 'Название\n файла', 'Состояние\n файла'])
        self.log_table.setColumnWidth(0,150)
        self.log_table.setColumnWidth(1,100)
        self.log_table.setColumnWidth(2,139)
        self.create_table()


        #Создание карантинного виджета aka списка
        file_list_label = QLabel("Файлы в карантине:")
        file_list_label.setFont(QFont("Arial", 14))
        self.file_list = QListView()

        #Создаёт диалоговое окно восстановления
        self.file_list.clicked.connect(self.show_restore_dialog)
        self.file_list.setFixedSize(300, 500)

        #Вызов диалога восстановить / отмена
        self.file_model = QStandardItemModel()
        self.update_file_model()


        #Создание правой части виджета
        input_label = QLabel("Путь:")
        input_label.setFont(QFont("Arial", 14))
        self.input_field = QLineEdit('/home/ok/Рабочий стол/test')

        self.get_directory_button = QPushButton("Выбрать папку")
        self.get_directory_button.clicked.connect(self.get_directory)


        self.start_button = QPushButton("Запустить")
        self.start_button.clicked.connect(self.start_process)

        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop_process)

        self.clear_journal_button = QPushButton("Очистить журнал")
        self.clear_journal_button.clicked.connect(self.clear_journal)

        self.quit_program_button = QPushButton("Завершение работы")
        self.quit_program_button.clicked.connect(self.quit_program)


        # Create layout for left panel
        log_layout = QVBoxLayout()
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_table)


        # Create layout for middle panel
        file_list_layout = QVBoxLayout()
        file_list_layout.addWidget(file_list_label)
        file_list_layout.addWidget(self.file_list)

        # Create layout for right panel
        input_layout = QHBoxLayout()
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_field)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.get_directory_button)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.clear_journal_button)
        button_layout.addWidget(self.quit_program_button)


        right_layout = QVBoxLayout()
        right_layout.addLayout(input_layout)
        right_layout.addLayout(button_layout)

        # Create main layout
        main_layout = QHBoxLayout()
        main_layout.addLayout(log_layout)
        main_layout.addLayout(file_list_layout)
        main_layout.addLayout(right_layout)

        # Create central widget and set layout
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.observer = Observer()
        self.event_handler = FileModifiedHandler()




    def restore_file(self,result):
        old_path, fname, = result[2], result[3]
        new_file_path = old_path
        file_path = quarantine_location + "/" + fname
        os.replace(file_path, new_file_path)
        mode = 777
        os.chmod(new_file_path, mode)

        conn = sqlite3.connect('my.db', check_same_thread=False)
        cur = conn.cursor()
        date = get_date()
        event = 'восстановлен'
        cur.execute("INSERT INTO files (date, path, file_name, event) VALUES(?, ?, ?, ?)", (date, old_path, fname, event))
        global window
        window.insert_row_table(date,fname,event)
        conn.commit()
        conn.close()

        self.update_file_model()
        print('файл восстановлен')



    def show_restore_dialog(self,index):
        result = QMessageBox.question(self, 'Восстановление файла', 'Вы хотите восстановить этот файл?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if result == QMessageBox.StandardButton.Yes:
            # self.restore_file()
            item = self.file_model.item(index.row())
            file_name_to_search = str(item.text())
            print(file_name_to_search)
            conn = sqlite3.connect('my.db', check_same_thread=False)
            cur = conn.cursor()
            cur.execute("SELECT * FROM files WHERE file_name=? ORDER BY id DESC LIMIT 1",(file_name_to_search,))
            result = cur.fetchone()
            if result:
                self.restore_file(result)

            else:
                print('Информации об этом файле нет в базе данных')

        else:
            print('файл не восстановлен')


    def start_process(self):
        self.ROOT_DIR_TO_SCAN = self.input_field.text()
        self.observer.schedule(self.event_handler, path=self.ROOT_DIR_TO_SCAN, recursive=True)
        self.observer.start()
        self.call_scanner()

    def stop_process(self):
        # код для остановки сканера
        if self.observer.is_alive():
            self.observer.stop()
            try:
                self.observer.join()
            except:
                pass
            print('сканер остановлен')
            self.observer = Observer()
            self.event_handler = FileModifiedHandler()


    def clear_journal(self):
        conn = sqlite3.connect('my.db', check_same_thread=False)
        cur = conn.cursor()
        cur.execute('DELETE FROM files')
        self.log_table.clearContents()
        conn.commit()
        conn.close()

    def quit_program(self):
        try:
            self.stop_process()
        finally:
            self.close()

    #установить папку слежения при помощи кнопок
    def get_directory(self):
        response = QFileDialog.getExistingDirectory(
            self,
            caption='Выберите корневую папку для отслеживания'
            )
        print(response)
        self.input_field.setText(response)

    def call_scanner(self):
        search_stop_words(self.ROOT_DIR_TO_SCAN)
        print('запускаю сканер')

    def get_file_names_for_manager(self):
        spisok = []
        if not os.path.exists(quarantine_location):
            os.mkdir(quarantine_location)
        for root,dirs,files in os.walk(quarantine_location):
            for file_ in files:
                spisok.append(file_)
        return spisok

    def create_table(self):
        lines = get_db_data()
        for line in lines:
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            self.log_table.setItem(row,0,QTableWidgetItem(line[1]))
            self.log_table.setItem(row,1,QTableWidgetItem(line[3]))
            self.log_table.setItem(row,2,QTableWidgetItem(line[4]))

    def insert_row_table(self, date, file_name, event):
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        self.log_table.setItem(row,0,QTableWidgetItem(date))
        self.log_table.setItem(row,1,QTableWidgetItem(file_name))
        self.log_table.setItem(row,2,QTableWidgetItem(event))

    def update_file_model(self):
        self.file_model.clear()
        for file_name in self.get_file_names_for_manager():
            self.file_model.appendRow(QStandardItem(file_name))
        self.file_list.setModel(self.file_model)




if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()

        exit_code = app.exec()
        try:
            window.observer.stop()
            window.observer.join()
        except Exception as e:
            print(e)
        sys.exit(exit_code)
    except Exception as e:
        print(e)
        print(e.args)
