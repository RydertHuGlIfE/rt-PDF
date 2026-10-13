"""
annotation.py - Core Annotation Engine & Drawboard-style Floating Toolbar
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QToolButton, 
    QButtonGroup, QFrame, QColorDialog
)


# -------------------------------------------------------------
# 1. Tools & Data Structures
# -------------------------------------------------------------

class ToolType(Enum):
    HAND = "hand"              # Default smooth scrolling & navigation
    PEN = "pen"                # Freehand vector ink
    HIGHLIGHTER = "highlighter"# Semi-transparent ink (multiply blend)
    TEXT = "text"              # Text note annotation
    ERASER = "eraser"          # Click/drag over stroke to delete
    RECTANGLE = "rectangle"    # Shapes


@dataclass
class AnnotationStroke:
    tool: ToolType
    page_index: int
    points: List[QPointF] = field(default_factory=list)  # In PDF Page Points (DPI-independent)
    color: QColor = field(default_factory=lambda: QColor("#ff0000"))
    width: float = 2.0         # In PDF Page Points
    opacity: float = 1.0       # 0.0 to 1.0
    text: str = ""             # For text annotations
    font_size: float = 14.0    # For text annotations
    rect: Optional[QRectF] = None  # Used for shapes like rectangles

    def render(self, painter: QPainter, page_rect: QRectF, page_point_size):
        """
        Renders this stroke onto a QPainter already translated to screen coords.
        Scales points from PDF page coordinates -> current screen viewport pixels.
        """
        if page_point_size.width() <= 0 or page_point_size.height() <= 0:
            return

        painter.save()
        scale_x = page_rect.width() / page_point_size.width()
        scale_y = page_rect.height() / page_point_size.height()

        if self.tool in (ToolType.PEN, ToolType.HIGHLIGHTER) and len(self.points) > 1:
            pen_color = QColor(self.color)
            if self.tool == ToolType.HIGHLIGHTER:
                pen_color.setAlpha(int(min(self.opacity, 1.0) * 128))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            else:
                pen_color.setAlpha(int(min(self.opacity, 1.0) * 255))
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            pen = QPen(pen_color)
            pen.setWidthF(max(1.0, self.width * scale_x))
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
            path = QPainterPath()
            start = self.points[0]
            path.moveTo(page_rect.x() + start.x() * scale_x,
                        page_rect.y() + start.y() * scale_y)
            for pt in self.points[1:]:
                path.lineTo(page_rect.x() + pt.x() * scale_x,
                            page_rect.y() + pt.y() * scale_y)
            painter.drawPath(path)

        elif self.tool == ToolType.RECTANGLE and self.rect:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            screen_r = QRectF(
                page_rect.x() + self.rect.x() * scale_x,
                page_rect.y() + self.rect.y() * scale_y,
                self.rect.width() * scale_x,
                self.rect.height() * scale_y
            )
            rect_color = QColor(self.color)
            rect_color.setAlpha(int(min(self.opacity, 1.0) * 255))
            pen = QPen(rect_color, max(1.0, self.width * scale_x))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(screen_r)

        elif self.tool == ToolType.TEXT and self.text:
            from PySide6.QtGui import QFont
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            text_color = QColor(self.color)
            text_color.setAlpha(int(min(self.opacity, 1.0) * 255))
            painter.setPen(QPen(text_color))
            font = QFont("sans-serif", max(7, int(self.font_size * scale_x)))
            painter.setFont(font)
            pt = self.points[0] if self.points else QPointF(0, 0)
            painter.drawText(
                QPointF(page_rect.x() + pt.x() * scale_x, page_rect.y() + pt.y() * scale_y),
                self.text
            )

        painter.restore()


# -------------------------------------------------------------
# 2. Annotation Manager (Undo / Redo & Storage)
# -------------------------------------------------------------

class AnnotationManager:
    def __init__(self):
        # page_index -> list of AnnotationStroke
        self.pages_annotations: Dict[int, List[AnnotationStroke]] = {}
        self.undo_stack = []
        self.redo_stack = []

    def add_stroke(self, stroke: AnnotationStroke):
        page = stroke.page_index
        if page not in self.pages_annotations:
            self.pages_annotations[page] = []
        self.pages_annotations[page].append(stroke)
        self.undo_stack.append(('add', stroke))
        self.redo_stack.clear()

    def remove_stroke(self, stroke: AnnotationStroke):
        page = stroke.page_index
        if page in self.pages_annotations and stroke in self.pages_annotations[page]:
            self.pages_annotations[page].remove(stroke)
            self.undo_stack.append(('remove', stroke))
            self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        action, stroke = self.undo_stack.pop()
        page = stroke.page_index
        if action == 'add':
            self.pages_annotations[page].remove(stroke)
            self.redo_stack.append(('add', stroke))
        elif action == 'remove':
            self.pages_annotations[page].append(stroke)
            self.redo_stack.append(('remove', stroke))

    def redo(self):
        if not self.redo_stack:
            return
        action, stroke = self.redo_stack.pop()
        page = stroke.page_index
        if action == 'add':
            self.pages_annotations[page].append(stroke)
            self.undo_stack.append(('add', stroke))
        elif action == 'remove':
            self.pages_annotations[page].remove(stroke)
            self.undo_stack.append(('remove', stroke))

    def erase_at(self, page_index: int, pt: QPointF, radius: float = 10.0) -> bool:
        """
        Stroke Eraser: If pt is within 'radius' of any stroke, text, or shape, remove it.
        """
        strokes = self.pages_annotations.get(page_index, [])
        for stroke in reversed(strokes):
            for sp in stroke.points:
                dist_sq = (sp.x() - pt.x()) ** 2 + (sp.y() - pt.y()) ** 2
                if dist_sq <= radius ** 2:
                    self.remove_stroke(stroke)
                    return True
            if stroke.rect and stroke.rect.adjusted(-radius, -radius, radius, radius).contains(pt):
                self.remove_stroke(stroke)
                return True
        return False

    def load_from_pdf(self, input_path: str):
        """
        Load any existing Ink, Square, or FreeText annotations from the PDF file into memory
        so the user can view, edit, and erase them.
        """
        self.pages_annotations.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        try:
            import pymupdf
            doc = pymupdf.open(input_path)
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                for a in page.annots():
                    atype = a.type[0]
                    if atype == pymupdf.PDF_ANNOT_INK:
                        colors = a.colors.get('stroke') or [1.0, 0.0, 0.0]
                        c = QColor.fromRgbF(colors[0], colors[1], colors[2])
                        b = a.border
                        w = b.get('width', 2.0) if isinstance(b, dict) else 2.0
                        opacity = getattr(a, 'opacity', 1.0) or 1.0
                        tool = ToolType.HIGHLIGHTER if opacity < 0.7 else ToolType.PEN
                        for stroke_pts in a.vertices:
                            qpts = [QPointF(x, y) for x, y in stroke_pts]
                            if len(qpts) > 1:
                                s = AnnotationStroke(
                                    tool=tool,
                                    page_index=page_idx,
                                    points=qpts,
                                    color=c,
                                    width=float(w),
                                    opacity=float(opacity)
                                )
                                if page_idx not in self.pages_annotations:
                                    self.pages_annotations[page_idx] = []
                                self.pages_annotations[page_idx].append(s)

                    elif atype == pymupdf.PDF_ANNOT_SQUARE:
                        colors = a.colors.get('stroke') or [1.0, 0.0, 0.0]
                        c = QColor.fromRgbF(colors[0], colors[1], colors[2])
                        b = a.border
                        w = b.get('width', 2.0) if isinstance(b, dict) else 2.0
                        opacity = getattr(a, 'opacity', 1.0) or 1.0
                        r = a.rect
                        qr = QRectF(r.x0, r.y0, r.width, r.height)
                        s = AnnotationStroke(
                            tool=ToolType.RECTANGLE,
                            page_index=page_idx,
                            rect=qr,
                            color=c,
                            width=float(w),
                            opacity=float(opacity)
                        )
                        if page_idx not in self.pages_annotations:
                            self.pages_annotations[page_idx] = []
                        self.pages_annotations[page_idx].append(s)

                    elif atype == pymupdf.PDF_ANNOT_FREE_TEXT:
                        content = a.info.get('content', '')
                        colors = a.colors.get('stroke') or a.colors.get('text') or [0.0, 0.0, 0.0]
                        c = QColor.fromRgbF(colors[0], colors[1], colors[2]) if len(colors) >= 3 else QColor("#000000")
                        r = a.rect
                        pt = QPointF(r.x0, r.y0 + 12)
                        opacity = getattr(a, 'opacity', 1.0) or 1.0
                        s = AnnotationStroke(
                            tool=ToolType.TEXT,
                            page_index=page_idx,
                            points=[pt],
                            text=content,
                            color=c,
                            font_size=14.0,
                            opacity=float(opacity)
                        )
                        if page_idx not in self.pages_annotations:
                            self.pages_annotations[page_idx] = []
                        self.pages_annotations[page_idx].append(s)
            doc.close()
        except Exception as e:
            print(f"Error loading PDF annotations: {e}")

    def save_to_pdf(self, input_path: str, output_path: str) -> bool:
        """
        Burn annotations into the PDF as standard ISO PDF annotations using PyMuPDF.
        Removes previous annotations first so erased strokes are genuinely removed from the PDF.
        """
        try:
            import pymupdf
            import tempfile
            import os
            import shutil

            # Open document
            doc = pymupdf.open(input_path)

            # 1. Clean previous annotations on all pages so deletions take effect
            for page in doc:
                for annot in list(page.annots()):
                    if annot.type[0] in (pymupdf.PDF_ANNOT_INK, pymupdf.PDF_ANNOT_SQUARE, pymupdf.PDF_ANNOT_FREE_TEXT):
                        page.delete_annot(annot)

            # 2. Write the current surviving annotations
            for page_idx, strokes in self.pages_annotations.items():
                if page_idx >= len(doc):
                    continue
                page = doc[page_idx]

                for s in strokes:
                    r, g, b = s.color.redF(), s.color.greenF(), s.color.blueF()

                    if s.tool in (ToolType.PEN, ToolType.HIGHLIGHTER) and len(s.points) > 1:
                        pts = [(p.x(), p.y()) for p in s.points]
                        annot = page.add_ink_annot([pts])
                        annot.set_colors(stroke=(r, g, b))
                        annot.set_border(width=s.width)
                        annot.set_opacity(min(s.opacity, 0.5) if s.tool == ToolType.HIGHLIGHTER else s.opacity)
                        annot.update()

                    elif s.tool == ToolType.RECTANGLE and s.rect:
                        rect = pymupdf.Rect(
                            s.rect.x(), s.rect.y(),
                            s.rect.x() + s.rect.width(), s.rect.y() + s.rect.height()
                        )
                        annot = page.add_rect_annot(rect)
                        annot.set_colors(stroke=(r, g, b))
                        annot.set_border(width=s.width)
                        annot.set_opacity(s.opacity)
                        annot.update()

                    elif s.tool == ToolType.TEXT and s.text:
                        pt = s.points[0] if s.points else QPointF(0, 0)
                        approx_width = max(120.0, len(s.text) * s.font_size * 0.7)
                        approx_height = s.font_size * 1.6
                        rect = pymupdf.Rect(pt.x(), pt.y(), pt.x() + approx_width, pt.y() + approx_height)
                        annot = page.add_freetext_annot(rect, s.text, fontsize=s.font_size, text_color=(r, g, b))
                        annot.set_opacity(s.opacity)
                        annot.update()

            # Save to temporary file first to support overwriting input_path safely
            temp_fd, temp_path = tempfile.mkstemp(suffix=".pdf")
            os.close(temp_fd)
            doc.save(temp_path, incremental=False, encryption=pymupdf.PDF_ENCRYPT_KEEP)
            doc.close()

            shutil.move(temp_path, output_path)
            return True
        except Exception as e:
            print(f"Error saving PDF annotations: {e}")
            return False


# -------------------------------------------------------------
# 3. Floating Toolbar Widget (No emojis, clean text and controls)
# -------------------------------------------------------------

class AnnotationToolbar(QFrame):
    """
    Floating pill-shaped toolbar:
    Tools (Pan, Pen, Highlighter, Text, Box, Eraser) | Size & Opacity | Palette + Custom Color | Undo / Redo
    """
    toolChanged = Signal(ToolType)
    colorChanged = Signal(QColor)
    widthChanged = Signal(float)
    opacityChanged = Signal(float)
    undoRequested = Signal()
    redoRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_color = QColor("#ef4444")
        self.current_width = 3.0
        self.current_opacity = 1.0

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 28, 30, 0.95);
                border-radius: 18px;
                border: 1px solid #48484a;
            }
            QPushButton {
                background: transparent;
                color: #e5e5ea;
                font-size: 12px;
                font-weight: 600;
                padding: 5px 9px;
                border-radius: 10px;
                border: none;
            }
            QPushButton:checked {
                background-color: #0a84ff;
                color: #ffffff;
            }
            QPushButton:hover:!checked {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QLabel {
                color: #aeaeb2;
                font-size: 11px;
                font-weight: 500;
            }
            QSpinBox {
                background-color: #2c2c2e;
                color: #ffffff;
                border: 1px solid #3a3a3c;
                border-radius: 6px;
                padding: 2px 5px;
                font-size: 11px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        # Tool button group
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_hand = self._create_tool_btn("Pan", ToolType.HAND, checked=True)
        self.btn_pen = self._create_tool_btn("Pen", ToolType.PEN)
        self.btn_highlighter = self._create_tool_btn("Highlighter", ToolType.HIGHLIGHTER)
        self.btn_text = self._create_tool_btn("Text", ToolType.TEXT)
        self.btn_rect = self._create_tool_btn("Box", ToolType.RECTANGLE)
        self.btn_eraser = self._create_tool_btn("Eraser", ToolType.ERASER)

        layout.addWidget(self.btn_hand)
        layout.addWidget(self.btn_pen)
        layout.addWidget(self.btn_highlighter)
        layout.addWidget(self.btn_text)
        layout.addWidget(self.btn_rect)
        layout.addWidget(self.btn_eraser)

        # Separator
        layout.addWidget(self._create_separator())

        # Size control
        from PySide6.QtWidgets import QLabel, QSpinBox
        layout.addWidget(QLabel("Size:"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 40)
        self.size_spin.setValue(int(self.current_width))
        self.size_spin.setSuffix(" px")
        self.size_spin.valueChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_spin)

        # Opacity control
        layout.addWidget(QLabel("Opacity:"))
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(10, 100)
        self.opacity_spin.setSingleStep(10)
        self.opacity_spin.setValue(int(self.current_opacity * 100))
        self.opacity_spin.setSuffix("%")
        self.opacity_spin.valueChanged.connect(self._on_opacity_changed)
        layout.addWidget(self.opacity_spin)

        # Separator
        layout.addWidget(self._create_separator())

        # Color presets
        self.colors = [
            QColor("#ef4444"),  # Red
            QColor("#f97316"),  # Orange
            QColor("#eab308"),  # Yellow
            QColor("#22c55e"),  # Green
            QColor("#06b6d4"),  # Cyan
            QColor("#3b82f6"),  # Blue
            QColor("#a855f7"),  # Purple
            QColor("#111827"),  # Black
        ]

        self.color_buttons = []
        for color in self.colors:
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._update_swatch_style(btn, color, is_active=(color == self.current_color))
            btn.clicked.connect(lambda _, c=color: self.set_active_color(c))
            layout.addWidget(btn)
            self.color_buttons.append((btn, color))

        # Custom Color Picker button (no emoji)
        self.btn_custom_color = QPushButton("Color")
        self.btn_custom_color.setToolTip("Pick Custom Color")
        self.btn_custom_color.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom_color.clicked.connect(self.choose_custom_color)
        layout.addWidget(self.btn_custom_color)

        # Separator
        layout.addWidget(self._create_separator())

        # Undo / Redo
        btn_undo = QPushButton("Undo")
        btn_undo.setToolTip("Undo (Ctrl+Z)")
        btn_undo.clicked.connect(self.undoRequested.emit)
        layout.addWidget(btn_undo)

        btn_redo = QPushButton("Redo")
        btn_redo.setToolTip("Redo (Ctrl+Y)")
        btn_redo.clicked.connect(self.redoRequested.emit)
        layout.addWidget(btn_redo)

    def _create_tool_btn(self, text, tool_type, checked=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.toolChanged.emit(tool_type))
        self.btn_group.addButton(btn)
        return btn

    def _create_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #48484a;")
        return sep

    def _update_swatch_style(self, btn: QPushButton, color: QColor, is_active: bool = False):
        border = "2px solid #ffffff" if is_active else "1px solid #666666"
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name()};
                border-radius: 10px;
                border: {border};
            }}
            QPushButton:hover {{
                border: 2px solid #38bdf8;
            }}
        """)

    def set_active_color(self, color: QColor):
        if not color.isValid():
            return
        self.current_color = color
        for btn, c in self.color_buttons:
            self._update_swatch_style(btn, c, is_active=(c.name() == color.name()))
        self.colorChanged.emit(color)

    def choose_custom_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Select Color")
        if color.isValid():
            self.set_active_color(color)

    def _on_size_changed(self, val):
        self.current_width = float(val)
        self.widthChanged.emit(self.current_width)

    def _on_opacity_changed(self, val):
        self.current_opacity = val / 100.0
        self.opacityChanged.emit(self.current_opacity)
