import sys
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QStackedWidget,
    QSplitter,
    QWidget,
    QVBoxLayout,
)

from homepage import HomePage
from smooth_pdf import SmoothPdfViewer
from annotation import AnnotationToolbar, ToolType
from sidebar import ThumbnailSidebar
from bottom_bar import BottomBar  # rename if your BottomBar file has another module name


class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("rt-PDF")
        self.resize(1000, 700)
        self.setAcceptDrops(True)

        # Apply global dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121214;
                color: #e5e5ea;
            }
            QToolBar {
                background-color: #18181b;
                border-bottom: 1px solid #27272a;
                spacing: 4px;
                padding: 4px 8px;
            }
            QToolBar::separator {
                width: 1px;
                background-color: #333338;
                margin: 4px 6px;
            }
            QToolButton {
                background-color: transparent;
                color: #e5e5ea;
                font-size: 13px;
                font-weight: 500;
                padding: 5px 12px;
                border-radius: 6px;
                border: 1px solid transparent;
            }
            QToolButton:hover {
                background-color: #27272a;
                color: #ffffff;
                border: 1px solid #3f3f46;
            }
            QToolButton:pressed {
                background-color: #1f2937;
            }
            QToolButton:checked {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #3b82f6;
            }
            QStackedWidget {
                background-color: #121214;
            }
            QMessageBox {
                background-color: #18181b;
            }
            QMessageBox QLabel {
                color: #e5e5ea;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                background-color: #27272a;
                color: #ffffff;
                font-size: 13px;
                padding: 6px 18px;
                border-radius: 6px;
                border: 1px solid #3f3f46;
            }
            QMessageBox QPushButton:hover {
                background-color: #2563eb;
                border-color: #3b82f6;
            }
            QDialog {
                background-color: #18181b;
                color: #e5e5ea;
            }
        """)

        # Home page, sidebar, PDF viewer, and bottom bar
        self.home = HomePage(self)
        self.viewer = SmoothPdfViewer(self)
        self.sidebar = ThumbnailSidebar(self)
        self.bottom_bar = BottomBar(self)

        # Splitter to hold retractable sidebar and viewer
        self.viewer_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.viewer_splitter.addWidget(self.sidebar)
        self.viewer_splitter.addWidget(self.viewer)
        self.viewer_splitter.setCollapsible(0, True)
        self.viewer_splitter.setCollapsible(1, False)
        self.viewer_splitter.setSizes([190, 810])
        self.viewer_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #2b2b2e;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #3b82f6;
            }
        """)

        # Viewer page = splitter on top, bottom bar underneath
        self.viewer_page = QWidget()
        viewer_layout = QVBoxLayout(self.viewer_page)
        viewer_layout.setContentsMargins(0, 0, 0, 0)
        viewer_layout.setSpacing(0)
        viewer_layout.addWidget(self.viewer_splitter, 1)
        viewer_layout.addWidget(self.bottom_bar, 0)

        self.pages = QStackedWidget()
        self.pages.addWidget(self.home)
        self.pages.addWidget(self.viewer_page)

        self.setCentralWidget(self.pages)
        self.pages.setCurrentWidget(self.home)

        self.current_pdf_path = None

        # Floating annotation toolbar positioned over viewer
        self.ann_toolbar = AnnotationToolbar(self.viewer)
        self.viewer.ann_toolbar = self.ann_toolbar
        self.ann_toolbar.toolChanged.connect(self.viewer.set_tool)
        self.ann_toolbar.colorChanged.connect(self.viewer.set_color)
        self.ann_toolbar.widthChanged.connect(self.viewer.set_stroke_width)
        self.ann_toolbar.opacityChanged.connect(self.viewer.set_opacity)
        self.ann_toolbar.undoRequested.connect(self.viewer.undo)
        self.ann_toolbar.redoRequested.connect(self.viewer.redo)
        self.ann_toolbar.hide()

        # Connect sidebar, viewer, and bottom bar signals
        self.sidebar.pageSelected.connect(self.viewer.scroll_to_page)
        self.viewer.pageChanged.connect(self.sidebar.set_current_page)
        self.viewer.pageChanged.connect(self.bottom_bar.set_page)
        self.bottom_bar.prevPageRequested.connect(self.viewer.prev_page)
        self.bottom_bar.nextPageRequested.connect(self.viewer.next_page)

        # Connect homepage signals
        self.home.openRequested.connect(self.open_pdf)
        self.home.pdfSelected.connect(self.open_recent_pdf)

        # File toolbar
        file_toolbar = self.addToolBar("File")

        self.sidebar_action = QAction("Sidebar", self)
        self.sidebar_action.setCheckable(True)
        self.sidebar_action.setChecked(True)
        self.sidebar_action.setShortcut(QKeySequence("F4"))
        self.sidebar_action.toggled.connect(self.toggle_sidebar)
        file_toolbar.addAction(self.sidebar_action)
        self.sidebar.visibilityToggled.connect(self.sidebar_action.setChecked)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_pdf)
        file_toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_pdf)
        file_toolbar.addAction(save_action)

        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_as_pdf)
        file_toolbar.addAction(save_as_action)

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

        # Undo / Redo shortcuts
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.viewer.undo)
        self.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.viewer.redo)
        self.addAction(redo_action)

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

    def toggle_sidebar(self, checked):
        self.sidebar.setVisible(checked)

    # Zoom controls
    def zoomin(self):
        if self.pages.currentWidget() != self.home:
            self.viewer.zoomin(1.1)

    def zoomout(self):
        if self.pages.currentWidget() != self.home:
            self.viewer.zoomout(1.1)

    def fit_to_width(self):
        if self.pages.currentWidget() != self.home:
            self.viewer.fit_width()

    # Return to homepage
    def show_home(self):
        self.ann_toolbar.hide()
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
        self.current_pdf_path = path

        # Load thumbnails into sidebar and page count into bottom bar
        self.sidebar.load_document(self.viewer.doc)
        self.bottom_bar.set_document(self.viewer.doc.pageCount())

        # Display the PDF with sidebar
        self.pages.setCurrentWidget(self.viewer_page)
        self.setWindowTitle(f"rt-PDF - {os.path.basename(path)}")
        self.ann_toolbar.show()
        self.ann_toolbar.raise_()
        self.ann_toolbar.adjustSize()
        self.ann_toolbar.move(
            max(10, (self.viewer.width() - self.ann_toolbar.width()) // 2),
            20
        )

    def save_pdf(self):
        if not self.current_pdf_path:
            return
        if self.viewer.ann_manager.save_to_pdf(self.current_pdf_path, self.current_pdf_path):
            QMessageBox.information(self, "Saved", "Annotations saved successfully to the PDF!")
        else:
            QMessageBox.warning(self, "Error", "Failed to save annotations to the PDF.")

    def save_as_pdf(self):
        if not self.current_pdf_path:
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            self.current_pdf_path,
            "PDF Files (*.pdf)",
        )
        if path:
            if self.viewer.ann_manager.save_to_pdf(self.current_pdf_path, path):
                self.current_pdf_path = path
                self.home.add_recent_file(path)
                self.setWindowTitle(f"rt-PDF - {os.path.basename(path)}")
                QMessageBox.information(self, "Saved", f"Saved successfully to:\n{os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "Error", "Failed to save annotations.")

    # Drag and drop support
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf") and os.path.isfile(path):
                self.open_recent_pdf(path)
                event.acceptProposedAction()
                return


def main():
    app = QApplication(sys.argv)

    # Set application-wide dark palette so all native dialogs match
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#121214"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e5e5ea"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#18181b"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e1e22"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#27272a"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e5e5ea"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#222226"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e5e5ea"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    window = PDFReader()
    window.show()

    # Open PDF passed via CLI argument if present
    if len(sys.argv) > 1:
        cli_path = sys.argv[1]
        if os.path.isfile(cli_path):
            window.open_recent_pdf(os.path.abspath(cli_path))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()