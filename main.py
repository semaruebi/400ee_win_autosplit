"""
AutoSplit GIEEE
========================
ロード画面を検知してLiveSplit向けにホットキーを自動送信する常駐型ツール Genshin Impact Elite Enemies Edition

使い方:
    python main.py

初回起動時は設定画面でパターンを設定してください。
"""
import sys
import ctypes
import os


def is_admin():
    """管理者権限で実行されているかチェック"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """管理者権限で再起動"""
    if sys.platform == 'win32':
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:])
        
        # ShellExecuteW で管理者として実行
        ctypes.windll.shell32.ShellExecuteW(
            None, 
            "runas",  # 管理者として実行
            sys.executable, 
            params, 
            None, 
            1  # SW_SHOWNORMAL
        )
        sys.exit(0)


def main():
    # 管理者権限チェック
    if not is_admin():
        print("管理者権限が必要です。昇格して再起動します...")
        run_as_admin()
        return
    
    print("管理者権限で起動しました")
    
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from gui.main_window import MainWindow
    
    # High DPI対応
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # トレイ常駐のため
    
    # スタイル設定
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
