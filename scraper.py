"""
KakoCal scraper: 宮内庁サイトから佳子内親王殿下のご日程を取得する
"""

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.kunaicho.go.jp"
SCHEDULE_INDEX = f"{BASE_URL}/watch/activity/schedule03/index.html"
DATA_FILE = Path("kako_schedule.json")

# 和暦→西暦変換テーブル
ERA_TABLE = {
    "令和": 2018,
    "平成": 1988,
    "昭和": 1925,
}

WEEKDAY_MAP = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}


def era_to_year(era: str, year_num: int) -> int:
    """和暦の元号と年数から西暦年を返す。元年=1。"""
    return ERA_TABLE[era] + year_num


def parse_japanese_date(date_str: str, current_year: int, current_month: int) -> Optional[date]:
    """
    「12月1日（火）」や「1日（月）」のような文字列をdateオブジェクトに変換する。
    月が省略されている場合は current_month を使用する。
    """
    # 「12月1日」パターン
    m = re.match(r"(\d+)月(\d+)日", date_str)
    if m:
        month = int(m.group(1))
        day = int(m.group(2))
        return date(current_year, month, day)

    # 「1日」パターン（月省略）
    m = re.match(r"(\d+)日", date_str)
    if m:
        day = int(m.group(1))
        return date(current_year, current_month, day)

    return None


def parse_year_month_from_url(url: str) -> tuple[int, int]:
    """
    URLから年月を取得する。例: .../202602/index.html -> 2026年2月
    フォーマット: .../YYYYMM/index.html
    """
    m = re.search(r"/(\d{4})(\d{2})/index\.html", url)
    if m:
        return int(m.group(1)), int(m.group(2))

    # fallback: 現在の日付
    today = date.today()
    return today.year, today.month


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en;q=0.9",
}


def fetch_monthly_links() -> list[dict]:
    """メインページから月別ページのリンク一覧を取得する。"""
    resp = requests.get(SCHEDULE_INDEX, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    links = []
    # 宮内庁サイトの月別リンクを探す（例: 202602/index.html 形式）
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"\d{6}/index\.html", href):
            # 相対URLを絶対URLに変換
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = BASE_URL + href
            else:
                # 相対パス
                base_path = SCHEDULE_INDEX.rsplit("/", 1)[0]
                full_url = base_path + "/" + href

            year, month = parse_year_month_from_url(href)
            links.append({
                "url": full_url,
                "year": year,
                "month": month,
                "label": a.get_text(strip=True),
            })

    # 重複除去・ソート
    seen = set()
    unique = []
    for link in links:
        key = link["url"]
        if key not in seen:
            seen.add(key)
            unique.append(link)

    unique.sort(key=lambda x: (x["year"], x["month"]))
    return unique


def _parse_location_from_content(content: str) -> tuple[str, str]:
    """
    「行事名（場所名／都道府県）」から行事名と場所を分離する。
    場所が見つからない場合は location="" を返す。
    """
    # 末尾の（場所／都道府県）パターン
    m = re.search(r"（([^）]+／[^）]+)）\s*$", content)
    if m:
        location = m.group(1)
        content = content[: m.start()].strip()
        return content, location

    # 「於：場所」パターン
    m = re.search(r"於[：:]\s*(.+)", content)
    if m:
        location = m.group(1).strip()
        content = re.sub(r"於[：:]\s*.+", "", content).strip()
        return content, location

    return content, ""


def fetch_monthly_schedule(url: str, year: int, month: int) -> list[dict]:
    """
    月別ページから佳子内親王殿下の日程一覧を取得する。
    ページ構造: <h2>令和X年Y月Z日（曜）</h2> の下に
    対象者と内容のテーブルが続く形式。
    Returns: [{"date": "2024-12-01", "content": "...", "location": "..."}]
    """
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")

    events = []
    current_date = None

    # ページ内の全要素を順に走査する
    for tag in soup.find_all(["h2", "h3", "tr"]):
        # ── 日付見出し（h2/h3）──
        if tag.name in ("h2", "h3"):
            text = tag.get_text(strip=True)
            # 「令和X年Y月Z日（曜）」を西暦に変換
            m = re.search(r"(\d+)月(\d+)日", text)
            if m:
                try:
                    current_date = date(year, int(m.group(1)), int(m.group(2)))
                except ValueError:
                    current_date = None
            continue

        # ── テーブル行（tr）──
        if current_date is None:
            continue

        cells = tag.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        cell_texts = [c.get_text(separator="", strip=True) for c in cells]

        # 対象者列に「佳子内親王」が含まれる行のみ処理
        target = cell_texts[0]
        if "佳子内親王" not in target:
            continue

        # 内容列（2列目以降を結合）
        raw_content = "　".join(t for t in cell_texts[1:] if t)
        content, location = _parse_location_from_content(raw_content)

        if content:
            events.append({
                "date": current_date.isoformat(),
                "content": content,
                "location": location,
            })

    # h2+table構造で取れなかった場合のフォールバック
    if not events:
        events = _parse_dl_structure(soup, year, month)
    if not events:
        events = _parse_text_structure(soup, year, month)

    return events


def _parse_dl_structure(soup: BeautifulSoup, year: int, month: int) -> list[dict]:
    """dl/dt/dd 形式の日程ページをパースする。"""
    events = []
    current_date = None

    for dl in soup.find_all("dl"):
        for child in dl.children:
            if not hasattr(child, "name"):
                continue
            if child.name == "dt":
                text = child.get_text(strip=True)
                parsed = parse_japanese_date(text, year, month)
                if parsed:
                    current_date = parsed
            elif child.name == "dd" and current_date:
                text = child.get_text(separator=" ", strip=True)
                location = ""
                loc_m = re.search(r"於[：:]\s*(.+)", text)
                if loc_m:
                    location = loc_m.group(1).strip()
                    text = re.sub(r"於[：:]\s*.+", "", text).strip()
                if text:
                    events.append({
                        "date": current_date.isoformat(),
                        "content": text,
                        "location": location,
                    })
    return events


def _parse_text_structure(soup: BeautifulSoup, year: int, month: int) -> list[dict]:
    """プレーンテキストから日程をパースする（フォールバック）。"""
    events = []
    text = soup.get_text(separator="\n")
    current_date = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 日付行の検出
        date_m = re.match(r"(\d+月)?(\d+)日[（(].[）)]", line)
        if date_m:
            parsed = parse_japanese_date(line, year, month)
            if parsed:
                current_date = parsed
            continue

        if current_date and len(line) > 2:
            location = ""
            loc_m = re.search(r"於[：:]\s*(.+)", line)
            if loc_m:
                location = loc_m.group(1).strip()
                line = re.sub(r"於[：:]\s*.+", "", line).strip()
            if line:
                events.append({
                    "date": current_date.isoformat(),
                    "content": line,
                    "location": location,
                })

    return events


def load_existing_data() -> dict[str, list[dict]]:
    """既存のJSONデータを読み込む。キーは "YYYY-MM"。"""
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict[str, list[dict]]) -> None:
    """データをJSONファイルに保存する。"""
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"データを保存しました: {DATA_FILE}")


def scrape(force: bool = False) -> dict[str, list[dict]]:
    """
    全月の日程をスクレイピングする。
    force=False の場合、既取得済みの月はスキップする（差分更新）。
    """
    existing = load_existing_data()
    monthly_links = fetch_monthly_links()

    if not monthly_links:
        print("月別リンクが見つかりませんでした。サイト構造が変わった可能性があります。")
        save_data(existing)  # JSONが存在しない場合に備えて空でも保存する
        return existing

    print(f"月別ページ数: {len(monthly_links)}")

    for link in monthly_links:
        key = f"{link['year']}-{link['month']:02d}"
        if not force and key in existing:
            print(f"スキップ（取得済み）: {key}")
            continue

        print(f"取得中: {key} ({link['url']})")
        try:
            events = fetch_monthly_schedule(link["url"], link["year"], link["month"])
            existing[key] = events
            print(f"  -> {len(events)} 件のイベント")
        except Exception as e:
            print(f"  -> エラー: {e}")

        time.sleep(1)  # サーバー負荷軽減

    save_data(existing)
    return existing


if __name__ == "__main__":
    import sys
    force = "--force" in sys.argv
    data = scrape(force=force)
    total = sum(len(v) for v in data.values())
    print(f"\n合計 {total} 件のイベントを取得しました。")
