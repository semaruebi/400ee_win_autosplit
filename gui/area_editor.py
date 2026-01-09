"""
AutoSplit GIEEE - エリア編集UI
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint, QTimer
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QBrush, QMouseEvent
from PIL import Image
from typing import Optional

from config import DetectionArea


class AreaEditorWidget(QWidget):
    """エリア編集ウィジェット"""
    
    areas_changed = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._image: Optional[Image.Image] = None
        self._target_window: Optional[str] = None
        self._areas: list[DetectionArea] = []
        self._dragging_idx: Optional[int] = None
        self._drag_offset = QPoint(0, 0)
        self._area_size_percent = 5  # 画面に対する%
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 説明
        info = QLabel("左クリック: エリア追加 / ドラッグ: 移動 / 右クリック: 削除")
        info.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(info)
        
        # プレビューエリア (クリック可能)
        self.preview_frame = ClickablePreview(self)
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 2px solid #444;
                border-radius: 8px;
            }
        """)
        self.preview_frame.setMinimumSize(400, 250)
        self.preview_frame.mouse_pressed.connect(self._on_mouse_press)
        self.preview_frame.mouse_moved.connect(self._on_mouse_move)
        self.preview_frame.mouse_released.connect(self._on_mouse_release)
        layout.addWidget(self.preview_frame)
        
        # ボタン
        btn_layout = QHBoxLayout()
        
        capture_btn = QPushButton("📷 画面キャプチャ")
        capture_btn.clicked.connect(self._capture_screen)
        capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn_layout.addWidget(capture_btn)
        
        clear_btn = QPushButton("🗑️ 全消去")
        clear_btn.clicked.connect(self._clear_areas)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #aa3333;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: #cc4444;
            }
        """)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        self.area_count_label = QLabel("エリア: 0個")
        self.area_count_label.setStyleSheet("color: #888;")
        btn_layout.addWidget(self.area_count_label)
        
        layout.addLayout(btn_layout)
    
    def set_areas(self, areas: list[DetectionArea]):
        self._areas = [DetectionArea(x=a.x, y=a.y) for a in areas]
        self._update_count()
        self.preview_frame.update()
    
    def get_areas(self) -> list[DetectionArea]:
        return [DetectionArea(x=a.x, y=a.y) for a in self._areas]
    
    def set_target_window(self, window_title: Optional[str]):
        """監視対象ウィンドウを設定"""
        self._target_window = window_title
        # 設定時に自動キャプチャ
        QTimer.singleShot(100, self._capture_screen)
    
    def _clear_areas(self):
        self._areas = []
        self.areas_changed.emit(self._areas)
        self._update_count()
        self.preview_frame.update()
    
    def _capture_screen(self):
        """監視対象ウィンドウをキャプチャしてプレビュー"""
        from capture import ScreenCapture
        
        try:
            capture = ScreenCapture()
            capture.set_target_window(self._target_window)
            self._image = capture.capture()
            if self._image:
                self._update_preview()
            else:
                print("キャプチャに失敗しました")
        except Exception as e:
            print(f"キャプチャエラー: {e}")
    
    def _update_preview(self):
        if self._image is None:
            return
        
        # リサイズしてプレビュー表示
        frame_w = self.preview_frame.width() - 10
        frame_h = self.preview_frame.height() - 10
        
        img_ratio = self._image.width / self._image.height
        frame_ratio = frame_w / frame_h
        
        if img_ratio > frame_ratio:
            new_w = frame_w
            new_h = int(frame_w / img_ratio)
        else:
            new_h = frame_h
            new_w = int(frame_h * img_ratio)
        
        resized = self._image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # QPixmapに変換
        qimage = QImage(
            resized.tobytes(),
            resized.width,
            resized.height,
            resized.width * 3,
            QImage.Format.Format_RGB888
        )
        self.preview_frame.set_pixmap(QPixmap.fromImage(qimage))
        self.preview_frame.update()
    
    def _on_mouse_press(self, pos: QPoint, button: Qt.MouseButton):
        img_pos = self._screen_to_percent(pos)
        if img_pos is None:
            return
        
        if button == Qt.MouseButton.LeftButton:
            # 既存エリアのドラッグチェック
            for i, area in enumerate(self._areas):
                if self._is_in_area(img_pos, area):
                    self._dragging_idx = i
                    return
            
            # 新規エリア追加
            self._areas.append(DetectionArea(x=img_pos[0], y=img_pos[1]))
            self.areas_changed.emit(self._areas)
            self._update_count()
            self.preview_frame.update()
        
        elif button == Qt.MouseButton.RightButton:
            # 右クリックでエリア削除
            for i, area in enumerate(self._areas):
                if self._is_in_area(img_pos, area):
                    del self._areas[i]
                    self.areas_changed.emit(self._areas)
                    self._update_count()
                    self.preview_frame.update()
                    return
    
    def _on_mouse_move(self, pos: QPoint):
        if self._dragging_idx is not None:
            img_pos = self._screen_to_percent(pos)
            if img_pos:
                x_percent = max(0, min(100 - self._area_size_percent, img_pos[0]))
                y_percent = max(0, min(100 - self._area_size_percent, img_pos[1]))
                self._areas[self._dragging_idx] = DetectionArea(x=x_percent, y=y_percent)
                self.preview_frame.update()
    
    def _on_mouse_release(self, pos: QPoint, button: Qt.MouseButton):
        if self._dragging_idx is not None:
            self.areas_changed.emit(self._areas)
        self._dragging_idx = None
    
    def _screen_to_percent(self, pos: QPoint) -> Optional[tuple[int, int]]:
        """画面座標を画像上のパーセント座標に変換"""
        img_rect = self.preview_frame.get_image_rect()
        if img_rect is None or img_rect.width() == 0 or img_rect.height() == 0:
            return None
        
        # 画像領域内かチェック
        if not img_rect.contains(pos):
            return None
        
        x_percent = int((pos.x() - img_rect.x()) / img_rect.width() * 100)
        y_percent = int((pos.y() - img_rect.y()) / img_rect.height() * 100)
        
        return (x_percent, y_percent)
    
    def _is_in_area(self, pos_percent: tuple[int, int], area: DetectionArea) -> bool:
        """ポイントがエリア内にあるかチェック"""
        return (area.x <= pos_percent[0] <= area.x + self._area_size_percent and
                area.y <= pos_percent[1] <= area.y + self._area_size_percent)
    
    def _update_count(self):
        count = len(self._areas)
        self.area_count_label.setText(f"エリア: {count}個")
    
    def get_draw_data(self):
        """描画用データを返す"""
        return self._areas, self._area_size_percent


class ClickablePreview(QFrame):
    """クリック可能なプレビューフレーム"""
    
    mouse_pressed = pyqtSignal(QPoint, Qt.MouseButton)
    mouse_moved = pyqtSignal(QPoint)
    mouse_released = pyqtSignal(QPoint, Qt.MouseButton)
    
    def __init__(self, editor: AreaEditorWidget, parent=None):
        super().__init__(parent)
        self._editor = editor
        self._pixmap: Optional[QPixmap] = None
        self._image_rect: Optional[QRect] = None
        self.setMouseTracking(True)
    
    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._update_image_rect()
    
    def get_image_rect(self) -> Optional[QRect]:
        return self._image_rect
    
    def _update_image_rect(self):
        if self._pixmap is None:
            self._image_rect = None
            return
        
        # 中央に配置
        x = (self.width() - self._pixmap.width()) // 2
        y = (self.height() - self._pixmap.height()) // 2
        self._image_rect = QRect(x, y, self._pixmap.width(), self._pixmap.height())
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_image_rect()
    
    def mousePressEvent(self, event: QMouseEvent):
        self.mouse_pressed.emit(event.pos(), event.button())
    
    def mouseMoveEvent(self, event: QMouseEvent):
        self.mouse_moved.emit(event.pos())
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        self.mouse_released.emit(event.pos(), event.button())
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 背景画像
        if self._pixmap and self._image_rect:
            painter.drawPixmap(self._image_rect, self._pixmap)
            
            # エリア描画
            areas, area_size_percent = self._editor.get_draw_data()
            
            pen = QPen(QColor(76, 175, 80), 3)
            painter.setPen(pen)
            brush = QBrush(QColor(76, 175, 80, 80))
            painter.setBrush(brush)
            
            for area in areas:
                x = self._image_rect.x() + int(area.x / 100 * self._image_rect.width())
                y = self._image_rect.y() + int(area.y / 100 * self._image_rect.height())
                size = int(area_size_percent / 100 * min(self._image_rect.width(), self._image_rect.height()))
                size = max(size, 20)
                painter.drawRect(x, y, size, size)
        else:
            # 画像なし
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                           "📷 画面キャプチャ をクリックしてください")
