import os
from PySide6.QtCore import Qt, QSize, QRect, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QListView,
    QFrame,
    QStyle,
    QStyledItemDelegate,
)


class ThumbDelegate(QStyledItemDelegate):
    """Paints each thumbnail centered, with a highlight frame hugging the page."""
    CARD_W, CARD_H, PAD = 130, 170, 5

    def paint(self, painter, option, index):
        icon = index.data(Qt.ItemDataRole.DecorationRole)
        card = QRect(0, 0, self.CARD_W, self.CARD_H)
        card.moveCenter(option.rect.center())
        frame = card.adjusted(-self.PAD, -self.PAD, self.PAD, self.PAD)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if option.state & QStyle.StateFlag.State_Selected:
            painter.setBrush(QColor(59, 130, 246, 50))
            painter.setPen(QPen(QColor("#60a5fa"), 2))
            painter.drawRoundedRect(frame, 6, 6)
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.setBrush(QColor(255, 255, 255, 13))
            painter.setPen(QPen(QColor("#3b82f6"), 2))
            painter.drawRoundedRect(frame, 6, 6)
        if isinstance(icon, QIcon):
            icon.paint(painter, card)
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.CARD_H + 2 * self.PAD + 8)


class ThumbnailSidebar(QWidget):
    pageSelected = Signal(int)
    visibilityToggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Must come AFTER super().__init__ so the stylesheet background is honored
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumWidth(140)
        self.setMaximumWidth(320)
        self.setFixedWidth(190)

        self._doc = None
        self._render_token = 0
        self.render_queue = []

        self.setStyleSheet("""
            ThumbnailSidebar {
                background-color: #202023;
                border-right: 1px solid #333336;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 4px;
            }
            QLabel#SidebarTitle {
                color: #f3f4f6;
                font-size: 13px;
                font-weight: 600;
                padding-left: 4px;
            }
            QPushButton#CollapseBtn {
                background: transparent;
                color: #9ca3af;
                font-size: 12px;
                font-weight: bold;
                border-radius: 6px;
                padding: 3px 6px;
                border: 1px solid transparent;
            }
            QPushButton#CollapseBtn:hover {
                background-color: #2d2d31;
                color: #ffffff;
                border: 1px solid #404045;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #3f3f46;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #52525b;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 6)
        layout.setSpacing(6)

        # Header with title and collapse button
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 2)
        self.title_label = QLabel("Pages", self)
        self.title_label.setObjectName("SidebarTitle")

        self.collapse_btn = QPushButton("◀", self)
        self.collapse_btn.setObjectName("CollapseBtn")
        self.collapse_btn.setToolTip("Collapse Sidebar (F4)")
        self.collapse_btn.clicked.connect(self.hide)

        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.collapse_btn)
        layout.addLayout(header)

        # Separator line
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #333336;")
        layout.addWidget(sep)

        # Thumbnail list
        self.list_widget = QListWidget(self)
        self.list_widget.setViewMode(QListView.ViewMode.ListMode)
        self.list_widget.setIconSize(QSize(130, 170))
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setItemDelegate(ThumbDelegate(self.list_widget))
        self.list_widget.setMouseTracking(True)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.visibilityToggled.emit(False)

    def showEvent(self, event):
        super().showEvent(event)
        self.visibilityToggled.emit(True)

    def load_document(self, doc):
        """Populates placeholder cards and begins progressive lazy thumbnail rendering."""
        self.list_widget.clear()
        self._doc = doc
        self._render_token += 1
        self.render_queue = []

        if not doc or doc.pageCount() <= 0:
            self.title_label.setText("Pages")
            return

        total_pages = doc.pageCount()
        self.title_label.setText(f"Pages ({total_pages})")

        # 1. Fill list with placeholder items instantly (no text overlay)
        for i in range(total_pages):
            item = QListWidgetItem()
            item.setToolTip(f"Page {i + 1}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            blank_pix = QPixmap(130, 170)
            blank_pix.fill(QColor("#2a2a2e"))
            item.setIcon(self._make_icon(blank_pix))
            self.list_widget.addItem(item)

        # 2. Queue thumbnails for lazy progressive rendering
        self.render_queue = list(range(total_pages))
        token = self._render_token
        QTimer.singleShot(15, lambda: self._render_next_thumbnail(token))

    def _render_next_thumbnail(self, token: int):
        if token != self._render_token or not self._doc or not self.render_queue:
            return

        page_idx = self.render_queue.pop(0)
        if page_idx < self._doc.pageCount():
            page_sz = self._doc.pagePointSize(page_idx)
            box_w, box_h = 130, 170
            scale = min(box_w / max(page_sz.width(), 1.0), box_h / max(page_sz.height(), 1.0))
            tw = max(1, int(page_sz.width() * scale))
            th = max(1, int(page_sz.height() * scale))

            img = self._doc.render(page_idx, QSize(tw, th))
            if not img.isNull():
                # PDF renders are transparent: composite onto white
                page = QPixmap(tw, th)
                page.fill(QColor("white"))
                p = QPainter(page)
                p.drawImage(0, 0, img)
                p.end()

                # Center on a fixed-size canvas so every card is uniform
                canvas = QPixmap(box_w, box_h)
                canvas.fill(Qt.GlobalColor.transparent)
                p = QPainter(canvas)
                p.drawPixmap((box_w - tw) // 2, (box_h - th) // 2, page)
                p.end()

                item = self.list_widget.item(page_idx)
                if item:
                    item.setIcon(self._make_icon(canvas))

        if self.render_queue:
            QTimer.singleShot(8, lambda: self._render_next_thumbnail(token))

    @staticmethod
    def _make_icon(pix: QPixmap) -> QIcon:
        # Same pixmap for selected state, so Qt doesn't tint the thumbnail dark
        icon = QIcon()
        for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
            icon.addPixmap(pix, mode)
        return icon

    def _on_item_clicked(self, item: QListWidgetItem):
        page_idx = item.data(Qt.ItemDataRole.UserRole)
        if page_idx is not None:
            self.pageSelected.emit(page_idx)

    def set_current_page(self, page_idx: int):
        """Highlights the currently active page in the sidebar."""
        if 0 <= page_idx < self.list_widget.count():
            item = self.list_widget.item(page_idx)
            if item and not item.isSelected():
                self.list_widget.blockSignals(True)
                self.list_widget.setCurrentRow(page_idx)
                self.list_widget.scrollToItem(
                    item, QListWidget.ScrollHint.EnsureVisible
                )
                self.list_widget.blockSignals(False)