
import os

from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
)


class HomePage(QWidget):
    openRequested = Signal()
    pdfSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings("rt-PDF", "rt-PDF")
        self.recent_files = self.settings.value(
            "recentFiles", [], type=list
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        # Header
        title = QLabel("rt-PDF")
        title.setStyleSheet("font-size: 30px; font-weight: bold;")

        subtitle = QLabel("Welcome back. Pick up where you left off.")
        subtitle.setStyleSheet("font-size: 14px; color: #888;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # Open PDF button
        open_button = QPushButton("Open PDF")
        open_button.clicked.connect(self.openRequested.emit)
        layout.addWidget(open_button)

        # Recent files
        recent_title = QLabel("Recent PDFs")
        recent_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )
        layout.addWidget(recent_title)

        self.file_list = QListWidget()
        self.file_list.itemDoubleClicked.connect(
            self.open_selected_pdf
        )
        layout.addWidget(self.file_list)

        self.refresh_recent_files()

    def refresh_recent_files(self):
        self.file_list.clear()

        # Remove paths that no longer exist
        self.recent_files = [
            path for path in self.recent_files
            if os.path.isfile(path)
        ]

        self.settings.setValue("recentFiles", self.recent_files)

        for path in self.recent_files:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.file_list.addItem(item)

        if not self.recent_files:
            self.file_list.addItem("No recent PDFs yet")

    def add_recent_file(self, path):
        if not path:
            return

        path = os.path.abspath(path)
        self.recent_files = [
            p for p in self.recent_files if p != path
        ]

        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:10]

        self.settings.setValue("recentFiles", self.recent_files)
        self.refresh_recent_files()

    def open_selected_pdf(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)

        if path:
            self.pdfSelected.emit(path)
