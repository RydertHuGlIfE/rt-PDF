import subprocess
import symtable

import sys

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView


class PDFView(QPdfView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gesture_zoom = 1.0

    def event(self, event):
        if event.type() == QEvent.Type.NativeGesture:
            if (
                event.gestureType()
                == Qt.NativeGestureType.ZoomNativeGesture
            ):
                factor = 1.0 + event.value()

                if factor > 0:
                    if self.zoomMode() == QPdfView.ZoomMode.FitToWidth:
                        self.gesture_zoom = self.zoomFactor()

                    self.gesture_zoom = max(
                        0.25,
                        min(self.gesture_zoom * factor, 5.0),
                    )

                    self.setZoomMode(QPdfView.ZoomMode.Custom)
                    self.setZoomFactor(self.gesture_zoom)

                    event.accept()
                    return True

        return super().event(event)

class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("rt-PDF")
        self.resize(1000, 700)
        self.customZoom = 1.0

        self.document = QPdfDocument(self)
        self.viewer = PDFView(self)
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


        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.zoomin)     #routing this action from this to the button action in linee 67ish 6-7
        self.addAction(zoom_in_action)

      
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.zoomout)
        self.addAction(zoom_out_action)

     
        fit_width_action = QAction("Fit to Width", self)
        fit_width_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_width_action.triggered.connect(self.fit_to_width)
        self.addAction(fit_width_action)

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
    
    def get_fit_zoom(self):
        page = self.document.pagePointSize(self.viewer.pageNavigator().currentPage())
        viewport_width = self.viewer.viewport().width()

        if page.width() <= 0:
            return 1.0
        return viewport_width / page.width()


    def zoomin(self):
        if self.viewer.zoomMode() == QPdfView.ZoomMode.FitToWidth:
            self.customZoom = self.get_fit_zoom()

        self.customZoom = min(self.customZoom * 1.1, 5.0)

        self.viewer.setZoomMode(QPdfView.ZoomMode.Custom)
        self.viewer.setZoomFactor(self.customZoom)


    def zoomout(self):
        if self.viewer.zoomMode() == QPdfView.ZoomMode.FitToWidth:
            self.customZoom = self.get_fit_zoom()

        self.customZoom = max(self.customZoom / 1.2, 0.25)

        self.viewer.setZoomMode(QPdfView.ZoomMode.Custom)
        self.viewer.setZoomFactor(self.customZoom)


    def fit_to_width(self):
        self.viewer.setZoomMode(QPdfView.ZoomMode.FitToWidth)


    






    #semimain
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

        
                
        
        
        