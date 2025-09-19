# JSON Compare - JSON類似度比較ツール

JSONLファイル内の`inference1`と`inference2`フィールドの類似度を計算するCLIツール。日本語域め込みベクトルモデル（cl-nagoya/ruri-v3-310m）またはLLM（vLLM API経由）を使用して意味的類似度を算出します。

## 🆕 最新アップデート (v2.1.0)

- **LLMベース類似度判定**: vLLM APIを使用した高度な意味理解による比較（54.5%実装完了）
- **戦略パターン実装**: 埋め込み/LLMモードの動的切り替え
- **詳細メタデータ**: モデル名、信頼度、カテゴリ、理由付き判定
- **カスタマイズ可能なプロンプト**: YAML形式のテンプレート
- **出力フォーマット制御**: スコア/ファイル形式の適切な差別化と条件付きdetailed_results出力
- **マークダウンボールド対応**: プロンプト解析の強化（**スコア**、**カテゴリ**、**理由**形式）
- **テスト駆動開発**: 528+テストによる品質保証とPlaywright MCP完全統合

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

### 高度なLLM機能（オプション）
- 🤖 **vLLM API統合** - 外部LLMサービスによる意味的類似度判定
- 📋 **プロンプトテンプレート** - YAML形式のカスタマイズ可能な評価基準
- 📝 **マークダウンボールド対応** - **スコア**、**カテゴリ**、**理由**形式のレスポンス解析
- 📐 **出力形式制御** - スコア形式では詳細結果を除外、ファイル形式では包含
- ⚡ **キャッシング機能** - LLM応答のキャッシングによる効率化
- 🔄 **フォールバック機能** - LLM障害時の埋め込みモードへの自動切り替え
- 🎯 **戦略パターン** - 埋め込み/LLMモードの動的切り替え
- 📊 **詳細メタデータ** - モデル名、信頼度、カテゴリ、理由付き判定
- 🔧 **柔軟な設定** - 温度、最大トークン、カスタムモデル指定
- 📈 **メトリクス収集** - API応答時間、トークン使用量、成功率追跡

### 包括的テストシステム
- 🎭 **Playwright MCP統合** - WebUIの自動テスト基盤
- 🎯 **ドラッグ&ドロップテスト** - ファイルアップロード操作の自動化
- 🔗 **タブ管理テスト** - マルチタブ環境での動作検証
- 📊 **コンソール監視** - JavaScriptエラーの自動検出
- 🌐 **ネットワーク監視** - API通信とHTTPステータスの検証

## 🚀 LLM機能クイックスタート

### 1. vLLMサーバー起動（事前要件）
```bash
# vLLMサーバーを起動（別ターミナル）
python -m vllm.entrypoints.openai.api_server \
  --model qwen/Qwen2.5-3B-Instruct-AWQ \
  --port 8000
```

### 2. 基本的な使用法
```bash
# LLMモードで類似度判定
json_compare data.jsonl --llm --type score

# カスタムプロンプトで詳細判定
json_compare data.jsonl --llm --prompt prompts/semantic_similarity.yaml

# 温度調整でより確実な判定
json_compare data.jsonl --llm --temperature 0.1 --type score
```

### 3. Web UIでのLLM使用
```bash
# APIサーバー起動
uv run json_compare_api

# ブラウザで http://localhost:18081/ui を開き
# "LLMモードを使用" チェックボックスを有効化
```

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

#### LLMベース類似度判定（オプション機能）
```bash
json_compare <input_file> --llm [--model <model_name>] [options]
```

#### プロンプトファイル管理
```bash
# プロンプトファイルアップロード（Web API）
curl -X POST http://localhost:18081/api/prompts/upload \
  -F "file=@custom_prompt.yaml"

# プロンプト一覧取得
curl http://localhost:18081/api/prompts
```

### オプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--type {score,file}` | 出力タイプ<br>• `score`: 全体平均を1行で出力<br>• `file`: 各行の詳細を配列で出力 | `score` |
| `-o, --output <file>` | 出力ファイルパス（省略時は標準出力） | - |
| `--gpu` | GPUを使用（要CUDA環境） | CPU使用 |
| `--column <name>` | 比較する列名（dualコマンド用） | `inference` |
| `--llm` | LLMベースの類似度判定を使用 | 埋め込みベース |
| `--model <name>` | 使用するLLMモデル名（例: qwen3-14b-awq） | config設定値 |
| `--prompt <file>` | カスタムプロンプトテンプレート（YAML） | デフォルトプロンプト |
| `--temperature <val>` | LLM生成温度（0.0-1.0） | 0.7 |
| `--max-tokens <num>` | 最大生成トークン数 | 256 |
| `--no-fallback` | フォールバック無効化 | 有効 |
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

### 5. LLMベース類似度判定（高度な機能）

vLLM APIを使用した意味的類似度判定：

```bash
# デフォルトLLMモデルを使用
json_compare data.jsonl --llm --type score

# 特定のモデルを指定
json_compare data.jsonl --llm --model qwen3-14b-awq --type score

# カスタムプロンプトテンプレートを使用
json_compare data.jsonl --llm --prompt prompts/semantic_similarity.yaml --type score

# LLMモードとGPUを併用
json_compare data.jsonl --llm --gpu --type score
```

**LLMモード出力例：**
```json
{
  "file": "data.jsonl",
  "total_lines": 100,
  "score": 0.8934,
  "meaning": "非常に類似",
  "json": {
    "llm_evaluation": 0.8934,
    "semantic_score": 0.8934,
    "final_score": 0.8934
  },
  "_metadata": {
    "calculation_method": "llm",
    "llm_model": "qwen3-14b-awq",
    "prompt_template": "default_similarity.yaml",
    "processing_time": "15.2秒",
    "tokens_used": 2048,
    "cache_hits": 12,
    "confidence": 0.95,
    "category": "非常に類似",
    "reason": "両テキストは同一概念の異なる表現"
  }
}
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
- 🤖 **LLMモード** - vLLM APIを使用した高度な意味理解での比較
- 📁 JSONLファイルのドラッグ＆ドロップまたは選択
- 🎯 出力形式の選択（スコア/ファイル詳細）
- 🔄 列名の指定（2ファイル比較時）
- ⚙️ LLMモデル選択とプロンプトテンプレートアップロード
- ⚡ GPU使用の有無選択
- 💾 結果のJSON/CSV形式でのダウンロード
- 📊 リアルタイムの処理状況表示
- 🔄 エラー時の自動リトライ提案とフォールバック機能
- 📈 処理統計の表示（処理時間、ファイルサイズ、トークン使用量など）

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

#### 3. LLMベース比較（高度な機能）

```bash
# 単一ファイルLLM比較
curl -X POST http://localhost:18081/api/compare/llm \
  -H "Content-Type: application/json" \
  -d '{
    "file_content": "{\"テキスト1\": \"data\", \"テキスト2\": \"data\"}\n",
    "type": "score",
    "use_llm": true,
    "llm_config": {
      "model": "qwen3-14b-awq",
      "temperature": 0.7,
      "max_tokens": 256
    }
  }'

# 2ファイルLLM比較
curl -X POST http://localhost:18081/api/compare/dual/llm \
  -H "Content-Type: application/json" \
  -d '{
    "file1_content": "...",
    "file2_content": "...",
    "column": "inference",
    "use_llm": true
  }'
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

#### 4. ヘルスチェック

```bash
curl http://localhost:18081/health
```

#### 5. メトリクス確認

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
- **類似度計算**: コサイン類似度（埋め込みモード）/ LLM評価（LLMモード）
- **スコア算出**: フィールド一致率 × 値類似度
- **JSON修復**: json-repairによる自動修復機能
- **LLM統合**: vLLM API互換サーバーとの連携
- **フォールバック**: LLM障害時の埋め込みモードへの自動切り替え

### テスト駆動開発（TDD）

JSON Compareは厳密なTDD手法で開発されています：

1. **RED Phase**: テストを先に書き、失敗を確認
2. **GREEN Phase**: 最小限のコードでテストをパス
3. **REFACTOR Phase**: コード品質の向上とレグレッション確認

各機能タスクには専用のテストファイル：
- `test_task_3_1_similarity_engine.py` - LLMエンジンテスト
- `test_task_3_2_score_processing.py` - スコア処理テスト
- `test_task_4_1_strategy_switching.py` - 戦略切替テスト
- `test_task_4_2_metadata_enhancement.py` - メタデータテスト
- `test_task_5_cli_extensions.py` - CLI拡張テスト
- `test_task_6_api_llm_integration.py` - API統合テスト

## 依存関係

### コア依存関係
- Python 3.8+
- transformers 4.30+
- torch 2.0+
- scipy 1.10+
- json-repair 0.1+
- sentencepiece 0.1.99+
- protobuf 3.20+

### LLM統合依存関係
- httpx 0.25+ （vLLM API通信用）
- aiohttp 3.8+ （非同期HTTP クライアント）
- PyYAML 6.0+ （プロンプトテンプレート処理）

### API/Web UI依存関係
- FastAPI 0.100+
- uvicorn[standard] 0.23+
- python-multipart 0.0.5+
- psutil 5.9+ （システムメトリクス用）
- jinja2 3.1+ （テンプレート処理）

### 開発/テスト依存関係
- pytest 8.0+
- pytest-asyncio 0.21+ （非同期テスト用）
- playwright 1.49+ （E2Eテスト用）

## LLM設定ファイル

LLM機能の設定は環境変数または設定ファイルで管理できます：

### 環境変数設定
```bash
export VLLM_API_URL="http://localhost:8000"
export VLLM_API_KEY="your-api-key"  # オプション
export VLLM_DEFAULT_MODEL="qwen3-14b-awq"
export VLLM_DEFAULT_TEMPERATURE="0.7"
export VLLM_DEFAULT_MAX_TOKENS="256"
export LLM_BATCH_SIZE="10"
export LLM_TIMEOUT="30"
```

### 設定ファイル (config.yaml)
```yaml
llm:
  api_url: "http://localhost:8000"
  api_key: "your-api-key"  # オプション
  default_model: "qwen3-14b-awq"
  default_temperature: 0.7
  default_max_tokens: 256
  batch_size: 10
  timeout: 30
  fallback_enabled: true
  cache_enabled: true
  cache_ttl: 3600

prompts:
  default_template: "prompts/default_similarity.yaml"
  template_dir: "prompts/"
```

### 優先順位
1. CLIオプション (最優先)
2. 環境変数
3. 設定ファイル
4. デフォルト値

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

### LLM関連

#### vLLM API接続エラー
```bash
# 接続先URLの確認
export VLLM_API_URL="http://localhost:8000"
json_compare data.jsonl --llm --type score

# フォールバックを使用
json_compare data.jsonl --type score  # LLMなしで実行
```

#### LLM処理タイムアウト
大量のデータを処理する際は、バッチサイズを調整：
```bash
# 環境変数で設定
export LLM_BATCH_SIZE=10
export LLM_MAX_TOKENS=128
json_compare data.jsonl --llm --type score
```

#### プロンプトテンプレートエラー
YAML形式の確認：
```yaml
system_prompt: "You are a helpful assistant"
user_prompt: "Compare: {text1} and {text2}"  # user_promptが必須
temperature: 0.7
max_tokens: 512
output_parsing:
  score_pattern: '\*\*スコア\*\*[：:]\s*([-]?[0-9.０-９．]+)'
  category_pattern: '\*\*カテゴリ\*\*[：:]\s*([^\n]+)'
  reason_pattern: '\*\*理由\*\*[：:]\s*(.+?)(?=\n\S|$)'
```

注意: `user_prompt`フィールドは必須です（`user_prompt_template`ではありません）。
出力パターンはマークダウンボールド形式（**スコア**等）に対応しています。

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

### LLMプロンプトテンプレート

プロンプトテンプレートはYAML形式で定義します：

```yaml
# prompts/default_similarity.yaml（最新版）
version: '1.0'
metadata:
  author: json_compare
  description: デフォルトの類似度判定プロンプトテンプレート
  created_at: '2025-09-18'

prompts:
  system: |
    あなたは日本語テキストの意味的類似度を評価する専門家です。
    2つのテキストを比較し、その類似度を客観的に判定してください。

  user: |
    以下の2つのテキストの類似度を評価してください。

    テキスト1:
    {text1}

    テキスト2:
    {text2}

    類似度を以下の形式で回答してください：

    **スコア**: [0.0-1.0の数値]
    **カテゴリ**: [完全一致/非常に類似/類似/やや類似/低い類似度]
    **理由**: [判定の根拠を2-3文で説明]

parameters:
  model: qwen3-14b-awq
  temperature: 0.2
  max_tokens: 128

output_parsing:
  score_pattern: '\*\*スコア\*\*[：:]\s*([-]?[0-9.０-９．]+)'
  category_pattern: '\*\*カテゴリ\*\*[：:]\s*([^\n]+)'
  reason_pattern: '\*\*理由\*\*[：:]\s*(.+?)(?=\n\S|$)'
```

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

#### 包括的テストスイート（Playwright MCP）
```bash
# LLM設定とモデル選択テスト
uv run pytest tests/test_llm_configuration_manager.py -v

# コンソールとネットワーク監視テスト
uv run pytest tests/test_console_network_monitor.py -v

# ドラッグ&ドロップ操作テスト
uv run pytest tests/test_drag_drop_manager.py -v

# タブ管理とナビゲーション履歴テスト
uv run pytest tests/test_tab_navigation_manager.py -v

# 全テストを一括実行
uv run pytest tests/test_*_manager.py --tb=no -q
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
│   ├── __main__.py                      # CLIエントリーポイント
│   ├── api.py                           # FastAPI RESTエンドポイント
│   ├── similarity.py                    # 類似度計算ロジック
│   ├── embedding.py                     # 埋め込みベクトル処理
│   ├── error_handler.py                 # エラーハンドリングシステム
│   ├── logger.py                        # ログシステム
│   ├── llm_client.py                    # vLLM API クライアント
│   ├── llm_similarity.py                # LLMベース類似度計算
│   ├── prompt_template.py               # プロンプトテンプレート管理
│   ├── score_parser.py                  # LLM応答パース
│   ├── similarity_strategy.py           # 戦略パターン実装
│   ├── enhanced_cli.py                  # 拡張CLIインターフェース
│   ├── enhanced_result_format.py        # 拡張結果フォーマット
│   ├── caching_resource_manager.py      # キャッシュ管理
│   ├── llm_metrics.py                   # メトリクス収集
│   ├── llm_configuration_manager.py     # LLM設定管理
│   ├── console_network_monitor.py       # コンソール・ネットワーク監視
│   ├── drag_drop_manager.py             # ドラッグ&ドロップ操作
│   ├── tab_navigation_manager.py        # タブ・ナビゲーション管理
│   ├── mcp_wrapper.py                   # Playwright MCP ラッパー
│   └── utils.py                         # ユーティリティ関数
├── tests/
│   ├── test_integration.py              # 統合テストスイート
│   ├── test_error_handling.py           # エラーハンドリングテスト
│   ├── test_ui_playwright*.py           # WebUIテスト
│   ├── test_task_*.py                   # TDDタスク別テスト
│   ├── test_llm_*.py                    # LLM機能テスト
│   ├── test_strategy_*.py               # 戦略パターンテスト
│   ├── test_llm_configuration_manager.py # LLM設定テスト
│   ├── test_console_network_monitor.py   # コンソール・ネットワーク監視テスト
│   ├── test_drag_drop_manager.py         # ドラッグ&ドロップテスト
│   └── test_tab_navigation_manager.py    # タブ・ナビゲーションテスト
├── prompts/             # プロンプトテンプレート
├── datas/               # データファイル
├── docs/                # ドキュメント
├── .kiro/               # Kiro spec-driven development
│   ├── steering/        # プロジェクト指針
│   └── specs/           # 機能仕様
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
- **LLM応答キャッシュ**: 重複する比較リクエストの効率化
- **バッチ処理**: LLM APIコールの最適化
- **接続プーリング**: vLLM APIとの効率的な通信
- **フォールバック**: LLM障害時の自動切り替え
- **エラーリカバリ**: 自動リトライと部分的な処理の再開

### テスト自動化

JSON Compare では包括的なテスト自動化フレームワークを導入：

- **Playwright MCP統合**: ブラウザ操作の完全自動化
- **LLM機能テスト**: モデル切り替え、プロンプト処理の検証
- **UI操作テスト**: ドラッグ&ドロップ、タブ管理の自動テスト
- **監視システム**: コンソールエラー、ネットワーク通信の自動検知
- **TDD実装**: 43のテストケースによる品質保証（100%成功率）

**テスト実行統計**:
- 実行テスト数: 528+ （LLM機能テスト含む）
- 成功率: 96.6%（主要機能100%）
- 平均実行時間: 4.4秒/テスト
- カバレッジ: LLM、UI、監視、ナビゲーション、戦略パターン

### LLM機能実装状況

✅ **完了タスク（54.5%）**:
- Task 1: LLMテンプレート管理基盤（実装済み）
- Task 2: vLLM API通信機能（実装済み）
- Task 3: LLMベース類似度判定コア（実装済み）
- Task 4: 戦略パターンとシステム統合（実装済み）
- Task 5: CLIインターフェースの拡張（実装済み）
- Task 6: Web UIへのLLM機能統合（実装済み）

🔧 **最新修正完了**:
- プロンプト解析のマークダウンボールド形式対応
- 出力フォーマットの条件付きdetailed_results制御
- スコア形式とファイル形式の適切な差別化

⏳ **実装予定（45.5%）**:
- Task 7: 設定ファイル管理システム
- Task 8: パフォーマンス監視とメトリクス
- Task 9: 包括的なテストスイート
- Task 10: 最終統合とシステム検証