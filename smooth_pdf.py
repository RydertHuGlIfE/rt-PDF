from PySide6.QtCore import Qt, QEvent, QTimer, QSize, QRectF
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QAbstractScrollArea
from PySide6.QtPdf import QPdfDocument


class SmoothPdfViewer(QAbstractScrollArea):
    """Zoom ke dauraan purani rendered image scale hoti hai (instant, no flicker).
    Zoom rukne ke ~120ms baad pages sharp re-render hote hain.

    Public API:
        load(path) -> bool
        zoomin(value=1.1)     # zoom *= value
        zoomout(value=1.1)    # zoom /= value
        set_zoom(z)
        fit_width()
    """

    MIN_ZOOM = 0.25
    MAX_ZOOM = 5.0
    GAP = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = QPdfDocument(self)
        self.verticalScrollBar().setSingleStep(40)
        self.zoom = 1.0
        self.fit_mode = True

        self._cache = {}   # page -> (zoom, QImage)
        self._tops = []    # per page: (top, width, height) in pixels
        self._total_h = 0
        self._total_w = 0

        self._sharp = QTimer(self)
        self._sharp.setSingleShot(True)
        self._sharp.setInterval(120)
        self._sharp.timeout.connect(self.viewport().update)

        self.verticalScrollBar().valueChanged.connect(self.viewport().update)
        self.horizontalScrollBar().valueChanged.connect(self.viewport().update)

    # ---------- public API ----------
    def load(self, path):
        err = self.doc.load(path)
        if err != QPdfDocument.Error.None_:
            return False
        self._cache.clear()
        self.fit_width()
        self.verticalScrollBar().setValue(0)
        return True

    def zoomin(self, value=1.1, anchor=None):
        self.set_zoom(self.zoom * value, anchor)

    def zoomout(self, value=1.1, anchor=None):
        self.set_zoom(self.zoom / value, anchor)

    def set_zoom(self, z, anchor=None):
        z = max(self.MIN_ZOOM, min(z, self.MAX_ZOOM))
        vb, hb = self.verticalScrollBar(), self.horizontalScrollBar()
        vp = self.viewport()
        ax = anchor.x() if anchor is not None else vp.width() / 2
        ay = anchor.y() if anchor is not None else vp.height() / 2

        ry = (vb.value() + ay) / max(self._total_h, 1)
        rx = (hb.value() + ax) / max(self._total_w, 1)

        self.fit_mode = False
        self.zoom = z
        self._relayout()

        vb.setValue(round(ry * self._total_h - ay))
        hb.setValue(round(rx * self._total_w - ax))
        self._sharp.start()
        vp.update()

    def fit_width(self):
        self.fit_mode = True
        self._apply_fit()
        self._sharp.start()
        self.viewport().update()

    # ---------- internals ----------
    def _dpi_scale(self):
        return self.logicalDpiX() / 72.0

    def _apply_fit(self):
        n = self.doc.pageCount()
        if n == 0:
            return
        maxw = max(self.doc.pagePointSize(i).width() for i in range(n))
        avail = self.viewport().width() - 2 * self.GAP
        if maxw > 0 and avail > 0:
            self.zoom = max(self.MIN_ZOOM, min(avail / (maxw * self._dpi_scale()), self.MAX_ZOOM))
        self._relayout()

    def _relayout(self):
        s = self.zoom * self._dpi_scale()
        self._tops = []
        y = self.GAP
        maxw = 0
        for i in range(self.doc.pageCount()):
            sz = self.doc.pagePointSize(i)
            w, h = sz.width() * s, sz.height() * s
            self._tops.append((y, w, h))
            y += h + self.GAP
            maxw = max(maxw, w)
        self._total_h = y
        self._total_w = maxw + 2 * self.GAP

        vp = self.viewport()
        vb, hb = self.verticalScrollBar(), self.horizontalScrollBar()
        vb.setRange(0, max(0, int(self._total_h - vp.height())))
        vb.setPageStep(vp.height())
        hb.setRange(0, max(0, int(self._total_w - vp.width())))
        hb.setPageStep(vp.width())

    def _get_image(self, i, w, h):
        entry = self._cache.get(i)
        if entry and entry[0] == self.zoom:
            return entry[1]
        if entry and self._sharp.isActive():
            return entry[1]  # stale image, scaled at paint time
        dpr = self.devicePixelRatioF()
        img = self.doc.render(i, QSize(max(1, int(w * dpr)), max(1, int(h * dpr))))
        img.setDevicePixelRatio(dpr)
        self._cache[i] = (self.zoom, img)
        return img

    # ---------- events ----------
    def paintEvent(self, event):
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.viewport().rect(), QColor("#3a3a3a"))

        vy = self.verticalScrollBar().value()
        vh, vw = self.viewport().height(), self.viewport().width()
        xoff = max((vw - self._total_w) / 2, 0) - self.horizontalScrollBar().value()

        visible = set()
        for i, (top, w, h) in enumerate(self._tops):
            if top + h < vy or top > vy + vh:
                continue
            visible.add(i)
            rect = QRectF(xoff + (self._total_w - w) / 2, top - vy, w, h)
            p.fillRect(rect, QColor("white"))
            img = self._get_image(i, w, h)
            if img is not None:
                p.drawImage(rect, img)

        if len(self._cache) > 30:
            for k in [k for k in self._cache if k not in visible]:
                del self._cache[k]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_mode:
            self._apply_fit()
        else:
            self._relayout()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            step = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
            self.zoomin(step, anchor=event.position())
            event.accept()
            return
        super().wheelEvent(event)

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                factor = 1.0 + event.value()
                if factor > 0:
                    self.zoomin(factor, anchor=event.position())
                event.accept()
                return True
        return super().viewportEvent(event)