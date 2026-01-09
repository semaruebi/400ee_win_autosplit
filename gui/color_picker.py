"""
AutoSplit Screen Detector - スポイト機能（色抽出）
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QPen, QDragEnterEvent, QDropEvent
from PIL import Image
from pathlib import Path
from typing import Optional

from config import rgb_to_hex


class ColorPreview(QFrame):
    """色のプレビュー表示"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self.setStyleSheet("border: 2px solid #555; border-radius: 8px;")
        self._color = QColor(128, 128, 128)
    
    def set_color(self, r: int, g: int, b: int):
        self._color = QColor(r, g, b)
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            f"border: 2px solid #555; border-radius: 8px;"
        )
    
    def get_color(self) -> tuple[int, int, int]:
        return (self._color.red(), self._color.green(), self._color.blue())


class ImageDropZone(QLabel):
    """画像ドラッグ&ドロップゾーン"""
    
    image_dropped = pyqtSignal(Image.Image)  # PIL Image
    color_picked = pyqtSignal(int, int, int)  # R, G, B
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("""
            QLabel {
                border: 3px dashed #666;
                border-radius: 12px;
                background-color: #2a2a2a;
                color: #888;
                font-size: 14px;
            }
            QLabel:hover {
                border-color: #888;
                background-color: #333;
            }
        """)
        self.setText("🖼️ 画像をここにドラッグ&ドロップ\nまたはクリックして選択")
        
        self.setAcceptDrops(True)
        self._pil_image: Optional[Image.Image] = None
        self._pixmap: Optional[QPixmap] = None
        self._scale_factor: float = 1.0
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                QLabel {
                    border: 3px solid #4CAF50;
                    border-radius: 12px;
                    background-color: #1a3a1a;
                    color: #888;
                    font-size: 14px;
                }
            """)
    
    def dragLeaveEvent(self, event):
        self._reset_style()
    
    def dropEvent(self, event: QDropEvent):
        self._reset_style()
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self._load_image(file_path)
    
    def mousePressEvent(self, event):
        if self._pil_image is not None:
            # 画像上でクリック → スポイト
            self._pick_color(event.pos())
        else:
            # 画像なし → ファイル選択
            from PyQt6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getOpenFileName(
                self, "画像を選択", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            if file_path:
                self._load_image(file_path)
    
    def _load_image(self, file_path: str):
        """画像を読み込む"""
        try:
            self._pil_image = Image.open(file_path).convert("RGB")
            
            # QPixmapに変換
            qimage = QImage(
                self._pil_image.tobytes(),
                self._pil_image.width,
                self._pil_image.height,
                self._pil_image.width * 3,
                QImage.Format.Format_RGB888
            )
            self._pixmap = QPixmap.fromImage(qimage)
            
            # サイズ調整
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self._scale_factor = scaled.width() / self._pixmap.width()
            self.setPixmap(scaled)
            
            self.image_dropped.emit(self._pil_image)
            
        except Exception as e:
            self.setText(f"❌ 読み込みエラー: {e}")
    
    def _pick_color(self, pos):
        """クリック位置の色を取得"""
        if self._pil_image is None or self._pixmap is None:
            return
        
        # 表示座標を元画像座標に変換
        pixmap_rect = self.pixmap().rect()
        offset_x = (self.width() - pixmap_rect.width()) // 2
        offset_y = (self.height() - pixmap_rect.height()) // 2
        
        img_x = int((pos.x() - offset_x) / self._scale_factor)
        img_y = int((pos.y() - offset_y) / self._scale_factor)
        
        if 0 <= img_x < self._pil_image.width and 0 <= img_y < self._pil_image.height:
            r, g, b = self._pil_image.getpixel((img_x, img_y))
            self.color_picked.emit(r, g, b)
    
    def _reset_style(self):
        if self._pil_image is None:
            self.setStyleSheet("""
                QLabel {
                    border: 3px dashed #666;
                    border-radius: 12px;
                    background-color: #2a2a2a;
                    color: #888;
                    font-size: 14px;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #555;
                    border-radius: 12px;
                    background-color: #1a1a1a;
                }
            """)


class ColorPickerWidget(QWidget):
    """スポイト機能ウィジェット"""
    
    color_selected = pyqtSignal(str)  # #RRGGBB形式
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 説明
        info_label = QLabel("画像をドロップして、クリックで色を抽出できます")
        info_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(info_label)
        
        # ドロップゾーン
        self.drop_zone = ImageDropZone()
        self.drop_zone.color_picked.connect(self._on_color_picked)
        layout.addWidget(self.drop_zone)
        
        # 色プレビュー
        preview_layout = QHBoxLayout()
        
        self.color_preview = ColorPreview()
        preview_layout.addWidget(self.color_preview)
        
        self.color_label = QLabel("#------")
        self.color_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        preview_layout.addWidget(self.color_label)
        
        self.select_btn = QPushButton("この色を使用")
        self.select_btn.setEnabled(False)
        self.select_btn.clicked.connect(self._on_select)
        self.select_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        preview_layout.addStretch()
        preview_layout.addWidget(self.select_btn)
        
        layout.addLayout(preview_layout)
        
        self._current_color: Optional[str] = None
    
    def _on_color_picked(self, r: int, g: int, b: int):
        self.color_preview.set_color(r, g, b)
        hex_color = rgb_to_hex(r, g, b)
        self.color_label.setText(hex_color)
        self._current_color = hex_color
        self.select_btn.setEnabled(True)
    
    def _on_select(self):
        if self._current_color:
            self.color_selected.emit(self._current_color)
