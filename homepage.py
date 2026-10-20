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
    QStackedWidget,
    QFileDialog,
    QMessageBox,
    QFrame,
    QButtonGroup,
)

from pdf_ops import merge_pdf, split_pdf, convert_imagestopdf


class ToolCard(QFrame):
    clicked = Signal()

    def __init__(self, title_text, desc_text, action_text="Select", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            ToolCard {
                background-color: #202024;
                border: 1px solid #333338;
                border-radius: 12px;
            }
            ToolCard:hover {
                background-color: #27272c;
                border: 1.5px solid #3b82f6;
            }
            QLabel#Title {
                color: #ffffff;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#Desc {
                color: #9ca3af;
                font-size: 13px;
                line-height: 1.4;
            }
            QPushButton#ActionBtn {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 18px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#ActionBtn:hover {
                background-color: #1d4ed8;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)

        title_lbl = QLabel(title_text, self)
        title_lbl.setObjectName("Title")
        desc_lbl = QLabel(desc_text, self)
        desc_lbl.setObjectName("Desc")
        desc_lbl.setWordWrap(True)

        text_layout.addWidget(title_lbl)
        text_layout.addWidget(desc_lbl)
        layout.addLayout(text_layout, 1)

        btn = QPushButton(action_text, self)
        btn.setObjectName("ActionBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self.clicked.emit)
        layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class HomePage(QWidget):
    openRequested = Signal()
    pdfSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings("rt-PDF", "rt-PDF")
        self.recent_files = self.settings.value(
            "recentFiles", [], type=list
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(48, 36, 48, 36)
        main_layout.setSpacing(20)

        # Header: Title + Subtitle and Open PDF Button
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("rt-PDF", self)
        title.setStyleSheet("font-size: 34px; font-weight: 800; color: #ffffff;")

        subtitle = QLabel("Fast, lightweight Linux PDF reader & toolkit.", self)
        subtitle.setStyleSheet("font-size: 14px; color: #9ca3af;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        open_button = QPushButton("Open PDF", self)
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 22px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        open_button.clicked.connect(self.openRequested.emit)
        header_layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(header_layout)

        # Section Selector (Recent PDFs | PDF Tools)
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        nav_style = """
            QPushButton {
                background-color: #1e1e22;
                color: #9ca3af;
                font-size: 14px;
                font-weight: 600;
                padding: 8px 20px;
                border: 1px solid #333338;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #28282e;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
            }
        """

        self.btn_recent_tab = QPushButton("Recent PDFs", self)
        self.btn_recent_tab.setCheckable(True)
        self.btn_recent_tab.setChecked(True)
        self.btn_recent_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recent_tab.setStyleSheet(nav_style)

        self.btn_tools_tab = QPushButton("PDF Tools", self)
        self.btn_tools_tab.setCheckable(True)
        self.btn_tools_tab.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tools_tab.setStyleSheet(nav_style)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        self.tab_group.addButton(self.btn_recent_tab)
        self.tab_group.addButton(self.btn_tools_tab)

        self.btn_recent_tab.clicked.connect(lambda: self.sections.setCurrentIndex(0))
        self.btn_tools_tab.clicked.connect(lambda: self.sections.setCurrentIndex(1))

        nav_layout.addWidget(self.btn_recent_tab)
        nav_layout.addWidget(self.btn_tools_tab)
        nav_layout.addStretch()
        main_layout.addLayout(nav_layout)

        # Stacked Widget holding Section 0 (Recent Files) and Section 1 (PDF Tools)
        self.sections = QStackedWidget(self)

        # ---- Section 0: Recent Files ----
        recent_page = QWidget()
        recent_layout = QVBoxLayout(recent_page)
        recent_layout.setContentsMargins(0, 8, 0, 0)
        recent_layout.setSpacing(10)

        self.file_list = QListWidget(recent_page)
        self.file_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1d;
                border: 1px solid #2d2d32;
                border-radius: 12px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                background-color: #222226;
                color: #e5e5ea;
                font-size: 13px;
                font-weight: 500;
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 6px;
                border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background-color: #2c2c32;
                border: 1px solid #3f3f46;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #1e3a8a;
                border: 1px solid #3b82f6;
                color: #ffffff;
            }
        """)
        self.file_list.itemDoubleClicked.connect(self.open_selected_pdf)
        recent_layout.addWidget(self.file_list)
        self.sections.addWidget(recent_page)

        # ---- Section 1: PDF Tools ----
        tools_page = QWidget()
        tools_layout = QVBoxLayout(tools_page)
        tools_layout.setContentsMargins(0, 8, 0, 0)
        tools_layout.setSpacing(14)

        # 1. Merge PDFs Tool
        merge_card = ToolCard(
            title_text="Merge PDFs",
            desc_text="Combine multiple PDF documents into a single organized file.",
            action_text="Merge Files",
            parent=tools_page
        )
        merge_card.clicked.connect(self.on_merge_clicked)
        tools_layout.addWidget(merge_card)

        # 2. Split PDF Tool
        split_card = ToolCard(
            title_text="Split PDF",
            desc_text="Separate each page of a PDF document into individual files.",
            action_text="Split File",
            parent=tools_page
        )
        split_card.clicked.connect(self.on_split_clicked)
        tools_layout.addWidget(split_card)

        # 3. Images to PDF Tool
        img_card = ToolCard(
            title_text="Images to PDF",
            desc_text="Convert images (PNG, JPG, JPEG, WebP) into a clean PDF document.",
            action_text="Convert Images",
            parent=tools_page
        )
        img_card.clicked.connect(self.on_images_to_pdf_clicked)
        tools_layout.addWidget(img_card)

        tools_layout.addStretch()
        self.sections.addWidget(tools_page)

        main_layout.addWidget(self.sections, 1)

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
            empty_item = QListWidgetItem("No recent PDFs yet")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.file_list.addItem(empty_item)

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

    # ------------------ Tool Handlers ------------------

    def on_merge_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select PDF Files to Merge",
            "",
            "PDF Files (*.pdf)",
        )
        if not files:
            return

        if len(files) < 2:
            QMessageBox.warning(
                self,
                "Merge PDFs",
                "Please select at least 2 PDF files to merge.",
            )
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Merged PDF As",
            "merged.pdf",
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        try:
            merge_pdf(files, output_path)
            self.add_recent_file(output_path)
            reply = QMessageBox.question(
                self,
                "Merge Successful",
                f"Successfully merged {len(files)} PDFs!\n\nWould you like to open the merged PDF now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.pdfSelected.emit(output_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to merge PDFs:\n{e}")

    def on_split_clicked(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF to Split",
            "",
            "PDF Files (*.pdf)",
        )
        if not file:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder for Split Pages",
            os.path.dirname(file),
        )
        if not output_dir:
            return

        try:
            generated = split_pdf(file, output_dir)
            QMessageBox.information(
                self,
                "Split Complete",
                f"Successfully split '{os.path.basename(file)}' into {len(generated)} pages!\n\nSaved in:\n{output_dir}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to split PDF:\n{e}")

    def on_images_to_pdf_clicked(self):
        images, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images to Convert",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*)",
        )
        if not images:
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Converted PDF As",
            "converted_images.pdf",
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        try:
            convert_imagestopdf(images, output_path)
            self.add_recent_file(output_path)
            reply = QMessageBox.question(
                self,
                "Conversion Successful",
                f"Successfully converted {len(images)} images to PDF!\n\nWould you like to open the new PDF now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.pdfSelected.emit(output_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to convert images:\n{e}")
