import os
from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QSpinBox,
    QSlider,
    QLineEdit,
    QFileDialog,
    QFrame,
    QMessageBox,
)
from pdf_ops import parse_page_ranges


class VisualSplitBar(QWidget):
    """
    Renders a sleek, proportional colored bar representing how the document
    is segmented across pages.
    """
    COLORS = [
        QColor("#2563eb"),  # Royal Blue
        QColor("#0284c7"),  # Sky Blue
        QColor("#059669"),  # Emerald
        QColor("#7c3aed"),  # Purple
        QColor("#d97706"),  # Amber
        QColor("#db2777"),  # Pink
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.total_pages = 1
        self.segments = []  # list of (start_page, end_page, label)

    def set_data(self, total_pages: int, segments: list):
        self.total_pages = max(1, total_pages)
        self.segments = segments
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        r = 6  # border radius

        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#27272a"))
        painter.drawRoundedRect(0, 0, w, h, r, r)

        if not self.segments or self.total_pages <= 0:
            return

        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        curr_x = 0
        for idx, (start, end, label) in enumerate(self.segments):
            pages_in_seg = max(1, end - start + 1)
            frac = pages_in_seg / self.total_pages
            seg_w = round(frac * w) if idx < len(self.segments) - 1 else (w - curr_x)
            seg_w = max(2, seg_w)

            color = self.COLORS[idx % len(self.COLORS)]
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)

            # Draw segment rect
            rect = QRect(curr_x, 0, seg_w, h)
            painter.drawRoundedRect(rect, r, r)

            # Inner text if segment is wide enough
            if seg_w > 45:
                painter.setPen(QColor("#ffffff"))
                text = f"P{idx + 1}: {start}-{end}" if seg_w > 85 else f"{start}-{end}"
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

            curr_x += seg_w


class SplitDialog(QDialog):
    def __init__(self, file_path: str, total_pages: int, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.total_pages = total_pages
        self.filename = os.path.basename(file_path)

        self.setWindowTitle("Split PDF")
        self.setMinimumWidth(580)
        self.resize(580, 540)
        self.setStyleSheet("""
            QDialog {
                background-color: #18181b;
                color: #e5e5ea;
            }
            QLabel {
                color: #e5e5ea;
                font-size: 13px;
            }
            QLabel#DocTitle {
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#DocBadge {
                background-color: #27272a;
                color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 8px;
            }
            QRadioButton {
                color: #f3f4f6;
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QSpinBox, QLineEdit {
                background-color: #202024;
                color: #ffffff;
                border: 1px solid #3f3f46;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QSpinBox:focus, QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 18px;
                background-color: #27272a;
                border-left: 1px solid #3f3f46;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #3b82f6;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #27272a;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #2563eb;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #2563eb;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #93c5fd;
            }
            QFrame#CardBox {
                background-color: #202024;
                border: 1px solid #2e2e34;
                border-radius: 10px;
                padding: 14px;
            }
            QPushButton#ChipBtn {
                background-color: #27272a;
                color: #d1d5db;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton#ChipBtn:hover {
                background-color: #3b82f6;
                color: #ffffff;
                border-color: #3b82f6;
            }
            QPushButton#PrimaryBtn {
                background-color: #2563eb;
                color: #ffffff;
                font-weight: 600;
                font-size: 13px;
                padding: 8px 22px;
                border-radius: 8px;
                border: none;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #1d4ed8;
            }
            QPushButton#SecondaryBtn {
                background-color: #27272a;
                color: #d1d5db;
                font-weight: 500;
                font-size: 13px;
                padding: 8px 16px;
                border-radius: 8px;
                border: 1px solid #3f3f46;
            }
            QPushButton#SecondaryBtn:hover {
                background-color: #323238;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header: File name & page count badge
        header_layout = QHBoxLayout()
        doc_title = QLabel(self.filename, self)
        doc_title.setObjectName("DocTitle")
        doc_title.setWordWrap(True)

        badge_lbl = QLabel(f"{self.total_pages} Pages", self)
        badge_lbl.setObjectName("DocBadge")

        header_layout.addWidget(doc_title, 1)
        header_layout.addWidget(badge_lbl, 0)
        layout.addLayout(header_layout)

        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2e2e34;")
        layout.addWidget(sep)

        # Mode Selection
        self.mode_group = QButtonGroup(self)

        # ----------------- Mode 1: Split into N Parts (by Cut Page) -----------------
        self.radio_cut = QRadioButton("Split into parts at page (e.g. before and after page 29):", self)
        self.radio_cut.setChecked(True)
        self.mode_group.addButton(self.radio_cut)
        layout.addWidget(self.radio_cut)

        self.cut_card = QFrame(self)
        self.cut_card.setObjectName("CardBox")
        cut_layout = QVBoxLayout(self.cut_card)
        cut_layout.setContentsMargins(14, 12, 14, 12)
        cut_layout.setSpacing(10)

        # "How many splits do you want?"
        splits_row = QHBoxLayout()
        splits_label = QLabel("How many splits do you want?", self.cut_card)
        splits_label.setStyleSheet("font-weight: 600; color: #f3f4f6; font-size: 13px;")
        splits_row.addWidget(splits_label, 1)

        self.spin_num_splits = QSpinBox(self.cut_card)
        self.spin_num_splits.setRange(2, min(20, self.total_pages))
        self.spin_num_splits.setValue(2)
        self.spin_num_splits.setSuffix(" parts")
        self.spin_num_splits.setFixedWidth(90)
        self.spin_num_splits.valueChanged.connect(self._on_num_splits_changed)
        splits_row.addWidget(self.spin_num_splits)

        chip_2 = QPushButton("2 Splits", self.cut_card)
        chip_2.setObjectName("ChipBtn")
        chip_2.clicked.connect(lambda: self.spin_num_splits.setValue(2))
        splits_row.addWidget(chip_2)

        if self.total_pages >= 3:
            chip_3 = QPushButton("3 Splits", self.cut_card)
            chip_3.setObjectName("ChipBtn")
            chip_3.clicked.connect(lambda: self.spin_num_splits.setValue(3))
            splits_row.addWidget(chip_3)

        cut_layout.addLayout(splits_row)

        # --- 2 Splits section (Split before and after page X) ---
        self.two_split_widget = QWidget(self.cut_card)
        two_layout = QVBoxLayout(self.two_split_widget)
        two_layout.setContentsMargins(0, 0, 0, 0)
        two_layout.setSpacing(6)

        page_row = QHBoxLayout()
        page_label = QLabel("Split before and after page:", self.two_split_widget)
        page_row.addWidget(page_label, 1)

        default_split = 29 if (self.total_pages > 29) else max(1, self.total_pages // 2)
        self.spin_split_page = QSpinBox(self.two_split_widget)
        self.spin_split_page.setRange(1, max(1, self.total_pages - 1))
        self.spin_split_page.setValue(default_split)
        self.spin_split_page.setPrefix("Page ")
        self.spin_split_page.setFixedWidth(100)
        page_row.addWidget(self.spin_split_page)
        two_layout.addLayout(page_row)

        # Slider synced with spinbox
        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        lbl_p1 = QLabel("1", self.two_split_widget)
        lbl_p1.setStyleSheet("color: #71717a; font-size: 11px;")
        lbl_pend = QLabel(str(self.total_pages - 1), self.two_split_widget)
        lbl_pend.setStyleSheet("color: #71717a; font-size: 11px;")

        self.slider_split_page = QSlider(Qt.Orientation.Horizontal, self.two_split_widget)
        self.slider_split_page.setRange(1, max(1, self.total_pages - 1))
        self.slider_split_page.setValue(default_split)

        self.spin_split_page.valueChanged.connect(self.slider_split_page.setValue)
        self.slider_split_page.valueChanged.connect(self.spin_split_page.setValue)
        self.spin_split_page.valueChanged.connect(self._update_preview)

        slider_row.addWidget(lbl_p1)
        slider_row.addWidget(self.slider_split_page, 1)
        slider_row.addWidget(lbl_pend)
        two_layout.addLayout(slider_row)

        cut_layout.addWidget(self.two_split_widget)

        # --- 3+ Splits section (Multiple cut pages) ---
        self.multi_split_widget = QWidget(self.cut_card)
        multi_layout = QVBoxLayout(self.multi_split_widget)
        multi_layout.setContentsMargins(0, 0, 0, 0)
        multi_layout.setSpacing(6)

        cut_pts_label = QLabel("Cut pages (comma-separated):", self.multi_split_widget)
        multi_layout.addWidget(cut_pts_label)

        multi_input_row = QHBoxLayout()
        self.edit_cut_points = QLineEdit(self.multi_split_widget)
        self.edit_cut_points.setPlaceholderText("e.g. 10, 29")
        self.edit_cut_points.textChanged.connect(self._update_preview)
        multi_input_row.addWidget(self.edit_cut_points, 1)

        btn_even = QPushButton("Divide Evenly", self.multi_split_widget)
        btn_even.setObjectName("ChipBtn")
        btn_even.clicked.connect(self._distribute_evenly)
        multi_input_row.addWidget(btn_even, 0)
        multi_layout.addLayout(multi_input_row)

        self.multi_split_widget.hide()
        cut_layout.addWidget(self.multi_split_widget)

        layout.addWidget(self.cut_card)

        # ----------------- Mode 2: Custom Ranges -----------------
        self.radio_ranges = QRadioButton("Custom page ranges:", self)
        self.mode_group.addButton(self.radio_ranges)
        layout.addWidget(self.radio_ranges)

        ranges_row = QHBoxLayout()
        ranges_row.setContentsMargins(24, 0, 0, 0)
        self.edit_ranges = QLineEdit(self)
        self.edit_ranges.setPlaceholderText(f"e.g. 1-10, 11-{default_split}, {default_split + 1}-{self.total_pages}")
        self.edit_ranges.textChanged.connect(self._update_preview)
        ranges_row.addWidget(self.edit_ranges)
        layout.addLayout(ranges_row)

        # ----------------- Mode 3: Extract All -----------------
        self.radio_all = QRadioButton(f"Extract every page as separate 1-page PDF ({self.total_pages} files)", self)
        self.mode_group.addButton(self.radio_all)
        layout.addWidget(self.radio_all)

        self.radio_cut.toggled.connect(self._on_mode_toggled)
        self.radio_ranges.toggled.connect(self._on_mode_toggled)
        self.radio_all.toggled.connect(self._on_mode_toggled)

        # Visual Split Bar
        self.split_bar = VisualSplitBar(self)
        layout.addWidget(self.split_bar)

        # Live Summary Label
        self.summary_label = QLabel(self)
        self.summary_label.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 500;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # Output Folder selector
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(8)
        self.edit_folder = QLineEdit(self)
        default_dir = os.path.dirname(self.file_path) or os.path.expanduser("~")
        self.edit_folder.setText(default_dir)

        btn_browse = QPushButton("Browse...", self)
        btn_browse.setObjectName("SecondaryBtn")
        btn_browse.clicked.connect(self._browse_folder)

        folder_layout.addWidget(self.edit_folder, 1)
        folder_layout.addWidget(btn_browse, 0)

        folder_box = QVBoxLayout()
        folder_box.setSpacing(4)
        folder_box.addWidget(QLabel("Save split files in folder:", self))
        folder_box.addLayout(folder_layout)
        layout.addLayout(folder_box)

        # Dialog Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel", self)
        btn_cancel.setObjectName("SecondaryBtn")
        btn_cancel.clicked.connect(self.reject)

        self.btn_split = QPushButton("Split PDF", self)
        self.btn_split.setObjectName("PrimaryBtn")
        self.btn_split.clicked.connect(self._on_split_clicked)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_split)
        layout.addLayout(btn_layout)

        self._on_mode_toggled()
        self._update_preview()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            self.edit_folder.text() or os.path.dirname(self.file_path),
        )
        if folder:
            self.edit_folder.setText(folder)

    def _on_num_splits_changed(self, count: int):
        if count == 2:
            self.two_split_widget.show()
            self.multi_split_widget.hide()
        else:
            self.two_split_widget.hide()
            self.multi_split_widget.show()
            self._distribute_evenly()
        self._update_preview()

    def _distribute_evenly(self):
        k = self.spin_num_splits.value()
        if k <= 1:
            return
        cuts = []
        step = self.total_pages / k
        for i in range(1, k):
            cut_page = max(1, min(round(i * step), self.total_pages - 1))
            if cut_page not in cuts:
                cuts.append(cut_page)
        self.edit_cut_points.setText(", ".join(str(c) for c in cuts))

    def _on_mode_toggled(self):
        is_cut = self.radio_cut.isChecked()
        is_ranges = self.radio_ranges.isChecked()

        self.cut_card.setEnabled(is_cut)
        self.edit_ranges.setEnabled(is_ranges)
        self._update_preview()

    def _update_preview(self):
        if self.radio_cut.isChecked():
            k = self.spin_num_splits.value()
            if k == 2:
                split_at = self.spin_split_page.value()
                p1_count = split_at
                p2_count = self.total_pages - split_at
                segments = [
                    (1, split_at, "Part 1"),
                    (split_at + 1, self.total_pages, "Part 2"),
                ]
                self.split_bar.set_data(self.total_pages, segments)
                self.summary_label.setText(
                    f"Result: 2 files\n"
                    f"• Part 1: Pages 1 to {split_at} (Before & including page {split_at} — {p1_count} pages)\n"
                    f"• Part 2: Pages {split_at + 1} to {self.total_pages} (After page {split_at} — {p2_count} pages)"
                )
            else:
                text = self.edit_cut_points.text().strip()
                try:
                    cuts = [int(c.strip()) for c in text.split(",") if c.strip()]
                    valid_cuts = sorted(list(set(
                        max(1, min(c, self.total_pages - 1)) for c in cuts
                    )))
                    if not valid_cuts:
                        self.summary_label.setText("Enter cut pages above (e.g. 10, 29)")
                        return
                    segments = []
                    prev = 1
                    for cut in valid_cuts:
                        segments.append((prev, cut, f"Part {len(segments) + 1}"))
                        prev = cut + 1
                    segments.append((prev, self.total_pages, f"Part {len(segments) + 1}"))
                    self.split_bar.set_data(self.total_pages, segments)
                    info = [f"Part {i+1}: pgs {s[0]}-{s[1]} ({s[1]-s[0]+1} pgs)" for i, s in enumerate(segments)]
                    self.summary_label.setText(f"Result: {len(segments)} files\n" + "  •  ".join(info))
                except Exception:
                    self.summary_label.setText("Enter valid comma-separated cut page numbers (e.g. 10, 29)")
        elif self.radio_ranges.isChecked():
            text = self.edit_ranges.text().strip()
            if not text:
                self.summary_label.setText("Enter page ranges (e.g. 1-10, 11-29, 30-39)")
                self.split_bar.set_data(self.total_pages, [])
            else:
                try:
                    ranges = parse_page_ranges(text, self.total_pages)
                    segments = [(r[0], r[1], f"Part {i+1}") for i, r in enumerate(ranges)]
                    self.split_bar.set_data(self.total_pages, segments)
                    info = [f"Part {i+1}: pgs {r[0]}-{r[1]}" for i, r in enumerate(ranges)]
                    self.summary_label.setText(f"Result: {len(ranges)} files\n" + "  •  ".join(info))
                except Exception:
                    self.summary_label.setText("Invalid range format. Use e.g. 1-10, 11-29, 30-39")
                    self.split_bar.set_data(self.total_pages, [])
        else:
            self.split_bar.set_data(self.total_pages, [])
            self.summary_label.setText(f"Result: {self.total_pages} individual 1-page PDF files")

    def _on_split_clicked(self):
        folder = self.edit_folder.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Invalid Folder", "Please choose a valid output folder.")
            return

        if self.radio_cut.isChecked():
            k = self.spin_num_splits.value()
            if k > 2:
                text = self.edit_cut_points.text().strip()
                try:
                    cuts = [int(c.strip()) for c in text.split(",") if c.strip()]
                    if not cuts:
                        raise ValueError("Please enter at least one cut page.")
                except Exception as e:
                    QMessageBox.warning(self, "Invalid Cut Pages", f"Please check your cut page syntax:\n{e}")
                    return
        elif self.radio_ranges.isChecked():
            text = self.edit_ranges.text().strip()
            try:
                ranges = parse_page_ranges(text, self.total_pages)
                if not ranges:
                    raise ValueError("No ranges specified.")
            except Exception as e:
                QMessageBox.warning(self, "Invalid Ranges", f"Please check your page ranges syntax:\n{e}")
                return

        self.accept()

    def get_split_parameters(self):
        folder = self.edit_folder.text().strip()
        if self.radio_cut.isChecked():
            k = self.spin_num_splits.value()
            if k == 2:
                return "at_page", self.spin_split_page.value(), folder
            else:
                cuts = [int(c.strip()) for c in self.edit_cut_points.text().split(",") if c.strip()]
                return "cut_points", cuts, folder
        elif self.radio_ranges.isChecked():
            ranges = parse_page_ranges(self.edit_ranges.text().strip(), self.total_pages)
            return "ranges", ranges, folder
        else:
            return "all", None, folder
