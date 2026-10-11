import subprocess
import symtable
import sys 

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QAction
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView


class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("rt-PDF")
        self.resize(1000, 700)

        self.document = QPdfDocument(self)
        self.viewer = QPdfView(self)
        self.viewer.setDocument(self.document)

        #vertical+contscroll

        self.viewer.setPageMode(QPdfView.PageMode.MultiPage)
        self.viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)

        #main viewerr
        self.setCentralWidget(self.viewer)
        
        
        #toolbar
        toolbar = self.addToolBar("File")
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_pdf)
        toolbar.addAction(open_action)


        #zoom control
        toolbar.addSeparator()

        zoomout = QAction("-", self)
        zoomout.triggered.connect(self.zoomout)
        toolbar.addAction(zoomout)

        zoomout = QAction("+", self)
        zoomout.triggered.connect(self.zoomin)
        toolbar.addAction(zoomout)

        zoomout = QAction("Fit to width", self)
        zoomout.triggered.connect(self.fit_to_width)
        toolbar.addAction(zoomout)


    def zoomin(self):
        self.viewer.setZoomMode(QPdfView.ZoomMode.Custom)
        self.viewer.setZoomFactor(
            min(self.viewer.zoomFactor() * 1.1, 5.0)
        )

    def zoomout(self):
        self.viewer.setZoomMode(QPdfView.ZoomMode.Custom)
        self.viewer.setZoomFactor(
            max(self.viewer.zoomFactor() / 1.2, 0.25)
        )


    def fit_to_width(self):
        self.viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open PDF", 
            "", 
            "PDF Files (*.pdf)"
        )
        
        if not path:
            return 

        
        #load pdf
        error = self.document.load(path)

        if error != QPdfDocument.Error.None_:
            QMessageBox.warning(self, "Error", "Cant open PDF",)
            return 

        
        self.setWindowTitle(f"rt-PDF - {path.split('/')[-1]}")




def main():
    app = QApplication(sys.argv)

    window = PDFReader()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

        
                
        
        
        