"""
AutoSplit GIEEE - 画面キャプチャモジュール
"""
from PIL import Image, ImageGrab
from typing import Optional
import win32gui
import win32ui
import win32con
import ctypes


class ScreenCapture:
    """画面キャプチャを行うクラス"""

    def __init__(self):
        self._target_window: Optional[str] = None
        self._window_handle: Optional[int] = None

    def set_target_window(self, window_title: Optional[str]) -> bool:
        """監視対象ウィンドウを設定"""
        self._target_window = window_title
        if window_title is None:
            self._window_handle = None
            return True

        self._window_handle = win32gui.FindWindow(None, window_title)
        return self._window_handle != 0

    def capture(self) -> Optional[Image.Image]:
        """画面をキャプチャしてPIL Imageを返す"""
        try:
            if self._window_handle is None:
                return ImageGrab.grab()
            else:
                return self._capture_window_bitblt(self._window_handle)
        except Exception as e:
            print(f"キャプチャエラー: {e}")
            return None

    def _capture_window_bitblt(self, hwnd: int) -> Optional[Image.Image]:
        """BitBltを使用してウィンドウをキャプチャ"""
        try:
            # ウィンドウの位置とサイズを取得
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            if width <= 0 or height <= 0:
                return None

            # デバイスコンテキスト取得
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            # ビットマップ作成
            save_bitmap = win32ui.CreateBitmap()
            save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(save_bitmap)
            
            # PrintWindow を ctypes経由で呼び出し (DirectXウィンドウ対応)
            # PW_RENDERFULLCONTENT = 2
            user32 = ctypes.windll.user32
            result = user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
            
            if result == 0:
                # PrintWindowが失敗した場合はBitBltを試す
                save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)
            
            # ビットマップからPIL Imageに変換
            bmp_info = save_bitmap.GetInfo()
            bmp_str = save_bitmap.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmp_info['bmWidth'], bmp_info['bmHeight']),
                bmp_str, 'raw', 'BGRX', 0, 1
            )
            
            # リソース解放
            win32gui.DeleteObject(save_bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwnd_dc)
            
            return img
            
        except Exception as e:
            print(f"BitBltキャプチャエラー: {e}")
            # フォールバック
            try:
                rect = win32gui.GetWindowRect(hwnd)
                return ImageGrab.grab(bbox=rect)
            except:
                return None

    @staticmethod
    def list_windows() -> list[str]:
        """キャプチャ可能なウィンドウ一覧を取得"""
        windows = []

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title and len(title) > 0:
                    if not win32gui.IsIconic(hwnd):
                        windows.append(title)
            return True

        win32gui.EnumWindows(enum_callback, None)
        return sorted(set(windows))

    def close(self):
        pass
