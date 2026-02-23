"""
住宅選定レポート用 データ収集スクリプト
実行方法: python data_collect.py
出力先: スクリプトと同じフォルダの data/ ディレクトリ

【住宅価格データについて】
不動産情報ライブラリ（https://www.reinfolib.mlit.go.jp/）から
各市の取引価格CSVをダウンロードして data/ に保存してください。
ファイル名パターン: Hyogo Prefecture_<City Name>_*.csv
"""

import pandas as pd
from pathlib import Path
import glob
import pdfplumber

# スクリプトファイルの場所を基準に data/ フォルダを作成する
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

print(f"データ出力先: {DATA_DIR.resolve()}")

# 対象3市とCSVファイルのキーワードの対応
CITIES = {
    "高砂市": "Takasago",
    "加古川市": "Kakogawa",
    "明石市": "Akashi",
}


# ============================================================
# 1. 住宅価格（不動産情報ライブラリのダウンロードCSVを読み込む）
# ============================================================

def load_housing_prices():
    """
    不動産情報ライブラリからダウンロードした CSV を読み込んで
    data/housing_prices.csv に整形・保存する。

    必要ファイル（data/ に配置）:
      Hyogo Prefecture_Takasago City_*.csv
      Hyogo Prefecture_Kakogawa City_*.csv
      Hyogo Prefecture_Akashi City_*.csv
    """
    print("\n【住宅価格】ダウンロード済みCSVからデータを読み込み中...")

    all_records = []
    missing = []

    for city_name, keyword in CITIES.items():
        pattern = str(DATA_DIR / f"Hyogo Prefecture_{keyword} City_*.csv")
        files = glob.glob(pattern)

        if not files:
            print(f"  ⚠ {city_name}: ファイルが見つかりません（{pattern}）")
            missing.append(city_name)
            continue

        # 複数ファイルがあれば全て結合する
        dfs = []
        for fpath in sorted(files):
            df_raw = pd.read_csv(fpath, encoding="cp932")
            dfs.append(df_raw)
            print(f"  読込: {Path(fpath).name}  ({len(df_raw)}行)")

        df = pd.concat(dfs, ignore_index=True)

        # 戸建て（宅地＋建物）とマンションを抽出し、種別ラベルを付与
        def classify_type(s):
            if "土地と建物" in str(s):
                return "戸建て"
            elif "マンション" in str(s):
                return "マンション"
            return None

        df["種別"] = df["種類"].apply(classify_type)
        df_house = df[df["種別"].notna()].copy()

        # 価格・面積を数値化
        df_house["取引価格（万円）"] = (
            pd.to_numeric(df_house["取引価格（総額）"], errors="coerce") / 10000
        )
        df_house["延床面積（㎡）"] = pd.to_numeric(df_house["延床面積（㎡）"], errors="coerce")
        df_house["面積（㎡）"] = pd.to_numeric(df_house["面積（㎡）"], errors="coerce")

        # 異常値（0以下）を除外
        df_house = df_house[df_house["取引価格（万円）"] > 0]

        for _, row in df_house.iterrows():
            all_records.append({
                "市": city_name,
                "取引価格（万円）": row["取引価格（万円）"],
                "種別": row["種別"],
                "価格区分": row.get("価格情報区分", ""),
                "建築年": row.get("建築年", ""),
                "延床面積（㎡）": row.get("延床面積（㎡）", ""),
                "面積（㎡）": row.get("面積（㎡）", ""),
                "地区名": row.get("地区名", ""),
                "取引時期": row.get("取引時期", ""),
            })

        n = len(df_house)
        med = df_house["取引価格（万円）"].median()
        print(f"  ✓ {city_name}: {n}件（中央値 {med:.0f}万円）")

    if missing:
        print()
        print("  以下の市のCSVが未配置です:")
        for city_name in missing:
            keyword = CITIES[city_name]
            print(f"    {city_name}: 不動産情報ライブラリで '{keyword}' を検索してダウンロードしてください")
            print(f"    URL: https://www.reinfolib.mlit.go.jp/")

    if all_records:
        df_out = pd.DataFrame(all_records)
        output_path = DATA_DIR / "housing_prices.csv"
        df_out.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n  ✓ 計{len(df_out)}件 → {output_path} に保存しました")

        # 集計表示
        summary = df_out.groupby("市")["取引価格（万円）"].describe()[
            ["count", "min", "50%", "mean", "max"]
        ].round(0)
        summary.columns = ["件数", "最安値", "中央値", "平均", "最高値"]
        print(summary.to_string())
    else:
        print("  ⚠ 住宅価格データがありません")


# ============================================================
# 2. 人口動態
# ============================================================

def save_population():
    """
    各市の人口推移データを保存する。
    出典: 総務省 住民基本台帳人口・世帯数表（各年1月1日時点）
    """
    print("\n【人口動態】データを保存中...")

    population_data = {
        "年": [2018, 2019, 2020, 2021, 2022, 2023, 2024],
        "高砂市": [87589, 86900, 86054, 85195, 84334, 83556, 82871],
        "加古川市": [263078, 261946, 260560, 259067, 258074, 257279, 256632],
        "明石市": [293157, 294898, 295685, 296554, 296826, 297030, 297230],
    }

    df = pd.DataFrame(population_data)
    df_melted = df.melt(id_vars="年", var_name="市", value_name="人口")

    output_path = DATA_DIR / "population.csv"
    df_melted.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ 人口データを {output_path} に保存しました")

    for city in ["高砂市", "加古川市", "明石市"]:
        start = population_data[city][0]
        end = population_data[city][-1]
        change = (end - start) / start * 100
        print(f"  {city}: {start:,} → {end:,}人 ({change:+.1f}%)")


# ============================================================
# 3. 犯罪統計（兵庫県警察 R06.pdf より解析）
# ============================================================

PDF_PATH = DATA_DIR / "R06.pdf"
TARGET_CITIES = ["高砂市", "加古川市", "明石市"]

# デバッグ用: PDFの全テーブル構造を出力する（列インデックス確認時に使用）
def debug_crime_pdf():
    """R06.pdf のテーブル構造をデバッグ出力する"""
    with pdfplumber.open(PDF_PATH) as pdf:
        for i, page in enumerate(pdf.pages):
            for j, table in enumerate(page.extract_tables()):
                print(f"=== Page {i}, Table {j} ===")
                for row in table[:10]:
                    print(row)


def parse_crime_pdf() -> dict:
    """
    R06.pdf（令和6年確定値）から高砂市・加古川市・明石市の
    刑法犯認知件数と人口を抽出する。
    PDF のセル値は "高 砂 市" のように文字間スペースが入る。
    列構造: [市名, サブ名, 人口(人), 刑法犯総数, 1000人あたり, ...]
    Returns: {"高砂市": {"count": int, "pop_man": float}, ...}
    """
    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"R06.pdf が見つかりません: {PDF_PATH}\n"
            "ブラウザでダウンロードして data/R06.pdf に配置してください:\n"
            "https://www.police.pref.hyogo.lg.jp/seikatu/gaitou/statis/data/R06.pdf"
        )
    results = {}
    with pdfplumber.open(PDF_PATH) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for row in table:
                    if not row or not row[0]:
                        continue
                    # PDF 内の市名は文字間にスペースが入る（例: "高 砂 市"）
                    cell = str(row[0]).replace(" ", "").replace("\n", "")
                    for city in TARGET_CITIES:
                        if city == cell:
                            try:
                                # col3: 刑法犯総数（認知件数）、col2: 人口（人）
                                count = int(str(row[3]).replace(",", "").strip())
                                pop_man = round(int(str(row[2]).replace(",", "").strip()) / 10000, 2)
                                results[city] = {"count": count, "pop_man": pop_man}
                            except (ValueError, IndexError):
                                pass
    return results


def save_crime_stats():
    """
    犯罪統計を R06.pdf（令和6年確定値）から取得して CSV 保存する。
    出典: 兵庫県警察「市区町別刑法犯認知状況（令和6年）」
    https://www.police.pref.hyogo.lg.jp/seikatu/gaitou/statis/data/R06.pdf
    """
    print("\n【犯罪統計】R06.pdf からデータを解析中...")

    parsed = parse_crime_pdf()

    rows = []
    for city in TARGET_CITIES:
        count = parsed[city]["count"]
        pop_man = parsed[city]["pop_man"]
        rows.append({
            "市": city,
            "認知件数（件）": count,
            "人口（万人）": pop_man,
            "年": 2024,
            "人口1万人あたり認知件数": round(count / pop_man, 1),
        })

    df = pd.DataFrame(rows)
    output_path = DATA_DIR / "crime_stats.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ 犯罪統計データを {output_path} に保存しました（令和6年確定値）")
    print(df[["市", "認知件数（件）", "人口1万人あたり認知件数"]].to_string(index=False))


# ============================================================
# 4a. 保育園・就学前教育（手動入力）
# ============================================================

def save_nursery_data():
    """
    各市の保育所・就学前教育環境データを保存する。
    出典: 各市公式ウェブサイト / こども家庭庁 保育所等関連状況取りまとめ（2023年4月）
    """
    print("\n【保育園・就学前教育】データを保存中...")

    nursery_data = {
        "市": ["高砂市", "加古川市", "明石市"],
        "認可保育所数": [23, 67, 49],
        "認定こども園数": [8, 18, 22],
        "合計施設数": [31, 85, 71],
        "待機児童数（人）": [0, 2, 5],
        "保育料月額目安（万円）": [5.5, 5.5, 3.0],
        "第2子以降無償化": ["一部", "一部", "全額（独自施策）"],
        "病児保育対応施設数": [2, 5, 7],
    }
    df = pd.DataFrame(nursery_data)

    output_path = DATA_DIR / "nursery.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ 保育園データを {output_path} に保存しました")
    print(df[["市", "合計施設数", "待機児童数（人）", "保育料月額目安（万円）"]].to_string(index=False))


# ============================================================
# 4b. 高校進学環境（手動入力）
# ============================================================

def save_highschool_data():
    """
    各市の主要公立高校と偏差値データを保存する。
    出典: みんなの高校情報 / 高校受験ナビ（2024年度参照値）
    ※ 偏差値は年度により変動します。最新値をご確認ください。
    """
    print("\n【高校進学環境】データを保存中...")

    highschool_data = {
        "市": [
            "高砂市", "高砂市",
            "加古川市", "加古川市", "加古川市", "加古川市",
            "明石市", "明石市", "明石市", "明石市", "明石市",
        ],
        "高校名": [
            "高砂高校", "高砂南高校",
            "加古川東高校", "加古川西高校", "加古川北高校", "加古川南高校",
            "明石高校", "明石城西高校", "明石南高校", "明石北高校", "明石西高校",
        ],
        "偏差値": [55, 42, 68, 57, 52, 44, 60, 52, 47, 47, 45],
    }
    df = pd.DataFrame(highschool_data)

    output_path = DATA_DIR / "highschool.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ 高校データを {output_path} に保存しました")
    for city in ["高砂市", "加古川市", "明石市"]:
        sub = df[df["市"] == city]["偏差値"]
        print(f"  {city}: {len(sub)}校、偏差値 {sub.min()}〜{sub.max()}（中央値 {sub.median():.0f}）")


# ============================================================
# 5. 子育て支援・行政サービス（手動入力）
# ============================================================

def save_childcare_support_data():
    """
    各市の子育て支援・行政サービスデータを保存する。
    出典: 各市公式ウェブサイト / こども家庭庁
    """
    print("\n【子育て支援・行政サービス】データを保存中...")

    childcare_data = {
        "市": ["高砂市", "加古川市", "明石市"],
        "子ども医療費助成年齢上限": [18, 18, 18],
        "子ども医療費所得制限": ["あり", "あり", "なし"],
        "子育て支援センター数": [2, 6, 8],
        "第2子以降保育料無償化": ["一部", "一部", "全額（独自施策）"],
        "病児保育対応施設数": [2, 5, 7],
        "総合スコア（5点満点）": [3, 3, 5],
    }
    df = pd.DataFrame(childcare_data)

    output_path = DATA_DIR / "childcare_support.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ 子育て支援データを {output_path} に保存しました")
    print(df[["市", "子育て支援センター数", "第2子以降保育料無償化", "総合スコア（5点満点）"]].to_string(index=False))


# ============================================================
# 6. 医療環境（手動入力）
# ============================================================

def save_medical_data():
    """
    各市の医療環境データを保存する。
    出典: 厚生労働省「医療機能情報提供制度（ナビイ）」/ 各病院公式HP
    """
    print("\n【医療環境】データを保存中...")

    medical_data = {
        "市": ["高砂市", "加古川市", "明石市"],
        "産婦人科・産科施設数": [2, 7, 9],
        "小児科施設数": [8, 28, 35],
        "総合病院数（200床以上）": [1, 3, 2],
        "NICU保有": ["なし", "あり", "あり"],
        "夜間救急小児対応": ["市外依存", "あり", "あり"],
        "総合スコア（5点満点）": [2, 4, 5],
    }
    df = pd.DataFrame(medical_data)

    output_path = DATA_DIR / "medical.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"  ✓ 医療環境データを {output_path} に保存しました")
    print(df[["市", "産婦人科・産科施設数", "小児科施設数", "NICU保有", "総合スコア（5点満点）"]].to_string(index=False))


# ============================================================
# 後片付け: 作業用一時ファイルを削除
# ============================================================

def cleanup_temp_files():
    for tmp in ["_inspect.json", "_summary.json"]:
        p = DATA_DIR / tmp
        if p.exists():
            p.unlink()


# ============================================================
# メイン実行
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("住宅選定レポート データ収集スクリプト")
    print("=" * 60)

    load_housing_prices()
    save_population()
    save_crime_stats()
    save_nursery_data()
    save_highschool_data()
    save_childcare_support_data()
    save_medical_data()
    cleanup_temp_files()

    print("\n" + "=" * 60)
    print("データ収集完了。以下のファイルが data/ に保存されました：")
    for f in sorted(DATA_DIR.glob("*.csv")):
        if not f.name.startswith("Hyogo"):  # 元のダウンロードCSVは除く
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")
    print(f"\n次のステップ: quarto render {SCRIPT_DIR / 'index.qmd'}")
    print("=" * 60)
