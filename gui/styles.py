"""
AutoSplit GIEEE - アプリケーションスタイル定義
"""
import os
from PyQt6.QtGui import QFontDatabase, QFont

def load_fonts():
    """カスタムフォントをロードし、フォントファミリー名を返す"""
    # フォントファイルのパス
    font_path = os.path.join("d:\\work\\timeline\\assets\\fonts\\ja-jp.ttf")
    
    font_family = "Segoe UI" # デフォルト
    
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                font_family = families[0]
                print(f"Custom font loaded: {font_family}")
            else:
                print("No font families found in loaded font.")
        else:
            print(f"Failed to load font from {font_path}")
    else:
        print(f"Font file not found: {font_path}")
        
    return font_family

# Double curly braces {{ }} are used to escape them so .format() ignores them
# The {font_family} placeholder is left with single braces
APP_STYLE_TEMPLATE = """
/* =======================================================
   Base Style - Modern & Trendy
   Palette: Deep Purple Theme with soft gradients
   ======================================================= */

QMainWindow, QDialog {{
    background-color: #1a1625;
    color: #ffffff;
    font-family: "{font_family}", "Meiryo", sans-serif;
    font-size: 14px;
}}

QWidget {{
    color: #f0f0f0;
    outline: none;
}}

/* =======================================================
   Containers (Glass-like cards)
   ======================================================= */

QFrame, QGroupBox, QScrollArea {{
    background-color: transparent;
    border: none;
}}

/* Card Container */
QFrame#controlFrame, QFrame#PatternEditor, QGroupBox {{
    background-color: #2b2438;
    border-radius: 16px;
    border: 1px solid #3d3450;
}}

/* GroupBox Header */
QGroupBox {{
    margin-top: 28px;
    padding-top: 24px;
    font-weight: bold;
    font-size: 13px;
    color: #d8b4fe;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    left: 12px;
    background-color: #3d3450;
    border-radius: 8px;
    color: #ffffff;
}}

/* =======================================================
   Typography
   ======================================================= */

QLabel {{
    color: #e0e0e0;
}}
QLabel#headerTitle {{
    color: #ffffff;
    font-size: 22px;
    font-weight: 800;
    margin-bottom: 4px;
}}
QLabel#subTitle {{
    color: #a364ff;
    font-size: 13px;
}}

/* =======================================================
   Buttons (Pill-shaped, Gradient)
   ======================================================= */

QPushButton {{
    background-color: #3d3450;
    color: #ffffff;
    border: 1px solid #554a6b;
    border-radius: 12px;
    padding: 10px 24px; /* Updated padding */
    min-height: 24px;   /* Updated min-height */
    font-weight: 600;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #4e4363;
    border-color: #6a5d85;
}}
QPushButton:pressed {{
    background-color: #2d263b;
    margin-top: 2px;
}}

/* Primary Action - "Holo/Neon" Gradient */
QPushButton#primaryBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6c35de, stop:1 #a364ff);
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    border: none;
    min-width: 100px;
}}
QPushButton#primaryBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7d4be1, stop:1 #b07aff);
}}
QPushButton#primaryBtn:pressed {{
    background-color: #582bb8;
}}

/* Danger Button (Red Gradient) */
QPushButton#dangerBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff5252, stop:1 #e53935);
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    border: none;
    min-width: 100px;
}}
QPushButton#dangerBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff6e6e, stop:1 #f44336);
}}
QPushButton#dangerBtn:pressed {{
    background-color: #c62828;
}}

/* Success Button (Green Gradient) */
QPushButton#successBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2ecc71, stop:1 #27ae60);
    color: #ffffff;
    font-size: 15px;
    font-weight: bold;
    border: none;
    min-width: 100px;
}}
QPushButton#successBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #40d47e, stop:1 #2cc96d);
}}
QPushButton#successBtn:pressed {{
    background-color: #219150;
}}

/* =======================================================
   Checkboxes (Toggle Switch Style)
   ======================================================= */

QCheckBox {{
    spacing: 12px;
    font-size: 14px;
    color: #ffffff;
    padding: 4px;
}}
QCheckBox::indicator {{
    width: 44px;
    height: 24px;
    border-radius: 12px;
    background-color: #3d3450;
    border: 2px solid #554a6b;
}}
QCheckBox::indicator:hover {{
    border-color: #a364ff;
    background-color: #4e4363;
}}
QCheckBox::indicator:checked {{
    background-color: #6c35de;
    border-color: #a364ff;
    border-image: none;
}}

/* =======================================================
   Inputs (Modern Flat)
   ======================================================= */

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: #231e2e;
    border: 2px solid transparent;
    border-radius: 10px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 14px;
    selection-background-color: #6c35de;
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    background-color: #231e2e;
    border: 2px solid #6c35de;
}}

/* ComboBox Dropdown */
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: #342a45;
    border: 1px solid #4d425f;
    border-radius: 8px;
    selection-background-color: #6c35de;
    padding: 4px;
}}

/* =======================================================
   Tabs (Capsule Style)
   ======================================================= */

QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabWidget::tab-bar {{
    alignment: center;
}}
QTabBar::tab {{
    background: transparent;
    color: #999;
    padding: 10px 24px;
    margin: 4px;
    border-radius: 20px;
    border: 1px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    background-color: #3d3450;
    color: #a364ff;
    border: 1px solid #6c35de;
}}
QTabBar::tab:hover:!selected {{
    color: #fff;
    background-color: #2b2438;
}}

/* =======================================================
   Scrollbars
   ======================================================= */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #554a6b;
    border-radius: 3px;
    min-height: 20px;
}}

/* =======================================================
   Sliders
   ======================================================= */

QSlider::groove:horizontal {{
    border: 1px solid #3d3450;
    height: 8px;
    background: #2b2438;
    margin: 2px 0;
    border-radius: 4px;
}}
QSlider::handle:horizontal {{
    background: #6c35de;
    border: 1px solid #6c35de;
    width: 18px;
    height: 18px;
    margin: -7px 0;
    border-radius: 9px;
}}
"""
