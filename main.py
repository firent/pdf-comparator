# PDF Comparator 3.0
# A program for comparing the textual content of PDF files
import difflib
import os
import sys

from pathlib import Path
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
                              QFileDialog, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text as pdfminer_extract


class Worker(QObject):
    progress_updated = Signal(int)
    status_updated = Signal(str)
    result_ready = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()

    def __init__(self, file1, file2):
        super().__init__()
        self.file1 = file1
        self.file2 = file2
        self._is_running = True

    def run(self):
        try:
            self.status_updated.emit(f"Извлечение текста из {Path(self.file1).name}...")
            text1 = self.extract_text(self.file1)
            if not self._is_running:
                return

            self.progress_updated.emit(30)
            self.status_updated.emit(f"Извлечение текста из {Path(self.file2).name}...")
            text2 = self.extract_text(self.file2)
            if not self._is_running:
                return

            self.progress_updated.emit(60)
            self.status_updated.emit("Сравнение текстов...")

            lines1 = text1.splitlines()
            lines2 = text2.splitlines()

            differ = difflib.Differ()
            diff = list(differ.compare(lines1, lines2))

            self.progress_updated.emit(80)
            self.status_updated.emit("Форматирование результатов...")

            result = []
            added = removed = 0
            for line in diff:
                if not self._is_running:
                    return

                if line.startswith('- '):
                    result.append(f'<span style="color:red">{line}</span>')
                    removed += 1
                elif line.startswith('+ '):
                    result.append(f'<span style="color:green">{line}</span>')
                    added += 1
                elif not line.startswith('? '):
                    result.append(f'<span style="color:gray">{line}</span>')

            result.append(f"\n<b>Итого: {added} добавлений, {removed} удалений</b>")
            self.result_ready.emit("<br>".join(result))
            self.progress_updated.emit(100)
            self.status_updated.emit(f"Сравнение завершено. {len(lines1)} к {len(lines2)} строк.")

        except Exception as e:
            self.error_occurred.emit(f"Ошибка: {str(e)}")
        finally:
            self.finished.emit()

    def extract_text(self, pdf_path):
        try:
            # Try pdfminer first for better extraction
            text = pdfminer_extract(pdf_path)
            return text
        except Exception as e:
            # Fall back to PyPDF2 if pdfminer fails
            try:
                reader = PdfReader(pdf_path)
                text = ""
                for i, page in enumerate(reader.pages):
                    if not self._is_running:
                        return ""
                    progress = 10 + (i * 40 // len(reader.pages))
                    self.progress_updated.emit(progress)
                    text += page.extract_text() or ""
                return text
            except Exception as e2:
                raise Exception(f"Ошибка извлечения текста: {str(e2)}")

    def stop(self):
        self._is_running = False


class PDFComparator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Comparator 3.0    Программа для сравнения текстового содержимого PDF-файлов")
        self.resize(1000, 700)
        self.worker_thread = None
        self.init_ui()
        self.init_menu()

    def init_menu(self):
        menubar = self.menuBar()
        
        # Menu "Menu"
        help_menu = menubar.addMenu("Меню")
        
        # Item "About"
        about_action = help_menu.addAction("О программе")
        about_action.triggered.connect(self.show_about)

        # Item "License"
        license_action = help_menu.addAction("Лицензия")
        license_action.triggered.connect(self.show_license)

        # Item "Exit"
        exit_action = help_menu.addAction("Выход")
        exit_action.triggered.connect(self.close)

    def show_about(self):
        text = """
        <b>PDF Comparator 3.0</b><br><br>
        Автор: Иван Пожидаев, 2025 г.<br>
        Email: ivan@ivanpozhidaev.ru<br>
        GitHub: <a href="https://github.com/firent/PDFComparator">https://github.com/firent/PDFComparator</a><br>
        Лицензия: MIT<br><br>
        Программа для сравнения текстового содержимого PDF-файлов.
        """
        QMessageBox.about(self, "О программе", text)

    def show_license(self):
        license_text = """
        Лицензия MIT<br><br>
        Copyright (c) 2025 Иван Пожидаев<br><br>
        Разрешается свободное использование, копирование, модификация и распространение. 
        Программа распространяется "как есть", без каких-либо гарантий.
        Подробнее в файле LICENSE.
        """
        msg = QMessageBox()
        msg.setWindowTitle("Лицензия")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(license_text)
        msg.exec()

    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # File selection group
        file_group = QGroupBox("Выбор файлов для сравнения")
        file_layout = QVBoxLayout()

        # File 1
        file1_layout = QHBoxLayout()
        file1_layout.addWidget(QLabel("Первый PDF-файл:"))
        self.file1_edit = QLineEdit()
        self.file1_edit.setPlaceholderText("Укажите путь к файлу...")
        file1_layout.addWidget(self.file1_edit, stretch=1)
        self.file1_btn = QPushButton("Обзор...")
        self.file1_btn.clicked.connect(lambda: self.select_file(self.file1_edit))
        file1_layout.addWidget(self.file1_btn)
        file_layout.addLayout(file1_layout)

        # File 2
        file2_layout = QHBoxLayout()
        file2_layout.addWidget(QLabel("Второй PDF-файл:"))
        self.file2_edit = QLineEdit()
        self.file2_edit.setPlaceholderText("Укажите путь к файлу...")
        file2_layout.addWidget(self.file2_edit, stretch=1)
        self.file2_btn = QPushButton("Обзор...")
        self.file2_btn.clicked.connect(lambda: self.select_file(self.file2_edit))
        file2_layout.addWidget(self.file2_btn)
        file_layout.addLayout(file2_layout)

        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.compare_btn = QPushButton("Сравнить файлы")
        self.compare_btn.clicked.connect(self.start_comparison)
        btn_layout.addWidget(self.compare_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_operation)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)

        # Results
        result_group = QGroupBox("Результаты сравнения")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setAcceptRichText(True)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group, stretch=1)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_label = QLabel("Готов")
        self.status_bar.addWidget(self.status_label, stretch=1)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.hide()

    def select_file(self, line_edit):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите PDF файл", "", "PDF Files (*.pdf)")
        if file_path:
            line_edit.setText(file_path)

    def start_comparison(self):
        file1 = self.file1_edit.text()
        file2 = self.file2_edit.text()

        if not file1 or not file2:
            QMessageBox.critical(self, "Ошибка", "Пожалуйста, выберите два PDF-файла")
            return

        if not os.path.exists(file1) or not os.path.exists(file2):
            QMessageBox.critical(self, "Ошибка", "Один или оба файла не существуют")
            return

        self.result_text.clear()
        self.compare_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.status_label.setText("Начато сравнение...")

        # Create worker and thread
        self.worker_thread = QThread()
        self.worker = Worker(file1, file2)
        self.worker.moveToThread(self.worker_thread)

        # Connect signals
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.status_updated.connect(self.update_status)
        self.worker.result_ready.connect(self.show_result)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.finished.connect(self.cleanup)

        self.worker_thread.started.connect(self.worker.run)
        self.worker_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, text):
        self.status_label.setText(text)

    def show_result(self, html_text):
        self.result_text.setHtml(html_text)

    def show_error(self, error_msg):
        QMessageBox.critical(self, "Ошибка", error_msg)

    def cleanup(self):
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None

        self.compare_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.hide()

    def cancel_operation(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker.stop()
            self.status_label.setText("Отмена операции...")
            self.cancel_btn.setEnabled(False)

    def closeEvent(self, event):
        if self.worker_thread and self.worker_thread.isRunning():
            self.cancel_operation()
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFComparator()
    window.show()
    sys.exit(app.exec())

