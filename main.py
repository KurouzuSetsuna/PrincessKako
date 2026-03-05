"""
KakoCal: 佳子内親王殿下ご日程 取得・カレンダー化ツール

使い方:
  python main.py            # 差分更新 + ICS/HTML生成
  python main.py --force    # 全月を再取得してから生成
"""

import sys
from scraper import scrape
from generate import generate


def main() -> None:
    force = "--force" in sys.argv
    print("=== KakoCal: スクレイピング開始 ===")
    data = scrape(force=force)
    total = sum(len(v) for v in data.values())
    print(f"\n合計 {total} 件のイベントを取得しました。")

    print("\n=== KakoCal: ファイル生成 ===")
    generate()
    print("\n完了しました。")
    print("  - kako_schedule.ics (Googleカレンダー等にインポート可)")
    print("  - index.html        (ブラウザで開いてご確認ください)")


if __name__ == "__main__":
    main()
