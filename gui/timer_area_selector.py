"""
AutoSplit GIEEE - タイマー領域選択ダイアログ
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QSlider
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush, QMouseEvent
from PIL import Image
from typing import Optional

from config import TimerArea
from capture import ScreenCapture


class TimerAreaSelector(QDialog):
    """タイマー領域をドラッグで選択するダイアログ (拡大/縮小対応)"""
    
    def __init__(self, window_title: str, current_area: TimerArea, parent=None):
        super().__init__(parent)
        self._window_title = window_title
        self._timer_area = TimerArea(
            x=current_area.x,
            y=current_area.y,
            width=current_area.width,
            height=current_area.height
        )
        self._image: Optional[Image.Image] = None
        self._zoom_factor = 1.0
        
        self._setup_ui()
        self._capture_screen()
    
    def _setup_ui(self):
        self.setWindowTitle("タイマー領域を選択")
        self.setMinimumSize(800, 700)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        layout = QVBoxLayout(self)
        
        # 説明
        info = QLabel("ドラッグしてメインタイマー領域を選択してください")
        info.setStyleSheet("color: #aaa; font-size: 13px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)
        
        # ズームコントロール
        zoom_layout = QHBoxLayout()
        zoom_layout.addStretch()
        zoom_layout.addWidget(QLabel("ズーム:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(50, 400)  # 50% - 400%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(200)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        zoom_layout.addWidget(self.zoom_slider)
        self.zoom_label = QLabel("100%")
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addStretch()
        layout.addLayout(zoom_layout)
        
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: 1px solid #444; background-color: #1a1a1a;")
        
        self.preview = DraggablePreview(self)
        self.preview.selection_changed.connect(self._on_selection_changed)
        scroll.setWidget(self.preview)
        layout.addWidget(scroll)
        
        # 現在の選択範囲
        self.area_label = QLabel(self._format_area())
        self.area_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        self.area_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.area_label)
        
        # ボタン
        btn_layout = QHBoxLayout()
        recapture_btn = QPushButton("🔄 再キャプチャ")
        recapture_btn.clicked.connect(self._capture_screen)
        recapture_btn.setStyleSheet("background-color: #555; border: none; padding: 10px 20px; border-radius: 6px; color: white;")
        btn_layout.addWidget(recapture_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("background-color: #444; border: none; padding: 10px 20px; border-radius: 6px; color: white;")
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("✓ 決定")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet("background-color: #4CAF50; border: none; padding: 10px 20px; border-radius: 6px; color: white; font-weight: bold;")
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
    
    def _capture_screen(self):
        try:
            capture = ScreenCapture()
            capture.set_target_window(self._window_title)
            self._image = capture.capture()
            if self._image:
                self._update_preview()
            else:
                self.area_label.setText("キャプチャに失敗しました")
        except Exception as e:
            self.area_label.setText(f"エラー: {e}")
    
    def _on_zoom_changed(self, value):
        self._zoom_factor = value / 100.0
        self.zoom_label.setText(f"{value}%")
        self._update_preview()
    
    def _update_preview(self):
        if self._image is None:
            return
        
        w = int(self._image.width * self._zoom_factor)
        h = int(self._image.height * self._zoom_factor)
        
        resized = self._image.resize((w, h), Image.Resampling.NEAREST) # 高速化のため
        
        qimage = QImage(
            resized.tobytes(),
            resized.width,
            resized.height,
            resized.width * 3,
            QImage.Format.Format_RGB888
        )
        pixmap = QPixmap.fromImage(qimage)
        self.preview.set_pixmap(pixmap)
        self.preview.set_selection(self._timer_area)
        self.preview.setFixedSize(w, h)
    
    def _on_selection_changed(self, x_percent: int, y_percent: int, w_percent: int, h_percent: int):
        self._timer_area = TimerArea(x=x_percent, y=y_percent, width=w_percent, height=h_percent)
        self.area_label.setText(self._format_area())
    
    def _format_area(self) -> str:
        ta = self._timer_area
        return f"X:{ta.x}% Y:{ta.y}% 幅:{ta.width}% 高:{ta.height}%"
    
    def get_timer_area(self) -> TimerArea:
        return self._timer_area


class DraggablePreview(QLabel): # QFrameからQLabelに変更
    """拡大対応の矩形選択プレビュー"""
    
    selection_changed = pyqtSignal(int, int, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap: Optional[QPixmap] = None
        self._selection_percent = (0, 0, 20, 10)
        self._dragging = False
        self._drag_start = QPoint()
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
    
    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.setPixmap(pixmap)
        self.update()
    
    def set_selection(self, area: TimerArea):
        self._selection_percent = (area.x, area.y, area.width, area.height)
        self.update()
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start = event.pos()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging:
            self._update_selection(self._drag_start, event.pos())
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging:
            self._update_selection(self._drag_start, event.pos())
            self._dragging = False
            self.selection_changed.emit(*self._selection_percent)
    
    def _update_selection(self, start: QPoint, end: QPoint):
        if not self._pixmap:
            return
        
        w = self._pixmap.width()
        h = self._pixmap.height()
        
        x1 = max(0, min(start.x(), w))
        y1 = max(0, min(start.y(), h))
        x2 = max(0, min(end.x(), w))
        y2 = max(0, min(end.y(), h))
        
        sx, sy = min(x1, x2), min(y1, y2)
        sw, sh = abs(x2 - x1), abs(y2 - y1)
        
        x_pct = int(sx / w * 100)
        y_pct = int(sy / h * 100)
        w_pct = max(1, int(sw / w * 100))
        h_pct = max(1, int(sh / h * 100))
        
        self._selection_percent = (x_pct, y_pct, w_pct, h_pct)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._pixmap:
            return
            
        painter = QPainter(self)
        x_pct, y_pct, w_pct, h_pct = self._selection_percent
        
        w = self._pixmap.width()
        h = self._pixmap.height()
        
        sel_x = int(x_pct / 100 * w)
        sel_y = int(y_pct / 100 * h)
        sel_w = int(w_pct / 100 * w)
        sel_h = int(h_pct / 100 * h)
        
        painter.setPen(QPen(QColor(255, 193, 7), 2))
        painter.setBrush(QBrush(QColor(255, 193, 7, 60)))
        painter.drawRect(sel_x, sel_y, sel_w, sel_h)
