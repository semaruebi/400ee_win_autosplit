"""
Todays Split Logger
========================
その日の区間タイムとロード時間を記録するモジュール
"""
import time
import datetime
import os
import csv

class TodaysSplitLogger:
    """
    その日の区間タイムとロード時間をペアにして記録するクラス
    """
    def __init__(self, output_dir=None):
        # ファイル名は日時で作る (例: 20260118_102030_GIEEE_split.csv)
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{date_str}_GIEEE_split.csv"
        
        # 出力先ディレクトリの指定があれば結合
        if output_dir:
            # ディレクトリがなければ作る
            try:
                os.makedirs(output_dir, exist_ok=True)
                self.filename = os.path.join(output_dir, filename)
            except Exception as e:
                print(f"ディレクトリ作成エラー: {e}")
                self.filename = filename # 失敗したらカレントに
        else:
            self.filename = filename
        
        # 状態管理用の変数
        self.last_split_time = None       # 前回のSplit時刻
        self.current_segment_load_time = 0.0 # 今の区間のロード時間合計
        
        # ファイルの準備（ヘッダーがあったほうがExcelで見たとき分かりやすい）
        try:
            with open(self.filename, "w", encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Segment_Time", "Load_Time"])
            print(f"今日のカルテを用意しました: {self.filename}")
        except Exception as e:
            print(f"初期化エラー: {e}")

    def start_timer(self):
        """
        RTA開始時（最初のStart）に呼ぶ
        """
        self.last_split_time = time.time()
        self.current_segment_load_time = 0.0
        print(">>> 計測開始！ (Logger)")

    def add_load_time(self, duration):
        """
        ロードが終わるたびに呼んで、時間を積み立てる
        duration: その1回のロードにかかった秒数
        """
        if self.last_split_time is not None:
            self.current_segment_load_time += duration
            # print(f"ロード時間を積み立て: +{duration:.3f}s (合計: {self.current_segment_load_time:.3f}s)")

    def record_split(self, split_time=None) -> tuple[float, float]:
        """
        Split（ホットキー送信）のタイミングで呼ぶ
        
        Args:
            split_time: Splitした時刻 (Unix Timestamp). Noneの場合は現在時刻を使う
                        誤検知フィルターで遅延した分を補正するために指定する
        
        1. 前回のSplitからの経過時間（区間タイム）を計算
        2. 積み立てたロード時間と一緒に書き込み
        3. 次の区間のためにリセット
        
        Returns:
            (segment_time, load_time) のタプル。計測開始前なら(0, 0)
        """
        if self.last_split_time is None:
            print("まだタイマーが始まっていません。start_timer() を呼んでください")
            return 0.0, 0.0

        now = split_time if split_time is not None else time.time()
        
        # 区間タイム = 現在時刻 - 前回時刻
        segment_time = now - self.last_split_time
        load_time = self.current_segment_load_time
        
        # ファイルに書き込む
        self._save_to_file(segment_time, load_time)
        
        # --- 次の区間の準備 ---
        self.last_split_time = now
        self.current_segment_load_time = 0.0  # ロード時間はリセット
        
        return segment_time, load_time

    def _save_to_file(self, segment, load):
        try:
            with open(self.filename, "a", encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([f"{segment:.3f}", f"{load:.3f}"])
            
            print(f"記録保存: 区間 {segment:.3f}秒 / ロード {load:.3f}秒")
        except Exception as e:
            print(f"書き込みエラー: {e}")

# --- 使い方（シミュレーション） ---
if __name__ == "__main__":
    logger = TodaysSplitLogger()

    # 1. ゲーム開始（タイマースタート）
    logger.start_timer()
    
    # ... ゲーム中 ...
    time.sleep(1)
    
    # 2. ロードが発生したとする（1回目）
    logger.add_load_time(1.500) 
    
    time.sleep(2)
    
    # 3. またロードが発生したとする（2回目）
    logger.add_load_time(0.500)
    
    # 4. ここでSplit発生！ (ホットキー検知)
    logger.record_split()

    print("--- CSVファイルを確認してください ---")
