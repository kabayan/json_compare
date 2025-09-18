# json_compare

JSON形式のデータを意味的類似度で比較するツール

## 概要

json_compareは、2つのJSON形式データを比較し、フィールド名の一致率と値の意味的類似度を組み合わせた総合スコアを算出します。日本語埋め込みベクトルモデル（cl-nagoya/ruri-v3-310m）を使用し、テキストの意味的な類似性を評価できます。

## 主な特徴

- **構造的比較**: JSONのフィールド名一致率を計算
- **意味的比較**: 日本語埋め込みベクトルによる値の類似度評価
- **再帰的処理**: ネストされたオブジェクトやリストも比較可能
- **JSON修復機能**: 不完全なJSONも自動修復して処理

## CLI使用方法

### 入力パラメータ

1. **ファイル指定**
   - ローカルファイルパス
   - ファイルアクセスURL（外部API経由）

2. **結果形式（type）**

   - `"score"`: 総合評価スコアを返す
     ```json
     {
       "file": "入力ファイル名またはURL",
       "score": 0.85,
       "meaning": 0.92,
       "json": 0.78
     }
     ```
     - score: 総合スコア（0-1）
     - meaning: 意味的類似度
     - json: 構造的類似度

   - `"file"`: 行ごとの詳細比較結果を追加したファイルURLを返す

### 出力

指定したtypeに応じた形式で結果を返します。

## 類似度計算アルゴリズム

総合類似度 = フィールド名一致率（A） × フィールド値類似度（B）

- **A**: 共通フィールド数 ÷ 最大フィールド数
- **B**: 共通フィールドの値の平均類似度
  - 完全一致: 1.0
  - 数値: 一致で1.0、不一致で0.1
  - テキスト: 埋め込みベクトルのコサイン類似度
  - リスト/オブジェクト: 再帰的に計算

## 使用例

```bash
# スコア形式で結果を取得
python -m json_compare input1.json input2.json --type score

# 詳細比較結果をファイルで取得
python -m json_compare data1.jsonl data2.jsonl --type file
```

## API仕様

### 概要
既存のCLI機能（json_compare）をHTTP APIとして提供します。
**重要**: 既存実装の修正は禁止。内部関数を直接インポートして呼び出します。

### サーバー設定
- **ポート**: 18081
- **ホスト**: 0.0.0.0（全インターフェースで待ち受け）
- **フレームワーク**: FastAPI

### エンドポイント

#### 1. 比較実行
```
POST /compare
```

**リクエストボディ**:
```json
{
  "file1": "入力ファイルパス（JSONLファイル）",
  "file2": "比較対象ファイルパス（省略時はfile1内のinference1とinference2を比較）",
  "type": "score" | "file",
  "output": "出力ファイルパス（省略可、指定時は結果をファイルに保存）"
}
```

**レスポンス（outputパラメータなしの場合）**:

type="score":
```json
{
  "file": "入力ファイルパス",
  "total_lines": 100,
  "score": 0.8523,
  "meaning": "非常に類似",
  "json": {
    "field_match_ratio": 0.9234,
    "value_similarity": 0.7812,
    "final_score": 0.8523
  }
}
```

type="file":
```json
[
  {
    "inference1": "{...}",
    "inference2": "{...}",
    "similarity_score": 0.8523,
    "similarity_details": {
      "field_match_ratio": 0.9234,
      "value_similarity": 0.7812
    }
  }
]
```

**レスポンス（outputパラメータ指定時）**:
```json
{
  "message": "結果を /path/to/output.json に保存しました",
  "output_path": "/path/to/output.json"
}
```

#### 2. ヘルスチェック
```
GET /health
```

**レスポンス**:
```json
{
  "status": "healthy",
  "cli_available": true
}
```

### 実装方針

#### アーキテクチャ
```
HTTPリクエスト
    ↓
FastAPI（受付・検証）
    ↓
process_jsonl_file()関数を直接呼び出し
    ↓
HTTPレスポンス返却
```

#### 実装詳細
- `from src.__main__ import process_jsonl_file` でインポート
- FastAPIのエンドポイントから直接関数呼び出し
- 一時ファイル処理: アップロードされたファイルを一時保存後、関数に渡す
- 出力ファイル指定時:
  - 結果をJSONファイルとして保存
  - レスポンスに保存先パスを含める
  - 形式: `{"message": "結果を保存しました", "output_path": "指定パス"}`

#### エラーハンドリング
- 関数内で発生する例外をキャッチ
- 適切なHTTPステータスコードに変換（400: Bad Request, 500: Internal Server Error）
- エラーレスポンス形式:
```json
{
  "error": "エラーメッセージ",
  "detail": "CLIからのエラー詳細"
}
```

### 開発・実行

#### 開発環境
```bash
# 依存関係インストール
uv pip install fastapi uvicorn

# サーバー起動
uv run uvicorn src.json_compare.api:app --host 0.0.0.0 --port 18081 --reload
```

#### 本番環境
```bash
# uvxで直接実行
uvx json_compare-api
```
