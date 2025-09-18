# タスクリスト: dual-file-inference-compare

## タスク概要
2つのJSONLファイルから指定された列（デフォルト: inference）を抽出し、比較するための機能実装。既存コードを一切変更せず、前処理層のみで実現する。

## タスクリスト

### タスク 1: DualFileExtractorクラスの実装
- [x] **ファイル**: `src/dual_file_extractor.py` (新規作成)
- **説明**: 2ファイルから列を抽出し、一時ファイルを生成して既存機能を呼び出すクラス
- **実装内容**:
  - `compare_dual_files()`メソッド: メインの比較処理
  - `_extract_column()`メソッド: 指定列の抽出
  - `_create_temp_file()`メソッド: 一時ファイル生成
  - `_cleanup_temp_file()`メソッド: 一時ファイル削除
- **要件**: R2（Inference列の抽出と中間ファイル生成）
- **_Prompt**:
  実装タスク（spec: dual-file-inference-compare）。既存のprocess_jsonl_file関数を変更せずに、2つのJSONLファイルから指定列を抽出し一時ファイルを作成するDualFileExtractorクラスを実装。tempfileモジュールで安全な一時ファイル管理を行い、json形式でinference1/inference2として出力。エラーハンドリングとログ出力を含む。制約: 既存コードの変更は禁止。成功基準: 2ファイルの指定列を正しく抽出し、一時ファイル経由でprocess_jsonl_fileが実行できること。
- **_Leverage**: `src/similarity.py`のprocess_jsonl_file関数、`src/logger.py`、`src/error_handler.py`

### タスク 2: CLIコマンドの追加
- [x] **ファイル**: `src/__main__.py` (既存ファイル更新)
- **説明**: 2ファイル比較用の新しいCLIコマンド`dual`を追加
- **実装内容**:
  - `@app.command("dual")`デコレータで新コマンド定義
  - file1, file2, column, type, gpu, outputパラメータ
  - DualFileExtractorの呼び出し
  - 結果の出力処理
- **要件**: R3（CLIインターフェース）
- **_Prompt**:
  実装タスク（spec: dual-file-inference-compare）。既存のCLI（__main__.py）にdualコマンドを追加。2つのJSONLファイルと列名（デフォルト:inference）を引数に取り、DualFileExtractorを使用して比較実行。Typerを使用し、既存コマンド構造に準拠。制約: 既存のcompareコマンドは変更しない。成功基準: `json_compare dual file1.jsonl file2.jsonl --column inference`が正しく実行できること。
- **_Leverage**: 既存の`src/__main__.py`の構造、Typerライブラリ

### タスク 3: APIエンドポイントの追加
- [x] **ファイル**: `src/api.py` (既存ファイル更新)
- **説明**: 2ファイル比較用の`/api/compare/dual`エンドポイント追加
- **実装内容**:
  - POSTエンドポイント定義
  - 2つのファイルアップロード処理
  - column, type, gpuパラメータ処理
  - DualFileExtractorの非同期実行
  - 一時ファイルのクリーンアップ
- **要件**: R5（REST APIインターフェース）
- **_Prompt**:
  実装タスク（spec: dual-file-inference-compare）。FastAPI（api.py）に/api/compare/dualエンドポイントを追加。2つのUploadFileを受け取り、DualFileExtractorで処理。asyncio.run_in_executorで同期処理を非同期実行。制約: 既存の/uploadエンドポイントは変更しない。成功基準: multipart/form-dataで2ファイルをアップロードし、比較結果が取得できること。
- **_Leverage**: 既存の`upload_file`関数の構造、`save_upload_file`関数

### タスク 4: Web UIの更新
- [x] **ファイル**: `src/api.py`内のHTMLテンプレート (既存ファイル更新)
- **説明**: 2ファイルアップロード用のUIフォーム追加
- **実装内容**:
  - 2つのファイル入力フィールド
  - 列名入力フィールド（デフォルト: inference）
  - 既存のtype/GPUオプション
  - JavaScriptでの2ファイル処理
  - 結果表示とダウンロード機能
- **要件**: R4（Web UIインターフェース）
- **_Prompt**:
  実装タスク（spec: dual-file-inference-compare）。Web UI（api.py内のHTML）に2ファイル比較機能を追加。タブまたはモード切替で1ファイル/2ファイル比較を選択。FormDataで2ファイルと列名を送信。制約: 既存の1ファイル比較UIは保持。成功基準: UIから2ファイルをアップロードし、比較結果が表示・ダウンロードできること。
- **_Leverage**: 既存のHTML_TEMPLATEの構造とJavaScript

### タスク 5: テストの追加
- [x] **ファイル**: `tests/test_dual_file_extractor.py` (新規作成)
- **説明**: DualFileExtractorの単体テストと統合テスト
- **実装内容**:
  - 列抽出機能のテスト
  - 一時ファイル生成・削除のテスト
  - エラーケースのテスト（ファイル不存在、列欠落）
  - CLI/API経由の統合テスト
- **要件**: R7（エラー処理とロギング）
- **_Prompt**:
  実装タスク（spec: dual-file-inference-compare）。DualFileExtractorとその統合のテストスイートを作成。pytestを使用し、正常系・異常系をカバー。一時ファイルの作成と削除、列の不存在、ファイル行数の不一致などをテスト。制約: 既存のテストに影響を与えない。成功基準: すべてのテストがパスし、カバレッジ80%以上。
- **_Leverage**: 既存のテストファイル構造、pytestフレームワーク

### タスク 6: ドキュメントの更新
- [x] **ファイル**: `README.md` (既存ファイル更新)
- **説明**: 2ファイル比較機能のドキュメント追加
- **実装内容**:
  - CLIコマンドの使用例
  - APIエンドポイントの説明
  - Web UIでの操作方法
  - 入力ファイル形式の説明
- **要件**: すべての要件
- **_Prompt**:
  実装タスク（spec: dual-file-inference-compare）。README.mdに2ファイル比較機能のドキュメントを追加。CLIコマンド（dual）、APIエンドポイント（/api/compare/dual）、Web UIの使用方法を記載。列名パラメータの説明を含む。制約: 既存のドキュメント構造を維持。成功基準: ユーザーがドキュメントを読んで機能を使用できること。
- **_Leverage**: 既存のREADME.md構造

## 実装順序
1. タスク1: DualFileExtractorクラス（基盤）
2. タスク2: CLIコマンド（最もシンプル）
3. タスク3: APIエンドポイント（CLIの拡張）
4. タスク4: Web UI（APIを利用）
5. タスク5: テスト（全機能の検証）
6. タスク6: ドキュメント（最終確認）

## 成功基準
- 既存コードを一切変更せずに機能を実装
- 2つのJSONLファイルから指定列を抽出して比較可能
- CLI、API、Web UIの3つのインターフェースから利用可能
- 列名をパラメータで指定可能（デフォルト: inference）
- エラー時の適切なメッセージ表示とクリーンアップ