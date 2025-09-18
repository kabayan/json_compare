# JSON Compare - JSON類似度比較ツール

JSONLファイル内の`inference1`と`inference2`フィールドの類似度を計算するCLIツール。日本語埋め込みベクトルモデル（cl-nagoya/ruri-v3-310m）を使用して意味的類似度を算出します。

## 特徴

### コア機能
- 🚀 **uvx対応** - インストール不要で即実行可能
- 🧠 **日本語特化** - cl-nagoya/ruri-v3-310mモデルによる高精度な日本語処理
- 💻 **CPU/GPU両対応** - デフォルトCPUで軽量動作、GPUオプションで高速処理
- 📊 **2つの出力形式** - 全体平均（score）と各行詳細（file）
- 🔀 **2ファイル比較** - 2つのJSONLファイルの指定列を比較（新機能）

### Web UI & API機能（新機能）
- 🌐 **直感的なWeb UI** - ドラッグ&ドロップ対応のモダンなインターフェース
- 🔄 **REST API** - プログラマティックなアクセス用の完全なAPI実装
- 📥 **マルチフォーマット対応** - JSON/CSV形式でのダウンロード
- ⚡ **並列処理対応** - 複数のファイルアップロードを同時処理

### 信頼性機能
- 🔧 **自動JSONL修復** - 不正なJSON行を自動的に修復
- 📐 **自動フォーマット修正** - 複数行のJSONオブジェクトを1行1オブジェクト形式に自動変換（新機能）
- 🆔 **エラーID生成** - トラブルシューティング用の一意のエラーID
- 💡 **改善提案** - エラー時に具体的な解決策を提示
- 🔍 **システムリソース監視** - メモリ/ディスク不足の事前検知

### 運用機能
- 📝 **構造化ログ** - JSON形式の3層ログシステム（アクセス/エラー/メトリクス）
- 📊 **メトリクス収集** - アップロード成功率、処理時間などの統計
- 🔄 **ログローテーション** - 10MB制限での自動ローテーション
- 🛡️ **包括的エラーハンドリング** - ユーザーフレンドリーなエラーメッセージ

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

#### 単一ファイル比較（従来機能）
```bash
json_compare <input_file> [options]
```

#### 2ファイル比較（新機能）
```bash
json_compare dual <file1> <file2> [options]
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--type {score,file}` | 出力タイプ<br>• `score`: 全体平均を1行で出力<br>• `file`: 各行の詳細を配列で出力 | `score` |
| `-o, --output <file>` | 出力ファイルパス（省略時は標準出力） | - |
| `--gpu` | GPUを使用（要CUDA環境） | CPU使用 |
| `--column <name>` | 比較する列名（dualコマンド用） | `inference` |
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

### 4. 2ファイル比較（新機能）

2つのJSONLファイルの指定列を抽出して比較：

```bash
# inference列を比較（デフォルト）
json_compare dual file1.jsonl file2.jsonl --type score

# カスタム列名を指定
json_compare dual file1.jsonl file2.jsonl --column custom_text --type score

# 詳細結果を出力
json_compare dual file1.jsonl file2.jsonl --type file -o comparison.json
```

**出力例（dualコマンド）：**
```json
{
  "score": 0.8234,
  "meaning": "非常に類似",
  "total_lines": 100,
  "json": {
    "field_match_ratio": 0.9000,
    "value_similarity": 0.8234,
    "final_score": 0.8234
  },
  "_metadata": {
    "source_files": {
      "file1": "file1.jsonl",
      "file2": "file2.jsonl"
    },
    "column_compared": "inference",
    "rows_compared": 100,
    "gpu_used": false
  }
}
```

## Web UI とAPI（新機能）

### Web UIの起動

```bash
# APIサーバーを起動（ポート18081）
uv run json_compare_api

# ブラウザでアクセス
http://localhost:18081/ui
```

Web UIでは以下の機能が利用可能：
- 📄 **単一ファイル比較** - 従来のinference1/inference2比較
- 📑 **2ファイル比較** - 2つのJSONLファイルの指定列を比較（新機能）
- 📁 JSONLファイルのドラッグ＆ドロップまたは選択
- 🎯 出力形式の選択（スコア/ファイル詳細）
- 🔄 列名の指定（2ファイル比較時）
- ⚡ GPU使用の有無選択
- 💾 結果のJSON/CSV形式でのダウンロード
- 📊 リアルタイムの処理状況表示
- 🔄 エラー時の自動リトライ提案
- 📈 処理統計の表示（処理時間、ファイルサイズなど）

### REST APIエンドポイント

#### 1. 単一ファイルアップロード（従来機能）

```bash
curl -X POST http://localhost:18081/api/compare/single \
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

#### 2. 2ファイル比較（新機能）

```bash
curl -X POST http://localhost:18081/api/compare/dual \
  -F "file1=@file1.jsonl" \
  -F "file2=@file2.jsonl" \
  -F "column=inference" \
  -F "type=score" \
  -F "gpu=false"
```

**レスポンス例：**
```json
{
  "score": 0.8234,
  "meaning": "非常に類似",
  "total_lines": 100,
  "json": {
    "field_match_ratio": 0.9000,
    "value_similarity": 0.8234,
    "final_score": 0.8234
  },
  "_metadata": {
    "source_files": {
      "file1": "file1.jsonl",
      "file2": "file2.jsonl"
    },
    "column_compared": "inference",
    "rows_compared": 100,
    "gpu_used": false
  }
}
```

#### 3. ヘルスチェック

```bash
curl http://localhost:18081/health
```

#### 4. メトリクス確認

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

### コア依存関係
- Python 3.8+
- transformers 4.30+
- torch 2.0+
- scipy 1.10+
- json-repair 0.1+
- sentencepiece 0.1.99+
- protobuf 3.20+

### API/Web UI依存関係
- FastAPI 0.100+
- uvicorn[standard] 0.23+
- python-multipart 0.0.5+
- psutil 5.9+ （システムメトリクス用）

### 開発/テスト依存関係
- pytest 8.0+
- playwright 1.49+ （E2Eテスト用）

## トラブルシューティング

### API/Web UI関連

#### ポート18081が使用中
```bash
# 別のポートで起動
uv run uvicorn src.api:app --host 0.0.0.0 --port 8000
```

#### ファイルアップロードサイズ制限（100MB）を超える
ファイルを分割するか、以下のように制限を変更：
```python
# src/api.py のMAX_FILE_SIZE定数を変更
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
```

#### JSONLファイルの自動修復が失敗する
エラーメッセージに従って手動で修正するか、以下を確認：
- 各行が独立したJSONオブジェクトであること
- inference1とinference2フィールドが存在すること
- UTF-8エンコーディングであること

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

### ユーティリティツール

#### JSONLフォーマット修正ツール

複数行にまたがるJSONオブジェクトを1行1オブジェクト形式に修正するヘルパーツール：

```bash
# 単一ファイルの修正
python3 utils/fix_jsonl_format.py data.jsonl

# ディレクトリ内のすべてのJSONLファイルを修正
python3 utils/fix_jsonl_format.py --dir ./datas

# サブディレクトリも含めて修正
python3 utils/fix_jsonl_format.py --dir . --recursive

# 修正前の確認（ドライラン）
python3 utils/fix_jsonl_format.py --dir ./datas --dry-run

# ファイルの検証のみ
python3 utils/fix_jsonl_format.py --validate data.jsonl
```

**注意**: 通常の処理では、JSONLファイルのフォーマットは自動的に修正されるため、このツールを手動で実行する必要はありません。

### テスト実行

#### 統合テストの実行
```bash
# APIサーバーを起動
uv run json_compare_api &

# 統合テストスイート実行
uv run python tests/test_integration.py
```

#### Web UIテスト（Playwright）
```bash
# Playwrightをインストール
uv run playwright install chromium

# テスト実行
uv run pytest tests/test_ui_playwright_improved.py -xvs
```

#### エラーハンドリングテスト
```bash
uv run python tests/test_error_handling.py
```

### CLIテスト

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

#### access.log
- すべてのHTTPリクエスト
- リクエストID、メソッド、パス、ステータスコード
- クライアントIP、処理時間

#### error.log
- エラーID付きのエラー情報
- スタックトレース
- リカバリ提案

#### metrics.log
- アップロード成功/失敗率
- 平均処理時間
- システムリソース使用状況（CPU、メモリ、ディスク）

ログ形式の例：
```json
{
  "timestamp": "2025-09-17T12:34:56.789Z",
  "event": "upload_completed",
  "filename": "data.jsonl",
  "file_size": 1234567,
  "processing_time": 1.23,
  "gpu_mode": false,
  "result": "success"
}
```

### パフォーマンス最適化

- **並列処理**: 最大5つの同時アップロードをサポート
- **メモリ効率**: ストリーミング処理による大容量ファイル対応
- **キャッシュ**: モデルの事前ロードによる高速化
- **エラーリカバリ**: 自動リトライと部分的な処理の再開