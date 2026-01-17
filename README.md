# AutoSplit GIEEE v1.2.0

ロード画面を検知してLiveSplit向けにホットキーを自動送信する常駐型ツール Genshin Impact Elite Enemies Edition

## 機能

- 🎯 カスタムエリア配置による色検知
- ⌨️ 検知時にホットキー自動送信 (拡張キー対応)
- 📝 **[NEW] 今日の記録 (CSVログ出力)**: 区間タイムとロード時間を自動記録
- 🛡️ **[NEW] 誤検知フィルター**: アニメーション等による一瞬の誤反応を防止
- 🖥️ 特定ウィンドウ or フルスクリーン監視
- 📊 リアルタイム一致率表示
- 🎨 原神の公式フォントを使ってみた

## 使い方

📖 **詳しい使い方は [MANUAL.md](MANUAL.md) をご覧ください！**

1. `python main.py` で起動（管理者権限で自動昇格）
2. ⚙️設定 → 監視対象ウィンドウを選択 (LiveSplitも指定可能)
3. パターン設定 → 「＋パターンを追加」 → ホットキーや検知色を設定
4. 「検知エリア」で画面上の監視したい場所をドラッグして指定
5. 保存して監視開始！ (緑のスタートボタンをクリック)

※ アプリを閉じると終了します。

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

[![Downloads](https://img.shields.io/github/downloads/semaruebi/400ee_win_autosplit/total)](https://github.com/semaruebi/400ee_win_autosplit/releases)
