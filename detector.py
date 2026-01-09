"""
AutoSplit GIEEE - 色検知ロジック (エリア方式)
"""
import math
from PIL import Image
from typing import Optional
from dataclasses import dataclass

from config import PatternConfig, DetectionArea, hex_to_rgb


@dataclass
class DetectionResult:
    """検知結果"""
    detected: bool
    pattern: Optional[PatternConfig]
    match_percent: float  # 一致率 (0-100)
    matched_areas: int
    total_areas: int


def calculate_color_distance(color1: tuple[int, int, int], color2: tuple[int, int, int]) -> float:
    """
    RGB空間でのユークリッド距離を計算
    
    Returns:
        色距離 (0 ~ 441.67...)
    """
    return math.sqrt(
        (color1[0] - color2[0]) ** 2 +
        (color1[1] - color2[1]) ** 2 +
        (color1[2] - color2[2]) ** 2
    )


def get_area_average_color(image: Image.Image, x_percent: int, y_percent: int, 
                            area_size: int = 50) -> tuple[int, int, int]:
    """
    エリアの平均色を取得
    
    Args:
        image: PIL Image
        x_percent, y_percent: エリアの位置 (0-100%)
        area_size: エリアサイズ (px)
    
    Returns:
        (R, G, B)
    """
    # パーセントから実座標に変換
    img_w, img_h = image.size
    x = int((x_percent / 100) * img_w)
    y = int((y_percent / 100) * img_h)
    
    # エリアが画像範囲内に収まるようにクリップ
    x = max(0, min(x, img_w - area_size))
    y = max(0, min(y, img_h - area_size))
    
    # 高速化: クロップして縮小することで平均色を取得
    # Image.Resampling.BOX は平均画素法に近い処理を行うため平均色取得に適している
    crop = image.crop((x, y, x + area_size, y + area_size))
    pixel = crop.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    return pixel


def detect_pattern(image: Image.Image, pattern: PatternConfig, 
                   area_size: int = 50) -> DetectionResult:
    """
    パターンの検知を行う (エリア方式)
    
    Args:
        image: キャプチャ画像
        pattern: 検知パターン設定
        area_size: エリアサイズ (px)
    
    Returns:
        DetectionResult
    """
    if not pattern.enabled or not pattern.areas:
        return DetectionResult(
            detected=False,
            pattern=pattern,
            match_percent=0.0,
            matched_areas=0,
            total_areas=len(pattern.areas) if pattern.areas else 0
        )
    
    target_color = hex_to_rgb(pattern.color)
    matched = 0
    
    for area in pattern.areas:
        area_color = get_area_average_color(image, area.x, area.y, area_size)
        distance = calculate_color_distance(area_color, target_color)
        if distance <= pattern.tolerance:
            matched += 1
    
    total = len(pattern.areas)
    match_percent = (matched / total * 100) if total > 0 else 0.0
    detected = match_percent >= pattern.threshold_percent
    
    return DetectionResult(
        detected=detected,
        pattern=pattern,
        match_percent=match_percent,
        matched_areas=matched,
        total_areas=total
    )


def detect_all_patterns(image: Image.Image, 
                        patterns: list[PatternConfig],
                        area_size: int = 50) -> tuple[Optional[DetectionResult], Optional[DetectionResult]]:
    """
    全パターンを検査し、結果を返す
    
    Returns:
        (検知パターン or None, ベストマッチ結果)
    """
    best_result = None
    detected_result = None
    
    for pattern in patterns:
        result = detect_pattern(image, pattern, area_size)
        
        # ベストマッチを更新 (一致率が高いもの)
        if best_result is None or result.match_percent > best_result.match_percent:
            best_result = result
        
        # 検知されたらそれを記録
        if result.detected and detected_result is None:
            detected_result = result
    
    return (detected_result, best_result)


def extract_dominant_color(image: Image.Image) -> tuple[int, int, int]:
    """
    画像から支配的な色を抽出（スポイト機能用）
    """
    small = image.resize((100, 100), Image.Resampling.BILINEAR)
    quantized = small.quantize(colors=10, method=Image.Quantize.FASTOCTREE)
    palette = quantized.getpalette()
    
    colors = quantized.getcolors()
    if colors:
        most_common = max(colors, key=lambda x: x[0])
        idx = most_common[1] * 3
        return (palette[idx], palette[idx + 1], palette[idx + 2])
    
    return (128, 128, 128)


def crop_timer_area(image: Image.Image, x_percent: int, y_percent: int,
                    width_percent: int, height_percent: int) -> Image.Image:
    """
    タイマー領域をクロップ
    
    Args:
        image: 元画像
        x_percent, y_percent: 左上座標 (0-100%)
        width_percent, height_percent: サイズ (0-100%)
    
    Returns:
        クロップした画像
    """
    img_w, img_h = image.size
    
    x = int(x_percent / 100 * img_w)
    y = int(y_percent / 100 * img_h)
    w = int(width_percent / 100 * img_w)
    h = int(height_percent / 100 * img_h)
    
    # 範囲チェック
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = max(1, min(w, img_w - x))
    h = max(1, min(h, img_h - y))
    
    return image.crop((x, y, x + w, y + h))


def images_are_similar(img1: Image.Image, img2: Image.Image, threshold: float = 0.99) -> bool:
    """
    2つの画像が類似しているかチェック
    
    Args:
        img1, img2: 比較する画像
        threshold: 類似度閾値 (0-1、1=完全一致)
    
    Returns:
        類似していればTrue
    """
    if img1.size != img2.size:
        return False
    
    # 小さくリサイズして比較（高速化）
    size = (50, 20)
    img1_small = img1.resize(size, Image.Resampling.NEAREST)
    img2_small = img2.resize(size, Image.Resampling.NEAREST)
    
    # ピクセル比較
    pixels1 = list(img1_small.getdata())
    pixels2 = list(img2_small.getdata())
    
    if len(pixels1) != len(pixels2):
        return False
    
    matching = 0
    total = len(pixels1)
    
    for p1, p2 in zip(pixels1, pixels2):
        # RGB距離
        dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
        if dist < 30:  # 許容誤差
            matching += 1
    
    similarity = matching / total
    return similarity >= threshold

