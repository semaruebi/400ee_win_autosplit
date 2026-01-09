# AutoSplit Screen Detector

ゲームのロード画面を検知してLiveSplit向けにホットキーを自動送信する常駐型ツール

## 機能

- 🎯 カスタムエリア配置による色検知
- ⌨️ 検知時にホットキー自動送信  
- 🖥️ 特定ウィンドウ or フルスクリーン監視
- 📊 リアルタイム一致率表示
- 🔧 システムトレイ常駐

## 使い方

1. `python main.py` で起動（管理者権限で自動昇格）
2. ⚙️設定 → 監視対象ウィンドウを選択
3. パターン設定 → 📷画面キャプチャ → エリア配置
4. 保存して監視開始！

## 必要なもの

```
pip install -r requirements.txt
```

## ファイル構成

```
timeline/
├── main.py          # エントリーポイント
├── config.py        # 設定管理
├── capture.py       # 画面キャプチャ
├── detector.py      # 色検知ロジック
├── hotkey.py        # ホットキー送信
├── gui/
│   ├── main_window.py      # メインウィンドウ
│   ├── settings_dialog.py  # 設定ダイアログ
│   ├── area_editor.py      # エリア編集UI
│   └── color_picker.py     # カラーピッカー
└── config.json      # ユーザー設定（自動生成）
```
