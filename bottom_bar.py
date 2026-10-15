from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class BottomBar(QFrame):
    """
    Bottom bar with centered page number indicator and clean styling.
    """
    prevPageRequested = Signal()
    nextPageRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.current_page = 0
        self.total_pages = 0

        self.setStyleSheet("""
            BottomBar {
                background-color: #1a1a1d;
                border-top: 1px solid #2d2d31;
            }
            QLabel#PageIndicator {
                color: #e5e5ea;
                font-size: 12px;
                font-weight: 500;
                background-color: #27272a;
                border: 1px solid #3f3f46;
                border-radius: 12px;
                padding: 3px 14px;
            }
            QPushButton#NavBtn {
                background: transparent;
                color: #a1a1aa;
                border: none;
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton#NavBtn:hover {
                background-color: #2d2d31;
                color: #ffffff;
            }
            QPushButton#NavBtn:disabled {
                color: #52525b;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        # Left stretch to keep page indicator centered
        layout.addStretch()

        # Prev button
        self.prev_btn = QPushButton("◀", self)
        self.prev_btn.setObjectName("NavBtn")
        self.prev_btn.setToolTip("Previous Page")
        self.prev_btn.clicked.connect(self.prevPageRequested.emit)
        layout.addWidget(self.prev_btn)

        # Center page indicator
        self.page_label = QLabel("Page 0 / 0", self)
        self.page_label.setObjectName("PageIndicator")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)

        # Next button
        self.next_btn = QPushButton("▶", self)
        self.next_btn.setObjectName("NavBtn")
        self.next_btn.setToolTip("Next Page")
        self.next_btn.clicked.connect(self.nextPageRequested.emit)
        layout.addWidget(self.next_btn)

        # Right stretch
        layout.addStretch()

        self._update_display()

    def set_document(self, page_count: int):
        self.total_pages = page_count
        self.current_page = 0 if page_count > 0 else -1
        self._update_display()

    def set_page(self, page_idx: int):
        self.current_page = page_idx
        self._update_display()

    def _update_display(self):
        if self.total_pages <= 0:
            self.page_label.setText("No document")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
        else:
            self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < self.total_pages - 1)
