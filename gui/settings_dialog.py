"""
AutoSplit Screen Detector - 設定ダイアログ
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QGroupBox, QFormLayout, QLineEdit,
    QCheckBox, QTabWidget, QWidget, QScrollArea, QFrame,
    QSlider, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QWheelEvent

from config import AppConfig, PatternConfig, DetectionArea, load_config, save_config, hex_to_rgb, rgb_to_hex
from capture import ScreenCapture
from hotkey import AVAILABLE_HOTKEYS
from gui.color_picker import ColorPickerWidget, ColorPreview
from gui.area_editor import AreaEditorWidget


class NoWheelComboBox(QComboBox):
    """ホイール操作を無効にしたComboBox"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()  # ホイールを無視


class NoWheelSpinBox(QSpinBox):
    """ホイール操作を無効にしたSpinBox"""
    def wheelEvent(self, event: QWheelEvent):
        event.ignore()


class PatternEditor(QFrame):
    """パターン編集ウィジェット"""
    
    pattern_changed = pyqtSignal()
    delete_requested = pyqtSignal()
    
    def __init__(self, pattern: PatternConfig, target_window=None, parent=None):
        super().__init__(parent)
        self.pattern = pattern
        self._target_window = target_window
        self._setup_ui()
    
    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            PatternEditor {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # ヘッダー (名前 + 有効/無効)
        header = QHBoxLayout()
        
        self.enabled_cb = QCheckBox()
        self.enabled_cb.setChecked(self.pattern.enabled)
        self.enabled_cb.stateChanged.connect(self._on_enabled_changed)
        header.addWidget(self.enabled_cb)
        
        self.name_edit = QLineEdit(self.pattern.name)
        self.name_edit.setPlaceholderText("パターン名")
        self.name_edit.textChanged.connect(self._on_name_changed)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
                font-size: 14px;
            }
        """)
        header.addWidget(self.name_edit, 1)
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setFixedSize(32, 32)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #aa3333;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #cc4444;
            }
        """)
        delete_btn.clicked.connect(self.delete_requested.emit)
        header.addWidget(delete_btn)
        
        layout.addLayout(header)
        
        # 色設定
        color_layout = QHBoxLayout()
        
        color_layout.addWidget(QLabel("色:"))
        
        self.color_preview = ColorPreview()
        r, g, b = hex_to_rgb(self.pattern.color)
        self.color_preview.set_color(r, g, b)
        color_layout.addWidget(self.color_preview)
        
        self.color_edit = QLineEdit(self.pattern.color)
        self.color_edit.setFixedWidth(100)
        self.color_edit.textChanged.connect(self._on_color_changed)
        self.color_edit.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
                font-family: monospace;
            }
        """)
        color_layout.addWidget(self.color_edit)
        
        pick_btn = QPushButton("🎨 スポイト")
        pick_btn.clicked.connect(self._open_color_picker)
        pick_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                border: 1px solid #666;
                border-radius: 4px;
                padding: 5px 10px;
                color: white;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        color_layout.addWidget(pick_btn)
        
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # 許容値 (tolerance)
        tolerance_layout = QHBoxLayout()
        tolerance_layout.addWidget(QLabel("色許容値:"))
        self.tolerance_spin = NoWheelSpinBox()
        self.tolerance_spin.setRange(1, 200)
        self.tolerance_spin.setValue(self.pattern.tolerance)
        self.tolerance_spin.valueChanged.connect(self._on_tolerance_changed)
        self.tolerance_spin.setStyleSheet("""
            QSpinBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
        """)
        tolerance_layout.addWidget(self.tolerance_spin)
        tolerance_layout.addStretch()
        layout.addLayout(tolerance_layout)
        
        # 閾値スライダー
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("検知閾値:"))
        
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(self.pattern.threshold_percent)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        self.threshold_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #333;
                height: 8px;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        threshold_layout.addWidget(self.threshold_slider)
        
        self.threshold_label = QLabel(f"{self.pattern.threshold_percent}%")
        self.threshold_label.setFixedWidth(50)
        self.threshold_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        threshold_layout.addWidget(self.threshold_label)
        
        layout.addLayout(threshold_layout)
        
        # ホットキー
        hotkey_layout = QHBoxLayout()
        hotkey_layout.addWidget(QLabel("ホットキー:"))
        self.hotkey_combo = NoWheelComboBox()
        self.hotkey_combo.addItems(AVAILABLE_HOTKEYS)
        if self.pattern.hotkey in AVAILABLE_HOTKEYS:
            self.hotkey_combo.setCurrentText(self.pattern.hotkey)
        self.hotkey_combo.currentTextChanged.connect(self._on_hotkey_changed)
        self.hotkey_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 14px;
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #333;
                color: white;
                selection-background-color: #555;
                selection-color: white;
                font-size: 14px;
                padding: 5px;
            }
        """)
        hotkey_layout.addWidget(self.hotkey_combo)
        hotkey_layout.addStretch()
        layout.addLayout(hotkey_layout)
        
        # エリア編集
        area_group = QGroupBox("検知エリア")
        area_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #555;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ccc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
            }
        """)
        area_layout = QVBoxLayout(area_group)
        
        self.area_editor = AreaEditorWidget()
        self.area_editor.set_areas(self.pattern.areas)
        self.area_editor.set_target_window(self._target_window)
        self.area_editor.areas_changed.connect(self._on_areas_changed)
        area_layout.addWidget(self.area_editor)
        
        layout.addWidget(area_group)
    
    def _on_enabled_changed(self, state):
        self.pattern.enabled = state == Qt.CheckState.Checked.value
        self.pattern_changed.emit()
    
    def _on_name_changed(self, text):
        self.pattern.name = text
        self.pattern_changed.emit()
    
    def _on_color_changed(self, text):
        if len(text) == 7 and text.startswith("#"):
            try:
                r, g, b = hex_to_rgb(text)
                self.color_preview.set_color(r, g, b)
                self.pattern.color = text
                self.pattern_changed.emit()
            except ValueError:
                pass
    
    def _on_tolerance_changed(self, value):
        self.pattern.tolerance = value
        self.pattern_changed.emit()
    
    def _on_threshold_changed(self, value):
        self.pattern.threshold_percent = value
        self.threshold_label.setText(f"{value}%")
        self.pattern_changed.emit()
    
    def _on_hotkey_changed(self, text):
        self.pattern.hotkey = text
        self.pattern_changed.emit()
    
    def _on_areas_changed(self, areas):
        self.pattern.areas = areas
        self.pattern_changed.emit()
    
    def _open_color_picker(self):
        """スポイトダイアログを開く"""
        dialog = QDialog(self)
        dialog.setWindowTitle("色を選択")
        dialog.setMinimumSize(500, 450)
        dialog.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        layout = QVBoxLayout(dialog)
        picker = ColorPickerWidget()
        
        def on_color_selected(hex_color):
            self.color_edit.setText(hex_color)
            dialog.accept()
        
        picker.color_selected.connect(on_color_selected)
        layout.addWidget(picker)
        
        dialog.exec()


class SettingsDialog(QDialog):
    """設定ダイアログ"""
    
    settings_changed = pyqtSignal(AppConfig)
    
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._pattern_editors: list[PatternEditor] = []
        self._setup_ui()
    
    def _setup_ui(self):
        self.setWindowTitle("AutoSplit Screen Detector - 設定")
        self.setMinimumSize(700, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: white;
            }
            QLabel {
                color: #ccc;
            }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                color: #fff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # タブ
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                border: 1px solid #444;
                padding: 8px 16px;
                margin-right: 2px;
                color: white;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3a3a3a;
                border-bottom-color: #3a3a3a;
            }
        """)
        
        # 監視設定タブ (先に設定)
        monitor_tab = self._create_monitor_tab()
        tabs.addTab(monitor_tab, "📺 監視設定")
        
        # パターン設定タブ
        pattern_tab = self._create_pattern_tab()
        tabs.addTab(pattern_tab, "🎯 パターン設定")
        
        layout.addWidget(tabs)
        
        # ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 保存")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _create_pattern_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        scroll_content = QWidget()
        self.patterns_layout = QVBoxLayout(scroll_content)
        
        for pattern in self.config.patterns:
            self._add_pattern_editor(pattern)
        
        self.patterns_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # パターン追加ボタン
        add_btn = QPushButton("➕ パターンを追加")
        add_btn.clicked.connect(self._add_new_pattern)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                border: none;
                padding: 10px;
                border-radius: 6px;
                color: white;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(add_btn)
        
        return widget
    
    def _create_monitor_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # ウィンドウ選択
        window_group = QGroupBox("監視対象")
        window_layout = QFormLayout(window_group)
        
        self.window_combo = NoWheelComboBox()
        self.window_combo.addItem("フルスクリーン (プライマリモニター)", None)
        
        try:
            windows = ScreenCapture.list_windows()
            for win in windows:
                self.window_combo.addItem(win, win)
            
            if self.config.target_window:
                idx = self.window_combo.findData(self.config.target_window)
                if idx >= 0:
                    self.window_combo.setCurrentIndex(idx)
        except Exception as e:
            print(f"ウィンドウ一覧取得エラー: {e}")
        
        self.window_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                min-width: 300px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #333;
                color: white;
                selection-background-color: #555;
                selection-color: white;
                font-size: 14px;
                padding: 5px;
            }
        """)
        window_layout.addRow("ウィンドウ:", self.window_combo)
        
        refresh_btn = QPushButton("🔄 更新")
        refresh_btn.clicked.connect(self._refresh_windows)
        window_layout.addRow("", refresh_btn)
        
        layout.addWidget(window_group)
        
        # タイミング設定
        timing_group = QGroupBox("タイミング設定")
        timing_layout = QFormLayout(timing_group)
        
        self.cooldown_spin = NoWheelSpinBox()
        self.cooldown_spin.setRange(100, 10000)
        self.cooldown_spin.setSingleStep(100)
        self.cooldown_spin.setValue(self.config.cooldown_ms)
        self.cooldown_spin.setSuffix(" ms")
        self.cooldown_spin.setStyleSheet("""
            QSpinBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
        """)
        timing_layout.addRow("クールダウン:", self.cooldown_spin)
        
        self.interval_spin = NoWheelSpinBox()
        self.interval_spin.setRange(16, 1000)
        self.interval_spin.setValue(self.config.check_interval_ms)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setStyleSheet("""
            QSpinBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
        """)
        timing_layout.addRow("監視間隔:", self.interval_spin)
        
        layout.addWidget(timing_group)
        
        # LiveSplit自動停止設定
        livesplit_group = QGroupBox("🕐 LiveSplit自動停止")
        livesplit_layout = QFormLayout(livesplit_group)
        
        self.auto_stop_cb = QCheckBox("タイマー停止で監視を自動停止")
        self.auto_stop_cb.setChecked(self.config.auto_stop_enabled)
        self.auto_stop_cb.setStyleSheet("""
            QCheckBox {
                color: white;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #555;
                background-color: #333;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QCheckBox::indicator:checked::after {
                content: '✓';
            }
        """)
        livesplit_layout.addRow("", self.auto_stop_cb)
        
        self.livesplit_combo = NoWheelComboBox()
        self.livesplit_combo.addItem("選択なし", None)
        try:
            windows = ScreenCapture.list_windows()
            for win in windows:
                self.livesplit_combo.addItem(win, win)
            
            if self.config.livesplit_window:
                idx = self.livesplit_combo.findData(self.config.livesplit_window)
                if idx >= 0:
                    self.livesplit_combo.setCurrentIndex(idx)
        except Exception as e:
            print(f"ウィンドウ一覧取得エラー: {e}")
        
        self.livesplit_combo.setStyleSheet("""
            QComboBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                min-width: 200px;
            }
            QComboBox QAbstractItemView {
                background-color: #333;
                color: white;
                selection-background-color: #555;
            }
        """)
        livesplit_layout.addRow("LiveSplitウィンドウ:", self.livesplit_combo)
        
        # タイマー領域設定 (GUIで選択)
        timer_area_widget = QWidget()
        timer_area_layout = QVBoxLayout(timer_area_widget)
        timer_area_layout.setContentsMargins(0, 0, 0, 0)
        
        ta = self.config.timer_area
        self.timer_area_label = QLabel(
            f"X:{ta.x}% Y:{ta.y}% 幅:{ta.width}% 高:{ta.height}%"
        )
        self.timer_area_label.setStyleSheet("color: #888; font-size: 12px;")
        timer_area_layout.addWidget(self.timer_area_label)
        
        select_timer_btn = QPushButton("📷 タイマー領域を選択...")
        select_timer_btn.clicked.connect(self._select_timer_area)
        select_timer_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                border: none;
                padding: 8px;
                border-radius: 4px;
                color: white;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        timer_area_layout.addWidget(select_timer_btn)
        
        livesplit_layout.addRow("タイマー領域:", timer_area_widget)
        
        self.min_hotkey_spin = NoWheelSpinBox()
        self.min_hotkey_spin.setRange(1, 50)
        self.min_hotkey_spin.setValue(self.config.min_hotkey_count)
        self.min_hotkey_spin.setStyleSheet("""
            QSpinBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
        """)
        livesplit_layout.addRow("最低ホットキー回数:", self.min_hotkey_spin)
        
        layout.addWidget(livesplit_group)
        layout.addStretch()
        
        return widget
    
    def _add_pattern_editor(self, pattern: PatternConfig):
        # 現在選択中のウィンドウを取得
        target_window = self.window_combo.currentData() if hasattr(self, 'window_combo') else self.config.target_window
        editor = PatternEditor(pattern, target_window=target_window)
        editor.delete_requested.connect(lambda: self._remove_pattern(editor))
        self._pattern_editors.append(editor)
        
        count = self.patterns_layout.count()
        self.patterns_layout.insertWidget(count - 1 if count > 0 else 0, editor)
    
    def _add_new_pattern(self):
        pattern = PatternConfig(
            name="新しいパターン",
            color="#808080",
            tolerance=50,
            threshold_percent=80,
            hotkey="numpad1",
            areas=[]
        )
        self.config.patterns.append(pattern)
        self._add_pattern_editor(pattern)
    
    def _remove_pattern(self, editor: PatternEditor):
        if len(self._pattern_editors) <= 1:
            QMessageBox.warning(self, "削除できません", "最低1つのパターンが必要です。")
            return
        
        self.config.patterns.remove(editor.pattern)
        self._pattern_editors.remove(editor)
        editor.deleteLater()
    
    def _refresh_windows(self):
        current = self.window_combo.currentData()
        self.window_combo.clear()
        self.window_combo.addItem("フルスクリーン (プライマリモニター)", None)
        
        try:
            windows = ScreenCapture.list_windows()
            for win in windows:
                self.window_combo.addItem(win, win)
            
            if current:
                idx = self.window_combo.findData(current)
                if idx >= 0:
                    self.window_combo.setCurrentIndex(idx)
        except Exception as e:
            print(f"ウィンドウ一覧取得エラー: {e}")
    
    def _save(self):
        self.config.target_window = self.window_combo.currentData()
        self.config.cooldown_ms = self.cooldown_spin.value()
        self.config.check_interval_ms = self.interval_spin.value()
        
        # LiveSplit設定
        self.config.auto_stop_enabled = self.auto_stop_cb.isChecked()
        self.config.livesplit_window = self.livesplit_combo.currentData()
        # timer_areaはダイアログで直接更新されるのでそのまま
        self.config.min_hotkey_count = self.min_hotkey_spin.value()
        
        save_config(self.config)
        self.settings_changed.emit(self.config)
        self.accept()
    
    def _select_timer_area(self):
        """タイマー領域選択ダイアログを開く"""
        from gui.timer_area_selector import TimerAreaSelector
        
        window_title = self.livesplit_combo.currentData()
        if not window_title:
            QMessageBox.warning(self, "エラー", "先にLiveSplitウィンドウを選択してください。")
            return
        
        dialog = TimerAreaSelector(window_title, self.config.timer_area, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ta = dialog.get_timer_area()
            self.config.timer_area = ta
            self.timer_area_label.setText(
                f"X:{ta.x}% Y:{ta.y}% 幅:{ta.width}% 高:{ta.height}%"
            )

