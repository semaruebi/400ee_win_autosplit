"""
AutoSplit Screen Detector - 色検知ロジック (エリア方式)
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
    
    # エリア内のピクセルを集計
    r_sum, g_sum, b_sum = 0, 0, 0
    count = 0
    
    # サンプリング (パフォーマンスのため5px間隔)
    for dx in range(0, area_size, 5):
        for dy in range(0, area_size, 5):
            px = x + dx
            py = y + dy
            if 0 <= px < img_w and 0 <= py < img_h:
                pixel = image.getpixel((px, py))
                r_sum += pixel[0]
                g_sum += pixel[1]
                b_sum += pixel[2]
                count += 1
    
    if count == 0:
        return (0, 0, 0)
    
    return (r_sum // count, g_sum // count, b_sum // count)


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
    small = image.resize((100, 100), Image.Resampling.LANCZOS)
    quantized = small.quantize(colors=10, method=Image.Quantize.FASTOCTREE)
    palette = quantized.getpalette()
    
    colors = quantized.getcolors()
    if colors:
        most_common = max(colors, key=lambda x: x[0])
        idx = most_common[1] * 3
        return (palette[idx], palette[idx + 1], palette[idx + 2])
    
    return (128, 128, 128)
