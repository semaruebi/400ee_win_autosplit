"""
AutoSplit GIEEE - メインウィンドウ (システムトレイ常駐)
"""
import sys
import os
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSystemTrayIcon, QMenu, QFrame,
    QProgressBar
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QIcon, QPixmap, QAction, QPainter, QColor, QFont
from PIL import Image

from config import AppConfig, load_config, save_config
from capture import ScreenCapture
from detector import detect_all_patterns, DetectionResult, crop_timer_area, images_are_similar
from hotkey import HotkeyManager
from gui.settings_dialog import SettingsDialog
from gui.styles import load_fonts, APP_STYLE_TEMPLATE


class MonitorThread(QThread):
    """
    画面をじっと見つめ続ける監視役スレッドです。
    """
    
    detection_result = pyqtSignal(object)  # (detected, best) -> 何か見つけたら報告
    timer_status_changed = pyqtSignal(bool)  # True = 凍結中, False = 動いてる
    error_occurred = pyqtSignal(str)
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._running = False
        self._capture = ScreenCapture()
        self._livesplit_capture = ScreenCapture()
        
        # タイムライン監視用の変数たち
        self._last_timer_image = None
        self._timer_frozen_since = None
        self._is_frozen = False
    
    def run(self):
        self._running = True
        self._capture.set_target_window(self.config.target_window)
        
        # LiveSplitもチェックするなら準備します
        if self.config.livesplit_window:
            self._livesplit_capture.set_target_window(self.config.livesplit_window)
        
        while self._running:
            try:
                # ゲーム画面をパシャリ
                image = self._capture.capture()
                if image is None:
                    self.error_occurred.emit("おっと、キャプチャに失敗しちゃいました...")
                    self.msleep(1000)
                    continue
                
                # 指定のパターンがあるか探します
                detected, best = detect_all_patterns(
                    image,
                    self.config.patterns,
                    self.config.area_size
                )
                
                self.detection_result.emit((detected, best))
                
                # LiveSplitの方もチラ見します
                if self.config.livesplit_window:
                    self._check_timer_frozen()
                
            except Exception as e:
                self.error_occurred.emit(f"何かエラーが起きちゃいました: {str(e)}")
            
            self.msleep(self.config.check_interval_ms)
    
    def _check_timer_frozen(self):
        """LiveSplitのタイマーが止まってないかチェックします"""
        try:
            ls_image = self._livesplit_capture.capture()
            if ls_image is None:
                return
            
            # タイマーの部分だけ切り抜きます
            ta = self.config.timer_area
            timer_image = crop_timer_area(ls_image, ta.x, ta.y, ta.width, ta.height)
            
            if self._last_timer_image is not None:
                # さっきと比べて変わったかな？
                is_currently_similar = images_are_similar(self._last_timer_image, timer_image)
                
                if is_currently_similar:
                    # 動いてない...
                    if self._timer_frozen_since is None:
                        self._timer_frozen_since = time.time()
                    else:
                        frozen_ms = (time.time() - self._timer_frozen_since) * 1000
                        if frozen_ms >= self.config.timer_freeze_ms:
                            if not self._is_frozen:
                                self._is_frozen = True
                                self.timer_status_changed.emit(True)
                else:
                    # 動いてる！
                    self._timer_frozen_since = None
                    if self._is_frozen:
                        self._is_frozen = False
                        self.timer_status_changed.emit(False)
            
            self._last_timer_image = timer_image
        except Exception as e:
            print(f"タイマー監視中に何か起きちゃいました: {e}")
    
    def stop(self):
        self._running = False
        self.wait()
        self._capture.close()
        self._livesplit_capture.close()
    
    def update_config(self, config: AppConfig):
        self.config = config
        self._capture.set_target_window(config.target_window)
        if config.livesplit_window:
            self._livesplit_capture.set_target_window(config.livesplit_window)


class StatusIndicator(QFrame):
    """ステータスインジケーター"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._status = "stopped"  # stopped, running, detected, error
    
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
        self._hotkey_count = 0  # ホットキー送信回数
        
        self._setup_ui()
        self._setup_tray()
    
    def _setup_ui(self):
        # フォント読み込みとスタイル適用
        font_family = load_fonts()
        
        app = QApplication.instance()
        if app:
            # テンプレートにフォント名を埋め込んで適用
            style_sheet = APP_STYLE_TEMPLATE.format(font_family=font_family)
            app.setStyleSheet(style_sheet)
            
            # アプリ全体のフォントも設定
            font = app.font()
            font.setFamily(font_family)
            # フォントが見つかった場合は少し大きめにするなどの調整が可能
            app.setFont(font)
            
        self.setWindowTitle("AutoSplit GIEEE")
        
        # アイコン設定
        icon_path = os.path.join("assets", "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        self.setMinimumSize(450, 400)
        # 個別のスタイルシートは削除 (グローバルスタイルを使用)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # ヘッダー
        header = QHBoxLayout()
        
        title = QLabel("🎮 AutoSplit GIEEE")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.status_indicator = StatusIndicator()
        header.addWidget(self.status_indicator)
        
        self.status_label = QLabel("停止中")
        self.status_label.setStyleSheet("color: #aaa; font-weight: bold;")
        header.addWidget(self.status_label)
        
        header.addSpacing(10)
        
        self.timer_status_label = QLabel("Timer: -")
        self.timer_status_label.setObjectName("timerStatus")
        self.timer_status_label.setStyleSheet("""
            QLabel#timerStatus {
                color: #777;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #444;
                padding: 4px 8px;
                border-radius: 6px;
                background-color: #222;
            }
        """)
        header.addWidget(self.timer_status_label)
        
        layout.addLayout(header)
        
        # メインコントロールエリア
        control_frame = QFrame()
        control_frame.setObjectName("controlFrame")
        control_layout = QVBoxLayout(control_frame)
        control_layout.setSpacing(15)
        control_layout.setContentsMargins(20, 20, 20, 20)
        
        # 開始/停止ボタン
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ 監視スタート")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._toggle_monitoring)
        btn_layout.addWidget(self.start_btn)
        
        settings_btn = QPushButton("⚙️ 設定")
        settings_btn.setMinimumHeight(50)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)
        btn_layout.addWidget(settings_btn)
        
        control_layout.addLayout(btn_layout)
        layout.addWidget(control_frame)
        
        # 一致率表示エリア
        match_frame = QFrame()
        match_frame.setObjectName("controlFrame")
        # グローバルスタイル使用のためインラインスタイル削除
        match_layout = QVBoxLayout(match_frame)
        
        match_header = QHBoxLayout()
        match_header.addWidget(QLabel("📊 現在の一致率"))
        match_header.addWidget(QLabel("📊 現在の一致率"))
        self.match_pattern_label = QLabel("")
        # スタイル定義済みなので削除
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
        self.tray_icon.setToolTip("AutoSplit GIEEE")
        
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
        
        # ホットキーカウントをリセット
        self._hotkey_count = 0
        
        self._monitor_thread = MonitorThread(self.config)
        self._monitor_thread.detection_result.connect(self._on_detection)
        self._monitor_thread.timer_status_changed.connect(self._on_timer_status_changed)
        self._monitor_thread.error_occurred.connect(self._on_error)
        self._monitor_thread.start()
        
        self.timer_status_label.setText("Timer: Wait...")
        self.timer_status_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold; border: 1px solid #444; padding: 2px 6px; border-radius: 4px;")
        
        self.start_btn.setText("⏹️ ストップ")
        self.start_btn.setObjectName("dangerBtn")
        # スタイルを強制再適用
        self.start_btn.setStyleSheet(self.start_btn.styleSheet())
        
        self.status_indicator.set_status("running")
        self.status_label.setText("監視中")
        self.tray_toggle_action.setText("監視停止")
        self.detection_info.setText("画面を監視しています...")
    
    def _stop_monitoring(self):
        if self._monitor_thread:
            self._monitor_thread.stop()
            self._monitor_thread = None
        
        self.timer_status_label.setText("Timer: -")
        self.timer_status_label.setStyleSheet("color: #555; font-size: 11px; font-weight: bold; border: 1px solid #444; padding: 2px 6px; border-radius: 4px; background-color: #222;")
        
        self.start_btn.setText("▶️ 監視スタート")
        self.start_btn.setObjectName("primaryBtn")
        # スタイルを強制再適用
        self.start_btn.setStyleSheet(self.start_btn.styleSheet())
        
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
            self._hotkey_count += 1  # カウント増加
            self.status_indicator.set_status("detected")
            self.detection_info.setText(
                f"🎯 検知! {detected.pattern.name} → {detected.pattern.hotkey} 送信 (計{self._hotkey_count}回)"
            )
            
            QTimer.singleShot(500, lambda: self.status_indicator.set_status("running"))
        
        # タイマー凍結中かつ規定回数送信済みなら停止 (オートストップ有効時)
        if self.config.auto_stop_enabled and self._monitor_thread and self._monitor_thread._is_frozen:
            if self._hotkey_count >= self.config.min_hotkey_count:
                self._handle_auto_stop()
    
    def _on_timer_status_changed(self, is_frozen: bool):
        """LiveSplitタイマーの状態が変化した"""
        if is_frozen:
            self.timer_status_label.setText("Timer: FROZEN")
            self.timer_status_label.setStyleSheet("color: #f44336; background-color: #3d1c1a; font-size: 11px; font-weight: bold; border: 1px solid #f44336; padding: 2px 6px; border-radius: 4px;")
            
            # オートストップチェック
            if self.config.auto_stop_enabled and self._hotkey_count >= self.config.min_hotkey_count:
                self._handle_auto_stop()
        else:
            self.timer_status_label.setText("Timer: RUNNING")
            self.timer_status_label.setStyleSheet("color: #4CAF50; background-color: #1a2d1b; font-size: 11px; font-weight: bold; border: 1px solid #4CAF50; padding: 2px 6px; border-radius: 4px;")
    
    def _handle_auto_stop(self):
        """オートストップを実行"""
        self.detection_info.setText(
            f"⏹️ タイマー停止検知 - 自動停止 (計{self._hotkey_count}回送信)"
        )
        self._stop_monitoring()
        
        # トレイ通知
        self.tray_icon.showMessage(
            "AutoSplit GIEEE",
            f"タイマー停止を検知し、監視を停止しました。\n(計{self._hotkey_count}回送信)",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )
    
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
            "AutoSplit GIEEE",
            "システムトレイで動作を継続しています",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
