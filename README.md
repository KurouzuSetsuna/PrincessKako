# PrincessKako

宮内庁公式サイトの「秋篠宮家のご日程（佳子内親王殿下）」ページから、月ごとのご公務スケジュールを自動抽出し、HTMLカレンダーおよびiCalendar (.ics) ファイルを生成するツールです。

## 生成されるファイル

| ファイル | 内容 |
|---|---|
| `index.html` | スマホ対応のスタイリッシュなカレンダーページ |
| `kako_schedule.ics` | Googleカレンダー等にインポートできるiCalendarファイル |
| `kako_schedule.json` | スクレイピング結果のキャッシュ（差分更新に使用） |

## セットアップ

Python 3.10以上が必要です。

```bash
pip install -r requirements.txt
```

## 使い方

```bash
# 差分更新（取得済みの月はスキップ）
python main.py

# 全月を再取得して生成
python main.py --force
```

## GitHub Actions による自動更新

`.github/workflows/schedule.yml` により、以下のタイミングで自動実行されます。

| 実行時刻 | JST |
|---|---|
| 毎日 | AM 5:00 |
| 毎日 | 13:00 |

実行後、生成ファイル (`index.html`, `kako_schedule.ics`, `kako_schedule.json`) は自動でリポジトリにコミットされます。

GitHubの **Actions タブ → KakoCal - スケジュール自動更新 → Run workflow** から手動実行も可能です。

## プロジェクト構成

```
.
├── main.py          # エントリーポイント
├── scraper.py       # スクレイピング・和暦変換・JSON保存
├── generate.py      # ICS・HTML生成
├── requirements.txt
└── .github/
    └── workflows/
        └── schedule.yml
```

## データソース

[宮内庁公式サイト - 秋篠宮家のご日程（佳子内親王殿下）](https://www.kunaicho.go.jp/watch/activity/schedule03/index.html)

---

このツールは非公式のファンプロジェクトです。
