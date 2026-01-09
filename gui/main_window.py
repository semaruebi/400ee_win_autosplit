"""
AutoSplit Screen Detector - メインウィンドウ (システムトレイ常駐)
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSystemTrayIcon, QMenu, QFrame,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QPixmap, QAction, QPainter, QColor, QFont

from config import AppConfig, load_config, save_config
from capture import ScreenCapture
from detector import detect_all_patterns, DetectionResult
from hotkey import HotkeyManager
from gui.settings_dialog import SettingsDialog


class MonitorThread(QThread):
    """画面監視スレッド"""
    
    detection_result = pyqtSignal(object)  # (detected, best) tuple
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._running = False
        self._capture = ScreenCapture()
    
    def run(self):
        self._running = True
        self._capture.set_target_window(self.config.target_window)
        
        while self._running:
            try:
                # キャプチャ
                image = self._capture.capture()
                if image is None:
                    self.error_occurred.emit("キャプチャに失敗しました")
                    self.msleep(1000)
                    continue
                
                # 検知 (エリア方式)
                detected, best = detect_all_patterns(
                    image,
                    self.config.patterns,
                    self.config.area_size
                )
                
                self.detection_result.emit((detected, best))
                
            except Exception as e:
                self.error_occurred.emit(str(e))
            
            self.msleep(self.config.check_interval_ms)
    
    def stop(self):
        self._running = False
        self.wait()
        self._capture.close()
    
    def update_config(self, config: AppConfig):
        self.config = config
        self._capture.set_target_window(config.target_window)


class StatusIndicator(QFrame):
    """ステータスインジケーター"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._status = "stopped"
    
    def set_status(self, status: str):
        self._status = status
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = {
            "stopped": QColor(128, 128, 128),
            "running": QColor(76, 175, 80),
            "detected": QColor(255, 193, 7),
            "error": QColor(244, 67, 54)
        }
        
        color = colors.get(self._status, colors["stopped"])
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 16, 16)


class MainWindow(QMainWindow):
    """メインウィンドウ"""
    
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self._monitor_thread = None
        self._hotkey_manager = HotkeyManager()
        self._last_detection_time = 0
        
        self._setup_ui()
        self._setup_tray()
    
    def _setup_ui(self):
        self.setWindowTitle("AutoSplit Screen Detector")
        self.setMinimumSize(450, 400)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #ccc;
            }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # ヘッダー
        header = QHBoxLayout()
        
        title = QLabel("🎮 AutoSplit Screen Detector")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.status_indicator = StatusIndicator()
        header.addWidget(self.status_indicator)
        
        self.status_label = QLabel("停止中")
        self.status_label.setStyleSheet("color: #888;")
        header.addWidget(self.status_label)
        
        layout.addLayout(header)
        
        # メインコントロール
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        control_layout = QVBoxLayout(control_frame)
        
        # 開始/停止ボタン
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ 監視開始")
        self.start_btn.setFixedHeight(50)
        self.start_btn.clicked.connect(self._toggle_monitoring)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.start_btn)
        
        settings_btn = QPushButton("⚙️ 設定")
        settings_btn.setFixedSize(80, 50)
        settings_btn.clicked.connect(self._open_settings)
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        btn_layout.addWidget(settings_btn)
        
        control_layout.addLayout(btn_layout)
        layout.addWidget(control_frame)
        
        # 一致率表示エリア
        match_frame = QFrame()
        match_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        match_layout = QVBoxLayout(match_frame)
        
        match_header = QHBoxLayout()
        match_header.addWidget(QLabel("📊 現在の一致率"))
        self.match_pattern_label = QLabel("")
        self.match_pattern_label.setStyleSheet("color: #888;")
        match_header.addWidget(self.match_pattern_label)
        match_header.addStretch()
        match_layout.addLayout(match_header)
        
        # プログレスバー
        self.match_progress = QProgressBar()
        self.match_progress.setRange(0, 100)
        self.match_progress.setValue(0)
        self.match_progress.setTextVisible(True)
        self.match_progress.setFormat("%v%")
        self.match_progress.setStyleSheet("""
            QProgressBar {
                background-color: #333;
                border: none;
                border-radius: 8px;
                height: 30px;
                text-align: center;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:1 #8BC34A);
                border-radius: 8px;
            }
        """)
        match_layout.addWidget(self.match_progress)
        
        # 詳細情報
        self.detection_info = QLabel("エリアを設定して監視を開始してください")
        self.detection_info.setStyleSheet("color: #888; font-size: 12px;")
        self.detection_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        match_layout.addWidget(self.detection_info)
        
        layout.addWidget(match_frame)
        
        # パターン一覧
        patterns_label = QLabel("📋 登録パターン")
        patterns_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa;")
        layout.addWidget(patterns_label)
        
        self.patterns_frame = QFrame()
        self.patterns_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
            }
        """)
        self.patterns_layout = QVBoxLayout(self.patterns_frame)
        self._update_patterns_display()
        layout.addWidget(self.patterns_frame)
        
        layout.addStretch()
        
        # フッター
        footer = QLabel("最小化するとシステムトレイに常駐します")
        footer.setStyleSheet("color: #666; font-size: 11px;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)
    
    def _setup_tray(self):
        """システムトレイの設定"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(76, 175, 80))
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "A")
        painter.end()
        
        icon = QIcon(pixmap)
        
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("AutoSplit Screen Detector")
        
        tray_menu = QMenu()
        
        show_action = QAction("表示", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)
        
        self.tray_toggle_action = QAction("監視開始", self)
        self.tray_toggle_action.triggered.connect(self._toggle_monitoring)
        tray_menu.addAction(self.tray_toggle_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("終了", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
    
    def _update_patterns_display(self):
        """パターン一覧の表示を更新"""
        while self.patterns_layout.count():
            item = self.patterns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        for pattern in self.config.patterns:
            area_count = len(pattern.areas) if pattern.areas else 0
            text = f"{'✅' if pattern.enabled else '⬜'} {pattern.name} ({area_count}エリア) → {pattern.hotkey}"
            label = QLabel(text)
            label.setStyleSheet("color: #bbb; padding: 5px;")
            self.patterns_layout.addWidget(label)
    
    def _toggle_monitoring(self):
        if self._monitor_thread is None or not self._monitor_thread.isRunning():
            self._start_monitoring()
        else:
            self._stop_monitoring()
    
    def _start_monitoring(self):
        # エリアが設定されているかチェック
        has_areas = any(pattern.areas for pattern in self.config.patterns if pattern.enabled)
        if not has_areas:
            self.detection_info.setText("⚠️ 検知エリアを設定してください (設定画面)")
            return
        
        self._monitor_thread = MonitorThread(self.config)
        self._monitor_thread.detection_result.connect(self._on_detection)
        self._monitor_thread.error_occurred.connect(self._on_error)
        self._monitor_thread.start()
        
        self.start_btn.setText("⏹️ 監視停止")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        self.status_indicator.set_status("running")
        self.status_label.setText("監視中")
        self.tray_toggle_action.setText("監視停止")
        self.detection_info.setText("画面を監視しています...")
    
    def _stop_monitoring(self):
        if self._monitor_thread:
            self._monitor_thread.stop()
            self._monitor_thread = None
        
        self.start_btn.setText("▶️ 監視開始")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.status_indicator.set_status("stopped")
        self.status_label.setText("停止中")
        self.tray_toggle_action.setText("監視開始")
        self.detection_info.setText("監視が停止されました")
        self.match_progress.setValue(0)
    
    def _on_detection(self, result_tuple):
        """検知結果を受信"""
        import time
        
        detected, best = result_tuple
        
        # リアルタイムで一致率を表示
        if best and best.total_areas > 0:
            self.match_progress.setValue(int(best.match_percent))
            self.match_pattern_label.setText(f"({best.pattern.name})")
            self.detection_info.setText(
                f"{best.matched_areas}/{best.total_areas}エリア一致 "
                f"(閾値: {best.pattern.threshold_percent}%)"
            )
            
            # プログレスバーの色を動的に変更
            if best.match_percent >= best.pattern.threshold_percent:
                self.match_progress.setStyleSheet("""
                    QProgressBar {
                        background-color: #333;
                        border: none;
                        border-radius: 8px;
                        height: 30px;
                        text-align: center;
                        color: white;
                        font-size: 16px;
                        font-weight: bold;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #FF9800, stop:1 #FFC107);
                        border-radius: 8px;
                    }
                """)
            else:
                self.match_progress.setStyleSheet("""
                    QProgressBar {
                        background-color: #333;
                        border: none;
                        border-radius: 8px;
                        height: 30px;
                        text-align: center;
                        color: white;
                        font-size: 16px;
                        font-weight: bold;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #4CAF50, stop:1 #8BC34A);
                        border-radius: 8px;
                    }
                """)
        
        if detected is None:
            return
        
        # クールダウンチェック
        now = time.time()
        if (now - self._last_detection_time) * 1000 < self.config.cooldown_ms:
            return
        
        # ホットキー送信
        if self._hotkey_manager.send_hotkey(detected.pattern.hotkey):
            self._last_detection_time = now
            self.status_indicator.set_status("detected")
            self.detection_info.setText(
                f"🎯 検知! {detected.pattern.name} → {detected.pattern.hotkey} 送信"
            )
            
            QTimer.singleShot(500, lambda: self.status_indicator.set_status("running"))
    
    def _on_error(self, error: str):
        self.status_indicator.set_status("error")
        self.detection_info.setText(f"❌ エラー: {error}")
    
    def _open_settings(self):
        # 監視中なら停止
        was_running = self._monitor_thread and self._monitor_thread.isRunning()
        if was_running:
            self._stop_monitoring()
        
        dialog = SettingsDialog(self.config, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()
    
    def _on_settings_changed(self, config: AppConfig):
        self.config = config
        self._update_patterns_display()
    
    def _show_window(self):
        self.showNormal()
        self.activateWindow()
    
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()
    
    def _quit_app(self):
        self._stop_monitoring()
        QApplication.quit()
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "AutoSplit Screen Detector",
            "システムトレイで動作を継続しています",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
