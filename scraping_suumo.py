"""
SUUMO 中古住宅スクレイパー
高砂市・加古川市・明石市の中古戸建て・マンション一覧を取得して
data/suumo_listings.csv に保存する。

実行方法:
    c:\\Users\\akiya\\Documents\\Quarto\\Qvenv\\Scripts\\python.exe scraping_suumo.py

注意:
    - リクエスト間に 2 秒の待機を入れてサーバー負荷を軽減しています。
    - 生成されたCSVは index.qmd から参照します。
"""

import re
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# ────────────────────────────────────────────────
# 設定
# ────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = DATA_DIR / "suumo_listings.csv"

# 対象3市の市区町村コード（SUUMO sc パラメータ）
CITIES = {
    "高砂市":  "28216",
    "加古川市": "28210",
    "明石市":  "28203",
}

# SUUMOの bs パラメータ（HTML確認済み）
# bs=011 → 中古マンション、bs=021 → 中古一戸建て
TYPES = {
    "マンション": "011",
    "戸建て":    "021",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DELAY_SECONDS = 2
REQUEST_TIMEOUT = 20
MAX_PAGES = 20


# ────────────────────────────────────────────────
# ユーティリティ
# ────────────────────────────────────────────────

def build_url(city_code: str, bs: str, page: int = 1) -> str:
    """SUUMO物件一覧URLを生成する。ar=060 は近畿エリア、page= でページ指定"""
    return (
        f"https://suumo.jp/jj/bukken/ichiran/JJ010FJ001/"
        f"?ar=060&bs={bs}&sc={city_code}&pc=100&page={page}"
    )


def parse_price(text: str) -> float | None:
    """テキストから価格（万円）を数値として抽出する"""
    text = text.replace("\xa0", "").replace(" ", "")
    m = re.search(r"([\d,]+)\s*万円", text)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def parse_area(text: str) -> float | None:
    """テキストから面積（㎡）を数値として抽出する。m2（sup変換後）も対応"""
    if not text:
        return None
    # BeautifulSoup の get_text() では <sup>2</sup> → "2" になるため m2 にも対応
    m = re.search(r"([\d.]+)\s*(?:㎡|m2)", text)
    if m:
        return float(m.group(1))
    return None


def has_next_page(soup: BeautifulSoup) -> bool:
    """「次へ」リンクが存在するか確認する（SUUMO のページネーション構造）"""
    for a in soup.select("p.pagination-parts a"):
        if "次へ" in a.get_text():
            return True
    return False


# ────────────────────────────────────────────────
# スクレイピング本体
# ────────────────────────────────────────────────

def parse_properties(soup: BeautifulSoup, city: str, type_name: str) -> list[dict]:
    """
    BeautifulSoup から各物件（property_unit）を抽出して辞書のリストで返す。

    SUUMO の HTML 構造（2025年確認）:
      <div class="property_unit ...">
        <h2 class="property_unit-title"><a href="...">物件名</a></h2>
        <div class="dottable dottable--cassette">
          <div class="dottable-line">
            <dl><dt>販売価格</dt><dd><span class="dottable-value">820万円</span></dd></dl>
          </div>
          <div class="dottable-line">
            <dl><dt>所在地</dt><dd>兵庫県高砂市...</dd></dl>
            <dl><dt>沿線・駅</dt><dd>JR宝殿 徒歩6分</dd></dl>
          </div>
          <div class="dottable-line">
            <table class="dottable-fix">
              <tr><td><dl><dt>専有面積</dt><dd>60.88m2（壁芯）</dd></dl></td>
                  <td><dl><dt>間取り</dt><dd>3DK</dd></dl></td></tr>
            </table>
          </div>
        </div>
      </div>
    """
    units = soup.select("div.property_unit")
    records = []

    for unit in units:
        record: dict = {
            "市":        city,
            "種別":      type_name,
            "価格（万円）":   None,
            "間取り":       "",
            "専有面積（㎡）":  None,
            "土地面積（㎡）":  None,
            "建物面積（㎡）":  None,
            "築年月":       "",
            "交通":        "",
            "所在地":       "",
            "物件名":       "",
            "URL":        "",
        }

        # ── 物件名・URL ──────────────────────────────
        title_a = unit.select_one("h2.property_unit-title a")
        if title_a:
            record["URL"] = (
                "https://suumo.jp" + title_a["href"]
                if title_a.get("href", "").startswith("/")
                else title_a.get("href", "")
            )

        # ── dottable--cassette 内の全 dl を解析 ──────
        cassette = unit.select_one("div.dottable--cassette")
        if not cassette:
            continue

        for dl in cassette.select("dl"):
            dt_el = dl.select_one("dt")
            dd_el = dl.select_one("dd")
            if not dt_el or not dd_el:
                continue
            key = dt_el.get_text(strip=True)
            val = dd_el.get_text(strip=True)

            if key == "物件名":
                record["物件名"] = val
            elif key == "販売価格":
                # span.dottable-value のテキストを優先
                sv = dd_el.select_one("span.dottable-value")
                price_text = sv.get_text(strip=True) if sv else val
                record["価格（万円）"] = parse_price(price_text)
            elif key == "所在地":
                record["所在地"] = val
            elif key in ("沿線・駅", "交通"):
                record["交通"] = val
            elif key == "専有面積":
                record["専有面積（㎡）"] = parse_area(val)
            elif key in ("土地面積", "敷地面積"):
                record["土地面積（㎡）"] = parse_area(val)
            elif key in ("建物面積", "建物面積（延べ）"):
                record["建物面積（㎡）"] = parse_area(val)
            elif key == "間取り":
                record["間取り"] = val
            elif key == "築年月":
                record["築年月"] = val

        # 価格が取れた物件のみ追加（バナー・広告ブロック除外）
        if record["価格（万円）"] is not None:
            records.append(record)

    return records


def scrape_city_type(city: str, city_code: str, type_name: str, bs: str) -> list[dict]:
    """1市×1種別について全ページを取得してレコードのリストを返す"""
    all_records: list[dict] = []

    for page in range(1, MAX_PAGES + 1):
        url = build_url(city_code, bs, page)
        print(f"  取得中: {city} {type_name} p{page}")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"  ⚠ リクエスト失敗: {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        records = parse_properties(soup, city, type_name)

        if not records:
            if page == 1:
                print(f"  ⚠ 1件も取得できませんでした（物件なし or HTML構造変更の可能性）")
            else:
                print(f"  ページ {page}: 件数0のため終了")
            break

        all_records.extend(records)
        print(f"  → {len(records)} 件取得（累計 {len(all_records)} 件）")

        if not has_next_page(soup):
            break

        time.sleep(DELAY_SECONDS)

    return all_records


# ────────────────────────────────────────────────
# メイン
# ────────────────────────────────────────────────

def main() -> None:
    print(f"=== SUUMO スクレイピング開始 ({date.today()}) ===")
    print(f"出力先: {OUTPUT_FILE}\n")

    all_records: list[dict] = []

    for city, city_code in CITIES.items():
        for type_name, bs in TYPES.items():
            print(f"【{city} / {type_name}】")
            records = scrape_city_type(city, city_code, type_name, bs)
            all_records.extend(records)
            print(f"  小計: {len(records)} 件\n")
            time.sleep(DELAY_SECONDS)

    if not all_records:
        print("⚠ データが1件も取得できませんでした。")
        return

    df = pd.DataFrame(all_records)

    col_order = [
        "市", "種別", "価格（万円）", "間取り",
        "専有面積（㎡）", "土地面積（㎡）", "建物面積（㎡）",
        "築年月", "交通", "所在地", "物件名", "URL",
    ]
    for col in col_order:
        if col not in df.columns:
            df[col] = None
    df = df[col_order]

    # SUUMO はおすすめ広告として他市の物件を混入させることがある。
    # 「所在地」列が対象市名を含む行のみを残す。
    before = len(df)
    mask = df.apply(lambda row: str(row["市"]) in str(row["所在地"]), axis=1)
    df = df[mask].reset_index(drop=True)
    removed = before - len(df)
    if removed > 0:
        print(f"  ※ 所在地フィルター: {removed} 件除外（他市の広告物件）")

    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print(f"[OK] 保存完了: {OUTPUT_FILE}")
    print(f"   総件数: {len(df)} 件\n")

    summary = (
        df.groupby(["市", "種別"])["価格（万円）"]
        .agg(件数="count", 中央値="median", 最安値="min", 最高値="max")
        .round(0)
        .astype({"件数": int})
    )
    print(summary.to_string())


if __name__ == "__main__":
    main()
