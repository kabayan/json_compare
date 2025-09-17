# JSON Compare - JSON類似度比較ツール

JSONLファイル内の`inference1`と`inference2`フィールドの類似度を計算するCLIツール。日本語埋め込みベクトルモデル（cl-nagoya/ruri-v3-310m）を使用して意味的類似度を算出します。

## 特徴

- 🚀 **uvx対応** - インストール不要で即実行可能
- 🧠 **日本語特化** - cl-nagoya/ruri-v3-310mモデルによる高精度な日本語処理
- 💻 **CPU/GPU両対応** - デフォルトCPUで軽量動作、GPUオプションで高速処理
- 📊 **2つの出力形式** - 全体平均（score）と各行詳細（file）
- 🌐 **Web UI/API対応** - ブラウザからのファイルアップロードとREST API
- 📈 **エラーハンドリング** - 自動JSONL修復機能とエラーID生成
- 📝 **詳細ログ** - アクセス、エラー、メトリクスの3種類のログ

## インストール

### uvx経由での実行（推奨）

インストール不要で直接実行：

```bash
uvx --from . json_compare input.jsonl --type score
```

### ローカルインストール

```bash
# リポジトリのクローン
git clone https://github.com/yourusername/json_compare.git
cd json_compare

# uv環境での実行
uv run python -m src.__main__ input.jsonl --type score
```

## 使い方

### 基本コマンド

```bash
json_compare <input_file> [options]
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--type {score,file}` | 出力タイプ<br>• `score`: 全体平均を1行で出力<br>• `file`: 各行の詳細を配列で出力 | `score` |
| `-o, --output <file>` | 出力ファイルパス（省略時は標準出力） | - |
| `--gpu` | GPUを使用（要CUDA環境） | CPU使用 |
| `-h, --help` | ヘルプを表示 | - |

## 使用例

### 1. 全体の類似度平均を確認（scoreタイプ）

```bash
# 標準出力に結果を表示
uvx --from . json_compare data.jsonl --type score

# ファイルに保存
uvx --from . json_compare data.jsonl --type score -o result.json
```

**出力例：**
```json
{
  "file": "data.jsonl",
  "total_lines": 145,
  "score": 0.7587,
  "meaning": "類似",
  "json": {
    "field_match_ratio": 0.8483,
    "value_similarity": 0.7587,
    "final_score": 0.7587
  }
}
```

### 2. 各行の詳細を確認（fileタイプ）

```bash
uvx --from . json_compare data.jsonl --type file -o details.json
```

**出力例：**
```json
[
  {
    "input": "元のテキスト...",
    "inference1": "{\"response\": \"カテゴリA\"}",
    "inference2": "{\"response\": \"カテゴリB\"}",
    "similarity_score": 0.9209,
    "similarity_details": {
      "field_match_ratio": 1.0,
      "value_similarity": 0.9209
    }
  },
  ...
]
```

### 3. GPU使用（高速処理）

```bash
uvx --from . json_compare data.jsonl --type score --gpu
```

## Web UI とAPI

### Web UIの起動

```bash
# APIサーバーを起動（ポート18081）
uv run uvicorn src.api:app --host 0.0.0.0 --port 18081

# ブラウザでアクセス
http://localhost:18081/ui
```

Web UIでは以下の機能が利用可能：
- JSONLファイルのドラッグ＆ドロップまたは選択
- 出力形式の選択（スコア/ファイル詳細）
- GPU使用の有無選択
- 結果のJSON/CSV形式でのダウンロード

### REST APIエンドポイント

#### 1. ファイルアップロード

```bash
curl -X POST http://localhost:18081/upload \
  -F "file=@data.jsonl" \
  -F "type=score" \
  -F "gpu=false"
```

**レスポンス例（エラーハンドリング付き）：**
```json
{
  "overall_similarity": 0.7587,
  "statistics": {
    "mean": 0.7587,
    "median": 0.7654,
    "std_dev": 0.1234
  },
  "_metadata": {
    "processing_time": "1.23秒",
    "original_filename": "data.jsonl",
    "gpu_used": false
  }
}
```

#### 2. ヘルスチェック

```bash
curl http://localhost:18081/health
```

#### 3. メトリクス確認

```bash
curl http://localhost:18081/metrics
```

**レスポンス例：**
```json
{
  "upload_metrics": {
    "total_uploads": 25,
    "successful_uploads": 23,
    "failed_uploads": 2,
    "success_rate": 92.0,
    "average_processing_time": 0.85
  },
  "timestamp": "2025-09-17T12:34:56.789Z"
}
```

### エラーレスポンス

APIはユーザーフレンドリーなエラーメッセージを返します：

```json
{
  "detail": {
    "error_id": "ERR-20250917-abc123",
    "error": "ファイルの形式に問題があります",
    "details": {
      "filename": "test.txt",
      "expected": ".jsonl"
    },
    "suggestions": [
      "ファイルがJSONL形式であることを確認してください",
      "各行が有効なJSONオブジェクトであることを確認してください"
    ],
    "timestamp": "2025-09-17T12:34:56.789Z"
  }
}
```

## 入力ファイル形式

JSONLファイル（1行1JSON）で、各行に`inference1`と`inference2`フィールドが必要：

```jsonl
{"input": "テキスト1", "inference1": "{\"response\": \"分類A\"}", "inference2": "{\"response\": \"分類B\"}"}
{"input": "テキスト2", "inference1": "{\"response\": \"分類C\"}", "inference2": "{\"response\": \"分類D\"}"}
```

## スコアの意味

| スコア範囲 | 意味 |
|-----------|------|
| 0.99以上 | 完全一致 |
| 0.80-0.99 | 非常に類似 |
| 0.60-0.80 | 類似 |
| 0.40-0.60 | やや類似 |
| 0.40未満 | 低い類似度 |

## 技術仕様

- **埋め込みモデル**: cl-nagoya/ruri-v3-310m（日本語特化）
- **類似度計算**: コサイン類似度
- **スコア算出**: フィールド一致率 × 値類似度
- **JSON修復**: json-repairによる自動修復機能

## 依存関係

- Python 3.8+
- transformers 4.30+
- torch 2.0+
- scipy 1.10+
- json-repair 0.1+
- sentencepiece 0.1.99+
- protobuf 3.20+

## トラブルシューティング

### CUDA out of memoryエラー

GPUメモリ不足の場合は、CPUモード（デフォルト）を使用：

```bash
uvx --from . json_compare input.jsonl --type score  # --gpuを付けない
```

### uvxキャッシュの問題

古いバージョンがキャッシュされている場合：

```bash
uvx --reinstall --from . json_compare input.jsonl --type score
```

## ライセンス

MIT License

## 開発者向け

### テスト実行

```bash
# 開発環境での実行
uv run python -m src.__main__ datas/merged.jsonl --type score

# サンプルデータでのテスト
head -10 datas/merged.jsonl > test.jsonl
uv run python -m src.__main__ test.jsonl --type score
```

### プロジェクト構造

```
json_compare/
├── src/
│   ├── __main__.py      # CLIエントリーポイント
│   ├── api.py           # FastAPI RESTエンドポイント
│   ├── similarity.py    # 類似度計算ロジック
│   ├── embedding.py     # 埋め込みベクトル処理
│   ├── error_handler.py # エラーハンドリングシステム
│   ├── logger.py        # ログシステム
│   └── utils.py         # ユーティリティ関数
├── tests/
│   ├── test_integration.py     # 統合テストスイート
│   ├── test_error_handling.py  # エラーハンドリングテスト
│   └── test_ui_playwright*.py  # WebUIテスト
├── datas/               # データファイル
├── docs/                # ドキュメント
└── pyproject.toml       # パッケージ設定
```

### ログファイル

ログファイルは `/tmp/json_compare/logs/` に保存されます：

- `access.log` - すべてのAPIリクエスト
- `error.log` - エラー情報とスタックトレース
- `metrics.log` - システムメトリクスと統計

ログは自動的にローテーション（10MB制限）され、JSON形式で構造化されています。