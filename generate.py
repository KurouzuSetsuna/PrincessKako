"""
KakoCal generator: ICSカレンダーとHTMLページを生成する
"""

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

from ics import Calendar, Event

DATA_FILE = Path("kako_schedule.json")
ICS_FILE = Path("kako_schedule.ics")
HTML_FILE = Path("index.html")


def load_data() -> dict[str, list[dict]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"{DATA_FILE} が見つかりません。先に scraper.py を実行してください。")
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate_ics(data: dict[str, list[dict]]) -> None:
    """ICSカレンダーファイルを生成する。"""
    cal = Calendar()
    cal.creator = "KakoCal"

    for month_key, events in sorted(data.items()):
        for ev in events:
            e = Event()
            e.name = ev["content"]
            e.begin = ev["date"]
            e.make_all_day()
            if ev.get("location"):
                e.location = ev["location"]
            e.description = ev["content"]
            cal.events.add(e)

    with ICS_FILE.open("w", encoding="utf-8") as f:
        f.writelines(cal)

    print(f"ICSファイルを生成しました: {ICS_FILE}")


def collect_events_by_month(data: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """データを月別に整理し、各イベントに曜日情報を付与する。"""
    WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
    result = {}
    for month_key in sorted(data.keys()):
        events = data[month_key]
        enriched = []
        for ev in sorted(events, key=lambda e: e["date"]):
            d = date.fromisoformat(ev["date"])
            enriched.append({
                **ev,
                "day": d.day,
                "weekday": WEEKDAYS[d.weekday()],
                "weekday_num": d.weekday(),  # 0=月, 6=日
            })
        result[month_key] = enriched
    return result


def _era_label(year: int, month: int) -> str:
    """西暦年月を「令和X年X月」形式に変換する。"""
    if year >= 2019:
        reiwa = year - 2018
        label = f"令和{reiwa}年" if reiwa > 1 else "令和元年"
    elif year >= 1989:
        heisei = year - 1988
        label = f"平成{heisei}年"
    else:
        label = f"{year}年"
    return f"{label}{month}月"


def generate_html(data: dict[str, list[dict]]) -> None:
    """スタイリッシュなHTMLカレンダーを生成する。"""
    monthly = collect_events_by_month(data)
    updated_at = datetime.now(timezone.utc).strftime("%Y年%m月%d日 %H:%M UTC")

    # 月別セクションのHTML生成
    sections_html = ""
    for month_key, events in monthly.items():
        year_str, month_str = month_key.split("-")
        year, month = int(year_str), int(month_str)
        era = _era_label(year, month)

        rows_html = ""
        for ev in events:
            location_html = (
                f'<span class="location">{ev["location"]}</span>'
                if ev.get("location")
                else ""
            )
            weekday_class = "weekend" if ev["weekday_num"] >= 5 else ""
            rows_html += f"""
        <div class="event-row {weekday_class}">
          <div class="event-date">
            <span class="day">{ev["day"]}</span>
            <span class="weekday">({ev["weekday"]})</span>
          </div>
          <div class="event-content">
            <p class="content-text">{ev["content"]}</p>
            {location_html}
          </div>
        </div>"""

        if not rows_html:
            rows_html = '<p class="no-events">ご日程の記載はありません</p>'

        sections_html += f"""
    <section class="month-section" id="m{month_key.replace('-', '')}">
      <h2 class="month-heading">{era}</h2>
      <div class="events-list">{rows_html}
      </div>
    </section>"""

    # ナビゲーション
    nav_items = ""
    for month_key in monthly.keys():
        year_str, month_str = month_key.split("-")
        year, month = int(year_str), int(month_str)
        era = _era_label(year, month)
        anchor = f"m{month_key.replace('-', '')}"
        nav_items += f'<a href="#{anchor}" class="nav-item">{era}</a>\n'

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>佳子内親王殿下 ご日程 | KakoCal</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --primary: #8b5e83;
      --primary-light: #c9a7c2;
      --primary-dark: #5e3a58;
      --accent: #d4a0c8;
      --bg: #fdf8fc;
      --surface: #ffffff;
      --text: #2d1f2b;
      --text-muted: #7a6577;
      --border: #e8d5e4;
      --weekend-bg: #fef0fa;
      --weekend-color: #9b4d8a;
      --radius: 12px;
      --shadow: 0 2px 16px rgba(139,94,131,0.10);
    }}

    body {{
      font-family: "Hiragino Mincho ProN", "Yu Mincho", Georgia, serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.8;
      font-size: 16px;
    }}

    /* ヘッダー */
    header {{
      background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
      color: #fff;
      padding: 48px 24px 36px;
      text-align: center;
    }}
    header h1 {{
      font-size: clamp(1.4rem, 4vw, 2.2rem);
      font-weight: 400;
      letter-spacing: 0.12em;
      margin-bottom: 8px;
    }}
    header .subtitle {{
      font-size: 0.9rem;
      opacity: 0.8;
      letter-spacing: 0.06em;
    }}
    .updated {{
      font-size: 0.78rem;
      opacity: 0.65;
      margin-top: 12px;
    }}

    /* ダウンロードボタン */
    .download-btn {{
      display: inline-block;
      margin-top: 20px;
      padding: 10px 28px;
      background: rgba(255,255,255,0.18);
      border: 1px solid rgba(255,255,255,0.5);
      color: #fff;
      text-decoration: none;
      border-radius: 50px;
      font-size: 0.88rem;
      letter-spacing: 0.05em;
      transition: background 0.2s;
    }}
    .download-btn:hover {{ background: rgba(255,255,255,0.30); }}

    /* ナビゲーション */
    nav {{
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 12px 16px;
      overflow-x: auto;
      white-space: nowrap;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 2px 8px rgba(139,94,131,0.08);
    }}
    .nav-item {{
      display: inline-block;
      padding: 6px 14px;
      margin: 0 4px;
      color: var(--primary);
      text-decoration: none;
      border-radius: 50px;
      font-size: 0.82rem;
      border: 1px solid var(--primary-light);
      transition: all 0.2s;
    }}
    .nav-item:hover {{
      background: var(--primary);
      color: #fff;
    }}

    /* メインコンテンツ */
    main {{
      max-width: 860px;
      margin: 0 auto;
      padding: 32px 16px 64px;
    }}

    /* 月セクション */
    .month-section {{
      background: var(--surface);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      margin-bottom: 32px;
      overflow: hidden;
    }}
    .month-heading {{
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
      color: #fff;
      padding: 16px 24px;
      font-size: 1.05rem;
      font-weight: 400;
      letter-spacing: 0.1em;
    }}
    .events-list {{
      padding: 8px 0;
    }}

    /* イベント行 */
    .event-row {{
      display: flex;
      align-items: flex-start;
      padding: 14px 24px;
      border-bottom: 1px solid var(--border);
      gap: 20px;
      transition: background 0.15s;
    }}
    .event-row:last-child {{ border-bottom: none; }}
    .event-row:hover {{ background: #fdf4fb; }}
    .event-row.weekend {{ background: var(--weekend-bg); }}
    .event-row.weekend:hover {{ background: #fce8f7; }}

    .event-date {{
      min-width: 64px;
      text-align: center;
      flex-shrink: 0;
    }}
    .event-date .day {{
      display: block;
      font-size: 1.6rem;
      line-height: 1.2;
      color: var(--primary-dark);
    }}
    .event-date .weekday {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}
    .weekend .event-date .weekday {{ color: var(--weekend-color); }}
    .weekend .event-date .day {{ color: var(--weekend-color); }}

    .event-content {{
      flex: 1;
      padding-top: 4px;
    }}
    .content-text {{
      font-size: 0.95rem;
      line-height: 1.7;
      color: var(--text);
    }}
    .location {{
      display: inline-block;
      margin-top: 4px;
      font-size: 0.80rem;
      color: var(--text-muted);
      background: var(--border);
      padding: 2px 10px;
      border-radius: 50px;
    }}
    .no-events {{
      padding: 20px 24px;
      color: var(--text-muted);
      font-size: 0.9rem;
    }}

    /* フッター */
    footer {{
      text-align: center;
      padding: 32px 16px;
      font-size: 0.78rem;
      color: var(--text-muted);
      border-top: 1px solid var(--border);
    }}
    footer a {{ color: var(--primary); }}

    @media (max-width: 480px) {{
      .event-row {{ padding: 12px 16px; gap: 12px; }}
      .event-date .day {{ font-size: 1.3rem; }}
      .month-heading {{ padding: 14px 16px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>佳子内親王殿下 ご日程</h1>
    <p class="subtitle">宮内庁公式サイトより自動収集</p>
    <a href="kako_schedule.ics" class="download-btn" download>
      &#128197; カレンダーに追加 (.ics)
    </a>
    <p class="updated">最終更新: {updated_at}</p>
  </header>

  <nav>
    {nav_items}
  </nav>

  <main>
    {sections_html}
  </main>

  <footer>
    <p>データ出典: <a href="https://www.kunaicho.go.jp/watch/activity/schedule03/index.html" target="_blank" rel="noopener">宮内庁公式サイト</a></p>
    <p style="margin-top:6px">このサイトは非公式のファンサイトです。</p>
  </footer>
</body>
</html>"""

    with HTML_FILE.open("w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTMLファイルを生成しました: {HTML_FILE}")


def generate(ics: bool = True, html: bool = True) -> None:
    data = load_data()
    if ics:
        generate_ics(data)
    if html:
        generate_html(data)


if __name__ == "__main__":
    generate()
