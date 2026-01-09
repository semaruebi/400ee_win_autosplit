"""
AutoSplit GIEEE - 設定管理モジュール
"""
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

CONFIG_FILE = Path(__file__).parent / "config.json"


@dataclass
class DetectionArea:
    """検知エリア (50x50px)"""
    x: int  # 左上X座標 (0-100%で保存)
    y: int  # 左上Y座標 (0-100%で保存)


@dataclass
class PatternConfig:
    """検知パターンの設定"""
    name: str
    color: str  # "#RRGGBB" 形式
    tolerance: int = 50  # 色距離の許容値
    threshold_percent: int = 80  # 一致判定閾値 (%)
    hotkey: str = "numpad1"
    enabled: bool = True
    areas: list[DetectionArea] = field(default_factory=list)  # 検知エリアリスト

    def __post_init__(self):
        # dictからDetectionAreaに変換
        if self.areas and isinstance(self.areas[0], dict):
            self.areas = [DetectionArea(**a) for a in self.areas]


@dataclass
class TimerArea:
    """タイマー監視エリア"""
    x: int = 0  # 0-100%
    y: int = 0
    width: int = 20
    height: int = 10


@dataclass
class AppConfig:
    """アプリケーション設定"""
    patterns: list[PatternConfig] = field(default_factory=list)
    target_window: Optional[str] = None  # None = フルスクリーン
    cooldown_ms: int = 2000  # 連続発火防止 (ミリ秒)
    check_interval_ms: int = 50  # 監視間隔 (約20fps)
    area_size: int = 50  # エリアサイズ (px)
    
    # LiveSplit監視設定
    livesplit_window: Optional[str] = None
    timer_area: TimerArea = field(default_factory=TimerArea)
    timer_freeze_ms: int = 1000  # タイマー停止判定時間 (ms)
    auto_stop_enabled: bool = False  # 自動停止機能を有効化
    min_hotkey_count: int = 3  # 自動停止前の最低ホットキー送信回数

    def __post_init__(self):
        # dictからPatternConfigに変換
        if self.patterns and isinstance(self.patterns[0], dict):
            self.patterns = [PatternConfig(**p) for p in self.patterns]
        # dictからTimerAreaに変換
        if isinstance(self.timer_area, dict):
            self.timer_area = TimerArea(**self.timer_area)


def get_default_config() -> AppConfig:
    """デフォルト設定を取得"""
    return AppConfig(
        patterns=[
            PatternConfig(
                name="ﾛｰﾄﾞ画面(夜)",
                color="#1C1C22",
                tolerance=10,
                threshold_percent=100,
                hotkey="f11",
                areas=[]
            ),
            PatternConfig(
                name="ﾛｰﾄﾞ画面(昼)",
                color="#FFFFFF",
                tolerance=10,
                threshold_percent=100,
                hotkey="f11",
                areas=[]
            )
        ],
        target_window="原神",
        cooldown_ms=3000,
        check_interval_ms=50,
        area_size=50
    )


def load_config() -> AppConfig:
    """設定ファイルから読み込み、なければデフォルトを返す"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AppConfig(**data)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"設定ファイルの読み込みエラー: {e}")
    return get_default_config()


def save_config(config: AppConfig) -> None:
    """設定をファイルに保存"""
    data = asdict(config)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB形式からRGBタプルに変換"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """RGBタプルから#RRGGBB形式に変換"""
    return f"#{r:02X}{g:02X}{b:02X}"
