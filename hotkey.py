"""
AutoSplit GIEEE - ホットキー送信モジュール
"""
from pynput.keyboard import Key, Controller
from typing import Optional
import time


class HotkeyManager:
    """ホットキーの送信を管理するクラス"""

    # キー名とpynputキーのマッピング
    KEY_MAP = {
        # ファンクションキー
        "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
        "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
        "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
        # テンキー
        "numpad0": Key.num_lock if hasattr(Key, 'num_lock') else None,  # フォールバック
        "numpad1": None, "numpad2": None, "numpad3": None,
        "numpad4": None, "numpad5": None, "numpad6": None,
        "numpad7": None, "numpad8": None, "numpad9": None,
        # 特殊キー
        "space": Key.space,
        "enter": Key.enter,
        "tab": Key.tab,
        "escape": Key.esc,
        "esc": Key.esc,
        "backspace": Key.backspace,
        "delete": Key.delete,
        "insert": Key.insert,
        "home": Key.home,
        "end": Key.end,
        "pageup": Key.page_up,
        "pagedown": Key.page_down,
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        # 修飾キー
        "ctrl": Key.ctrl,
        "alt": Key.alt,
        "shift": Key.shift,
    }

    # テンキーの仮想キーコード (VK_NUMPAD0 = 0x60)
    NUMPAD_VK = {
        "numpad0": 0x60, "numpad1": 0x61, "numpad2": 0x62, "numpad3": 0x63,
        "numpad4": 0x64, "numpad5": 0x65, "numpad6": 0x66,
        "numpad7": 0x67, "numpad8": 0x68, "numpad9": 0x69,
    }

    def __init__(self):
        self.keyboard = Controller()
        self._last_send_time: dict[str, float] = {}

    def parse_hotkey(self, hotkey_str: str) -> list:
        """
        ホットキー文字列をパース
        
        Args:
            hotkey_str: "ctrl+shift+f5" 形式
        
        Returns:
            キーのリスト
        """
        parts = hotkey_str.lower().replace(" ", "").split("+")
        keys = []
        
        for part in parts:
            if part in self.KEY_MAP and self.KEY_MAP[part] is not None:
                keys.append(self.KEY_MAP[part])
            elif part in self.NUMPAD_VK:
                # テンキーは仮想キーコードで処理
                keys.append(("vk", self.NUMPAD_VK[part]))
            elif len(part) == 1:
                # 単一文字キー
                keys.append(part)
            else:
                print(f"未知のキー: {part}")
        
        return keys

    def send_hotkey(self, hotkey_str: str, cooldown_ms: int = 0) -> bool:
        """
        ホットキーを送信
        
        Args:
            hotkey_str: ホットキー文字列
            cooldown_ms: クールダウン時間 (ミリ秒)
        
        Returns:
            送信成功したか (クールダウン中はFalse)
        """
        # クールダウンチェック
        now = time.time()
        if hotkey_str in self._last_send_time:
            elapsed_ms = (now - self._last_send_time[hotkey_str]) * 1000
            if elapsed_ms < cooldown_ms:
                return False
        
        keys = self.parse_hotkey(hotkey_str)
        if not keys:
            return False
        
        try:
            self._send_keys(keys)
            self._last_send_time[hotkey_str] = now
            return True
        except Exception as e:
            print(f"ホットキー送信エラー: {e}")
            return False

    def _send_keys(self, keys: list):
        """キーを送信 (内部用)"""
        import ctypes
        
        # 修飾キーを押す
        modifiers = []
        regular_keys = []
        
        for key in keys:
            if isinstance(key, Key) and key in (Key.ctrl, Key.alt, Key.shift):
                modifiers.append(key)
            else:
                regular_keys.append(key)
        
        # 修飾キーを押す
        for mod in modifiers:
            self.keyboard.press(mod)
        
        # 通常キーを押す
        for key in regular_keys:
            if isinstance(key, tuple) and key[0] == "vk":
                # 仮想キーコードを使用
                self._send_vk(key[1])
            elif isinstance(key, Key):
                self.keyboard.press(key)
                self.keyboard.release(key)
            else:
                self.keyboard.press(key)
                self.keyboard.release(key)
        
        # 修飾キーを離す (逆順)
        for mod in reversed(modifiers):
            self.keyboard.release(mod)

    def _send_vk(self, vk_code: int):
        """仮想キーコードでキーを送信"""
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        
        # INPUT構造体
        KEYEVENTF_KEYUP = 0x0002
        INPUT_KEYBOARD = 1
        
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
            ]
        
        class INPUT(ctypes.Structure):
            class _INPUT(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]
            _anonymous_ = ("_input",)
            _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]
        
        # キーダウン
        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.ki.wVk = vk_code
        inp_down.ki.dwFlags = 0
        
        # キーアップ
        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.ki.wVk = vk_code
        inp_up.ki.dwFlags = KEYEVENTF_KEYUP
        
        user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(INPUT))
        time.sleep(0.01)
        user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(INPUT))


# 使用可能なホットキーの一覧
AVAILABLE_HOTKEYS = [
    # 数字・テンキー
    "numpad0", "numpad1", "numpad2", "numpad3", "numpad4",
    "numpad5", "numpad6", "numpad7", "numpad8", "numpad9",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    
    # ファンクションキー
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "f13", "f14", "f15", "f16", "f17", "f18", "f19", "f20", "f21", "f22", "f23", "f24",
    
    # 特殊キー
    "space", "enter", "tab", "backspace", "delete", "insert",
    "home", "end", "pageup", "pagedown", "escape",
    
    # 矢印キー
    "up", "down", "left", "right",
    
    # アルファベット
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
    
    # 記号 (一部)
    "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/",
]
