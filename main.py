import subprocess
import symtable

import sys

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from smooth_pdf import SmoothPdfViewer


class PDFView(QPdfView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gesture_zoom = 1.0

    def set_zoom(self, z):
        vb, hb = self.verticalScrollBar(), self.horizontalScrollBar()
        vr = vb.value() / max(vb.maximum(), 1)
        hr = hb.value() / max(hb.maximum(), 1)
        self.setZoomMode(QPdfView.ZoomMode.Custom)
        self.setZoomFactor(z)
        QTimer.singleShot(0, lambda: (vb.setValue(int(vr * vb.maximum())),
                                      hb.setValue(int(hr * hb.maximum()))))

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

                    self.set_zoom(self.gesture_zoom)

                    event.accept()
                    return True

        return super().event(event)

class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("rt-PDF")
        self.resize(1000, 700)
        self.viewer = SmoothPdfViewer(self)

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

        zoomin = QAction("+", self)
        zoomin.triggered.connect(self.zoomin)
        toolbar.addAction(zoomin)

        zoomout = QAction("Fit to width", self)
        zoomout.triggered.connect(self.fit_to_width)
        toolbar.addAction(zoomout)
    
    def get_fit_zoom(self):
        page = self.document.pagePointSize(self.viewer.pageNavigator().currentPage())
        viewport_width = self.viewer.viewport().width()

        dpi = self.viewer.logicalDpiX()

        if page.width() <= 0 or dpi <=0:
            return 1.0
        return (viewport_width*72) / (page.width()*dpi)

    
    def apply_zoom(self, factor):
        if self.viewer.zoomMode() == QPdfView.ZoomMode.FitToWidth:
            self.customZoom = self.viewer.zoomFactor()

        self.customZoom = max(0.25, min(self.customZoom * factor, 5.0))

        self.viewer.set_zoom(self.customZoom)


    def zoomin(self):
        self.viewer.zoomin(1.1)


    def zoomout(self):
        self.viewer.zoomout(1.1)


    def fit_to_width(self):
        self.viewer.fit_width()


    #semimain
    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open PDF", 
            "", 
            "PDF Files (*.pdf)"
        )
        
        if not self.viewer.load(path):
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