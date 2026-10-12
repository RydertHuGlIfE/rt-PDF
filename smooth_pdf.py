import math

from PySide6.QtCore import Qt, QEvent, QTimer, QSize, QRect, QElapsedTimer
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QAbstractScrollArea
from PySide6.QtPdf import QPdfDocument


class SmoothPdfViewer(QAbstractScrollArea):
    """Public API:
        load(path) -> bool
        zoomin(value=1.1)     # zoom *= value
        zoomout(value=1.1)    # zoom /= value
        set_zoom(z)
        fit_width()
        smooth_scroll = True/False
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
        self._visible = set()

        # smooth scroll
        self.smooth_scroll = True
        self.mouse_speed = 10.0    # mouse wheel sensitivity
        self.touch_speed = 10.0    # touchpad sensitivity
        self.smooth_time = 120    # ms, bada = zyada dheere ruke
        self._pos = 0.0
        self.target_scroll = 0.0
        self._clock = QElapsedTimer()
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.scroll_timer.setInterval(16)  # ~60fps
        self.scroll_timer.timeout.connect(self.animate_scroll)

        self._sharp = QTimer(self)
        self._sharp.setSingleShot(True)
        self._sharp.setInterval(120)
        self._sharp.timeout.connect(self.viewport().update)

        self.verticalScrollBar().sliderPressed.connect(self.scroll_timer.stop)
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
        self.scroll_timer.stop()
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

    def _render(self, i, w, h):
        dpr = self.devicePixelRatioF()
        img = self.doc.render(i, QSize(max(1, round(w * dpr)), max(1, round(h * dpr))))
        img.setDevicePixelRatio(dpr)
        self._cache[i] = (self.zoom, img)
        return img

    def _get_image(self, i, w, h):
        entry = self._cache.get(i)
        if entry and entry[0] == self.zoom:
            return entry[1]
        if entry and self._sharp.isActive():
            return entry[1]  # stale image, scaled at paint time
        return self._render(i, w, h)

    def _prefetch(self):
        if not self._visible or self._sharp.isActive() or not self._tops:
            return
        lo = max(min(self._visible) - 2, 0)
        hi = min(max(self._visible) + 2, len(self._tops) - 1)
        for i in range(lo, hi + 1):
            e = self._cache.get(i)
            if e is None or e[0] != self.zoom:
                _, w, h = self._tops[i]
                self._render(i, round(w), round(h))
                QTimer.singleShot(0, self._prefetch)  # one page per tick
                return

    # ---------- events ----------
    def paintEvent(self, event):
        p = QPainter(self.viewport())
        p.fillRect(self.viewport().rect(), QColor("#3a3a3a"))

        vy = self.verticalScrollBar().value()
        vh, vw = self.viewport().height(), self.viewport().width()
        xoff = max((vw - self._total_w) / 2, 0) - self.horizontalScrollBar().value()

        visible = set()
        for i, (top, w, h) in enumerate(self._tops):
            if top + h < vy or top > vy + vh:
                continue
            visible.add(i)
            rect = QRect(round(xoff + (self._total_w - w) / 2),
                         round(top - vy), round(w), round(h))
            p.fillRect(rect, QColor("white"))
            img = self._get_image(i, rect.width(), rect.height())
            if img is not None:
                stale = abs(img.width() / img.devicePixelRatio() - rect.width()) > 1
                p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, stale)
                p.drawImage(rect, img)
        p.end()

        self._visible = visible
        if len(self._cache) > 30:
            for k in [k for k in self._cache if k not in visible]:
                del self._cache[k]
        QTimer.singleShot(0, self._prefetch)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_mode:
            self._apply_fit()
        else:
            self._relayout()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoomin(1.1 if event.angleDelta().y() > 0 else 1 / 1.1,
                        anchor=event.position())
            event.accept()
            return

        bar = self.verticalScrollBar()
        pd = event.pixelDelta().y()
        if pd != 0:  # touchpad
            delta = pd * self.touch_speed
        else:        # mouse wheel, 100px per notch
            delta = event.angleDelta().y() / 120 * 100 * self.mouse_speed

        if not self.smooth_scroll:
            self.scroll_timer.stop()
            bar.setValue(bar.value() - round(delta))
            event.accept()
            return

        if not self.scroll_timer.isActive():
            self._pos = float(bar.value())
            self.target_scroll = self._pos
            self._clock.start()
        self.target_scroll = max(bar.minimum(),
                                 min(self.target_scroll - delta, bar.maximum()))
        self.scroll_timer.start()
        event.accept()

    def animate_scroll(self):
        bar = self.verticalScrollBar()
        dt = min(self._clock.restart(), 50)
        diff = self.target_scroll - self._pos
        if abs(diff) < 0.5:
            bar.setValue(round(self.target_scroll))
            self.scroll_timer.stop()
            return
        self._pos += diff * (1 - math.exp(-dt / self.smooth_time))
        self._pos = max(float(bar.minimum()), min(self._pos, float(bar.maximum())))
        bar.setValue(round(self._pos))

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.NativeGesture:
            if event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                factor = 1.0 + event.value()
                if factor > 0:
                    self.zoomin(factor, anchor=event.position())
                event.accept()
                return True
        return super().viewportEvent(event)