
import sys
import os
# 親ディレクトリをパスに追加
sys.path.append(os.path.abspath("d:/work/timeline"))

from capture import check_window_exists

def test_check_window():
    print("check_window_exists をテスト中...")
    
    # テスト 1: None (フルスクリーン) -> True になるべき
    assert check_window_exists(None) == True
    print("テスト 1 合格: None (フルスクリーン) は True を返しました")
    
    # テスト 2: 空文字列 -> True になるべき (現在のロジックではフルスクリーン扱い)
    assert check_window_exists("") == True
    print("テスト 2 合格: 空文字列は True を返しました")
    
    # テスト 3: 存在しないウィンドウ -> False になるべき
    fake_window = "ThisWindowDefinitelyDoesNotExist_123456789"
    exists = check_window_exists(fake_window)
    assert exists == False
    print(f"テスト 3 合格: '{fake_window}' は False を返しました")
    
    # テスト 4: 既存のウィンドウ (可能であればテストするが、制御可能なウィンドウが不明なためスキップ)

if __name__ == "__main__":
    test_check_window()
