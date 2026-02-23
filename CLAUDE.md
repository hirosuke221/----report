# 住宅選定レポート プロジェクト方針

## プロジェクト概要

兵庫県内の3市（高砂市・加古川市・明石市）から中古住宅を選定するための意思決定支援Quartoレポート。

## 基本情報

- **取得形態**: 中古住宅購入
- **通勤先**: 神戸製鋼所 高砂製作所（兵庫県高砂市荒井町新浜2-3-1）
- **通勤手段**: 車または電車
- **家族構成**: 30代前半夫婦、子なし、1〜2年以内に出産予定
- **レポート形式**: Quarto HTML（embed-resources: true で単一ファイル出力）

## 評価軸と重み付け（6軸）

| 評価軸 | 重み | 備考 |
|--------|------|------|
| 治安・安全性 | 20% | 子どもの安全な育ちに直結 |
| 教育環境 | 20% | 長期的な教育選択肢（保育〜高校） |
| 交通アクセス | 10% | 高砂製作所への通勤効率 |
| 子育て支援・行政 | 15% | 保育料・医療費助成など出産後の家計負担（新規追加） |
| 医療環境 | 10% | 産婦人科・NICU・小児救急など出産育児の医療アクセス（新規追加） |
| 住宅価格 | 25% | 中古住宅購入コスト |

※「将来の資産価値」章は根拠不十分のため削除済み。

## データソース（確定版）

| データ | 取得方法 | 備考 |
|--------|----------|------|
| 住宅取引価格（成約） | **不動産情報ライブラリ**（国土交通省）からCSV手動ダウンロード | 旧API（land.mlit.go.jp/webland）は2024年5月廃止。新API（reinfolib.mlit.go.jp）はAPIキー申請が必要なため手動DL対応 |
| 住宅売出し価格（現在） | **scraping_suumo.py** でSUUMOをスクレイピング | 初回のみ実行。`data/suumo_listings.csv` に保存 |
| 人口動態 | `data_collect.py` 内に手動入力済み | 総務省 住民基本台帳 各年1月1日時点 |
| 犯罪統計 | **`data_collect.py` の `parse_crime_pdf()` が `data/R06.pdf` を自動解析** | 兵庫県警察「市区町別刑法犯認知状況（令和6年確定値）」。`pdfplumber` でテーブル抽出 |
| 教育環境 | `data_collect.py` 内に手動入力済み | 文部科学省 学校基本調査2023年 |
| 子育て支援・行政 | `data_collect.py` 内に手動入力済み | 各市公式HP / こども家庭庁（2024年度） |
| 医療環境 | `data_collect.py` 内に手動入力済み | 厚生労働省「医療機能情報提供制度（ナビイ）」/ 各病院公式HP |
| ハザードリスク | `index.qmd` 内にテーブルで手動記述 | 国土交通省ハザードマップポータル参照 |
| 交通アクセス | `index.qmd` 内にテーブルで手動記述 | Googleマップ・乗換案内参照 |

## 市区町村コード（実CSVより確認済み）

- 高砂市: **28216**（旧メモの28214は誤り。28214は三木市）
- 加古川市: 28210
- 明石市: 28203

## ファイル構成

```
住宅選定report/
├── CLAUDE.md              # このファイル（プロジェクト方針）
├── _quarto.yml            # Quarto設定（cosmoテーマ、embed-resources）
├── index.qmd              # メインレポート（出典明記済み）
├── data_collect.py        # データ収集・整形スクリプト（住宅価格以外）
├── scraping_suumo.py      # SUUMOスクレイパー（初回のみ実行）
└── data/
    ├── R06.pdf                               # 兵庫県警察「市区町別刑法犯認知状況（令和6年）」
    ├── Hyogo Prefecture_Akashi City_*.csv    # 不動産情報ライブラリからDL
    ├── Hyogo Prefecture_Kakogawa City_*.csv  # 同上
    ├── Hyogo Prefecture_Takasago City_*.csv  # 同上
    ├── housing_prices.csv       # data_collect.py が生成（成約価格）
    ├── suumo_listings.csv       # scraping_suumo.py が生成（売出し価格）
    ├── population.csv           # data_collect.py が生成
    ├── crime_stats.csv          # data_collect.py が R06.pdf を解析して生成（令和6年）
    ├── nursery.csv              # data_collect.py が生成
    ├── highschool.csv           # data_collect.py が生成
    ├── childcare_support.csv    # data_collect.py が生成（子育て支援・行政）
    └── medical.csv              # data_collect.py が生成（医療環境）
```

## Python環境

既存の仮想環境を使用: `c:\Users\akiya\Documents\Quarto\Qvenv\`

インストール済みパッケージ（通常と異なるもの）:
- `pdfplumber` — R06.pdf の解析用

## 実行手順

```bash
# 1. データ収集・整形（住宅価格以外）
#    ※ data/R06.pdf が存在すること（なければブラウザでDL）
PYTHONIOENCODING=utf-8 c:\Users\akiya\Documents\Quarto\Qvenv\Scripts\python.exe data_collect.py

# 2. SUUMOスクレイピング（初回のみ。data/suumo_listings.csv を生成）
PYTHONIOENCODING=utf-8 c:\Users\akiya\Documents\Quarto\Qvenv\Scripts\python.exe scraping_suumo.py

# 3. レポート生成
quarto render index.qmd
```

※ Windows bash から実行する場合は `PYTHONIOENCODING=utf-8` を先頭に付けること（✓ 文字のcp932エンコーディングエラー回避）

## 犯罪統計 PDF 解析の仕様

- **PDFソース**: `data/R06.pdf`（兵庫県警察 令和6年確定値、手動DL必要）
  - DL URL: https://www.police.pref.hyogo.lg.jp/seikatu/gaitou/statis/data/R06.pdf
- **PDF構造**: 1ページ・1テーブル・55行×18列
  - 市名セルは文字間スペース入り（例: "高 砂 市"）→ `.replace(" ", "")` で正規化して比較
  - col0=市名、col2=人口（人）、col3=刑法犯総数（認知件数）
- **令和6年データ**: 高砂568件(67.4/万人) / 加古川1754件(68.8/万人) / 明石1881件(61.4/万人)
- **注意**: ターミナル出力は文字化けするが、ファイル書き出し（UTF-8）では正常

## スコアリングの仕様

### 治安スコア（絶対評価）

3市間の相対比較ではなく、**兵庫県下平均（71.0件/万人）を基準とした絶対評価**を採用：

```
score = clip(5 - 4 × city_rate / (2 × 71.0), 1.0, 5.0)
```

| rate | score |
|------|-------|
| 0件/万人 | 5.0（最良） |
| 71.0件/万人（県下平均） | 3.0 |
| 142.0件/万人（平均の2倍） | 1.0（最低） |

### 住宅価格スコア（相対評価）

```
score = 5 - 4 × (median - min_median) / (max_median - min_median)
```
3市内での最安値=5点、最高値=1点の線形変換。

### 手動スコア（5点満点、小数点第一位まで）

| 軸 | 高砂市 | 加古川市 | 明石市 |
|----|--------|----------|--------|
| 教育環境 | 2 | 4 | 4 |
| 交通アクセス | 5 | 3 | 2 |
| 子育て支援 | 3 | 3 | 5 |
| 医療環境 | 2 | 4 | 5 |

スコアテーブルの表示は `.round(1)` で小数点第一位まで。

### 総合スコア試算（参考値）

| 市 | 総合スコア | 順位 |
|----|-----------|------|
| 加古川市 | 3.6 | 1位 |
| 明石市 | 3.6 | 2位 |
| 高砂市 | 3.5 | 3位 |

## 子育て支援・行政スコアリングの根拠

- **高砂市（3点）**: 医療費助成は18歳まで（所得制限あり）、支援センター2か所、独自施策は限定的
- **加古川市（3点）**: 播磨地域の中心として標準的施策、支援センター6か所
- **明石市（5点）**: 第2子保育料全額無償化（全国初）、所得制限なし医療費助成、支援センター8か所

## 医療環境スコアリングの根拠

- **高砂市（2点）**: 産婦人科2施設・小児科8施設、NICU保有病院なし、夜間救急は加古川市依存
- **加古川市（4点）**: 産婦人科7施設・小児科28施設、加古川市民病院にNICU、夜間急病センターあり
- **明石市（5点）**: 産婦人科9施設・小児科35施設、明石市立市民病院にNICU、急病センターあり

## SUUMOスクレイパーの仕様メモ

- **URL**: `https://suumo.jp/jj/bukken/ichiran/JJ010FJ001/?ar=060&bs={bs}&sc={city_code}&pc=100&page={page}`
  - `ar=060`: 近畿エリア
  - `bs=011`: 中古マンション　`bs=021`: 中古一戸建て（**逆は誤り**）
  - `page=` でページ指定（`pn=` は誤り）
- **セレクター**: 物件コンテナ = `div.property_unit`、価格 = `dt="販売価格"` → `dd > span.dottable-value`
- **混入対策**: `sc=` 指定でもおすすめ広告として他市物件が混入する → `所在地` フィルターで除外済み
- **スクレイピング結果**（2026-02-23時点）: 高砂12+100件 / 加古川145+277件 / 明石465+353件

## トラブルシューティング

- **旧API（TradeListSearch）接続エラー**: 2024年5月に廃止済み。不動産情報ライブラリ（https://www.reinfolib.mlit.go.jp/）からCSVをブラウザでダウンロードして `data/` に配置する
- **`#| eval: false` によって章が空欄になる**: Quartoのコードブロックにこのオプションがあると実行されない。意図しない場合は削除する
- **`display()` が未定義エラー**: setup チャンクで `from IPython.display import display` を import する
- **data_collect.py の ✓ 文字でエンコーディングエラー**: bash から実行する場合は `PYTHONIOENCODING=utf-8` を先頭に付けること
- **犯罪統計PDFが解析できない**: `pdfplumber` が未インストールの場合は `pip install pdfplumber`。`data/R06.pdf` が存在しない場合はブラウザでDL
- **犯罪統計の市が見つからない**: PDFの市名セルは文字間スペース入り。`parse_crime_pdf()` 内の `replace(" ", "")` が正しく動作しているか確認
- **SUUMOで0件取得**: `bs` コードを確認（`011`=マンション、`021`=戸建て）。またURLパラメータが `page=` であることを確認（`pn=` は誤り）
- **SUUMOで他市物件が混入**: `所在地` フィルターが機能しているか確認。`scraping_suumo.py` の main() 内に実装済み
- **散布図にトレンド線が出ない**: `pip install statsmodels` を実行する（未インストールでも散布図自体は表示される）
