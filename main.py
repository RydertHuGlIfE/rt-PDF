import sys
import os

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QStackedWidget,
)

from homepage import HomePage
from smooth_pdf import SmoothPdfViewer


class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("rt-PDF")
        self.resize(1000, 700)

        # Home page and PDF viewer
        self.home = HomePage(self)
        self.viewer = SmoothPdfViewer(self)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.home)
        self.pages.addWidget(self.viewer)

        self.setCentralWidget(self.pages)
        self.pages.setCurrentWidget(self.home)

        # Connect homepage signals
        self.home.openRequested.connect(self.open_pdf)
        self.home.pdfSelected.connect(self.open_recent_pdf)

        # File toolbar
        file_toolbar = self.addToolBar("File")

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_pdf)
        file_toolbar.addAction(open_action)

        home_action = QAction("Home", self)
        home_action.triggered.connect(self.show_home)
        file_toolbar.addAction(home_action)

        # Smooth scrolling toolbar
        smooth_toolbar = self.addToolBar("Smooth")

        smooth_action = QAction("Smooth", self)
        smooth_action.setCheckable(True)
        smooth_action.setChecked(True)
        smooth_action.toggled.connect(
            lambda checked: setattr(
                self.viewer, "smooth_scroll", checked
            )
        )
        smooth_toolbar.addAction(smooth_action)

        # Keyboard shortcuts
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.zoomin)
        self.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.zoomout)
        self.addAction(zoom_out_action)

        fit_width_action = QAction("Fit to Width", self)
        fit_width_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_width_action.triggered.connect(self.fit_to_width)
        self.addAction(fit_width_action)

        # Zoom toolbar controls
        smooth_toolbar.addSeparator()

        zoom_out_button = QAction("-", self)
        zoom_out_button.triggered.connect(self.zoomout)
        smooth_toolbar.addAction(zoom_out_button)

        zoom_in_button = QAction("+", self)
        zoom_in_button.triggered.connect(self.zoomin)
        smooth_toolbar.addAction(zoom_in_button)

        fit_button = QAction("Fit to Width", self)
        fit_button.triggered.connect(self.fit_to_width)
        smooth_toolbar.addAction(fit_button)

    # Zoom controls
    def zoomin(self):
        if self.pages.currentWidget() == self.viewer:
            self.viewer.zoomin(1.1)

    def zoomout(self):
        if self.pages.currentWidget() == self.viewer:
            self.viewer.zoomout(1.1)

    def fit_to_width(self):
        if self.pages.currentWidget() == self.viewer:
            self.viewer.fit_width()

    # Return to homepage
    def show_home(self):
        self.home.refresh_recent_files()
        self.pages.setCurrentWidget(self.home)
        self.setWindowTitle("rt-PDF")

    # Open PDF using file picker
    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF Files (*.pdf)",
        )

        if path:
            self.open_recent_pdf(path)

    # Open a selected or recently opened PDF
    def open_recent_pdf(self, path):
        if not os.path.isfile(path):
            QMessageBox.warning(
                self,
                "File Not Found",
                "This PDF no longer exists.",
            )
            self.home.refresh_recent_files()
            return

        if not self.viewer.load(path):
            QMessageBox.warning(
                self,
                "Error",
                "Can't open PDF.",
            )
            return

        # Save PDF in recent files
        self.home.add_recent_file(path)

        # Display the PDF
        self.pages.setCurrentWidget(self.viewer)
        self.setWindowTitle(f"rt-PDF - {os.path.basename(path)}")


def main():
    app = QApplication(sys.argv)

    window = PDFReader()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
