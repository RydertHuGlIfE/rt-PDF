
import sys

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
)

from smooth_pdf import SmoothPdfViewer


class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("rt-PDF")
        self.resize(1000, 700)

        # minapdf
        self.viewer = SmoothPdfViewer(self)
        self.setCentralWidget(self.viewer)

        
        toolbar = self.addToolBar("File")
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)

        # keyboshort
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

        # Zoooooooom
        toolbar.addSeparator()

        zoom_out_button = QAction("-", self)
        zoom_out_button.triggered.connect(self.zoomout)
        toolbar.addAction(zoom_out_button)

        zoom_in_button = QAction("+", self)
        zoom_in_button.triggered.connect(self.zoomin)
        toolbar.addAction(zoom_in_button)

        fit_button = QAction("Fit to Width", self)
        fit_button.triggered.connect(self.fit_to_width)
        toolbar.addAction(fit_button)

    def zoomin(self):
        self.viewer.zoomin(1.1)

    def zoomout(self):
        self.viewer.zoomout(1.1)

    def fit_to_width(self):
        self.viewer.fit_width()

    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF",
            "",
            "PDF Files (*.pdf)",
        )

        if not path:
            return

        if not self.viewer.load(path):
            QMessageBox.warning(
                self,
                "Error",
                "Can't open PDF",
            )
            return

        self.setWindowTitle(f"rt-PDF - {path.split('/')[-1]}")


def main():
    app = QApplication(sys.argv)

    window = PDFReader()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
