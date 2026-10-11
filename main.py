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

        
                
        
        
        