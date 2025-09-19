# Requirements Document

## Introduction
JSON Compareツールに、既存の埋め込みベースの類似度計算に加えて、vLLM APIを活用したLLMベースの意味的類似度判定機能を追加します。この新機能により、より高度なコンテキスト理解と柔軟な類似度評価基準の適用が可能となります。特に、複雑な日本語の文脈理解や、カスタムプロンプトによる評価基準の調整が可能になることで、より多様な評価ニーズに対応できるようになります。

## Requirements

### Requirement 1: LLMベース類似度判定機能
**Objective:** MLエンジニアとして、vLLM APIを使用したLLMベースの類似度判定をオプションで利用したい、より高度なコンテキスト理解に基づいた評価を行うため

#### Acceptance Criteria

1. WHEN ユーザーが `--llm` フラグを指定して実行した場合 THEN json_compare SHALL vLLM APIを使用したLLMベースの類似度判定を実行する
2. IF `--llm` フラグが指定されていない場合 THEN json_compare SHALL 既存の埋め込みベースの類似度計算を実行する
3. WHEN LLMベースの類似度判定が選択された場合 THEN json_compare SHALL 設定されたvLLMエンドポイント（http://192.168.1.18:8000/v1/chat/completions）に接続する
4. IF vLLM APIへの接続が失敗した場合 THEN json_compare SHALL エラーメッセージを表示し、埋め込みベースの計算にフォールバックするオプションを提供する
5. WHERE APIレスポンスがタイムアウト（デフォルト30秒）した場合 THE json_compare SHALL タイムアウトエラーを報告し、処理を中断する

### Requirement 2: プロンプトテンプレート管理
**Objective:** データサイエンティストとして、比較プロンプトを外部ファイルで管理・カスタマイズしたい、異なる評価基準を柔軟に適用するため

#### Acceptance Criteria

1. WHEN json_compare が起動する際 THEN システム SHALL デフォルトプロンプトファイル（prompts/default_similarity.yaml）を読み込む
2. IF ユーザーが `--prompt-file` オプションを指定した場合 THEN json_compare SHALL 指定されたファイルからプロンプトテンプレートを読み込む
3. WHEN プロンプトファイルが見つからない場合 THEN json_compare SHALL エラーメッセージを表示し、デフォルトプロンプトの使用を提案する
4. WHERE プロンプトファイルのフォーマットが不正な場合 THE json_compare SHALL 詳細なエラーメッセージと正しいフォーマットの例を表示する
5. WHEN プロンプトテンプレートが読み込まれた場合 THEN json_compare SHALL `{text1}`, `{text2}` プレースホルダーを実際の比較対象テキストで置換する

### Requirement 3: モデル選択と設定
**Objective:** システム管理者として、使用するLLMモデルと生成パラメータを設定したい、環境に応じた最適な設定を適用するため

#### Acceptance Criteria

1. WHEN LLMベースの類似度判定を使用する場合 THEN json_compare SHALL デフォルトでqwen3-14b-awqモデルを使用する
2. IF ユーザーが `--model` オプションを指定した場合 THEN json_compare SHALL 指定されたモデル名をvLLM APIリクエストに使用する
3. WHEN ユーザーが `--temperature` オプションを指定した場合 THEN json_compare SHALL 指定された温度パラメータ（0.0-1.0）をAPI呼び出しに適用する
4. IF ユーザーが `--max-tokens` オプションを指定した場合 THEN json_compare SHALL 指定された最大トークン数をAPI呼び出しに設定する
5. WHERE 環境変数 `VLLM_API_URL` が設定されている場合 THE json_compare SHALL その値をAPIエンドポイントとして使用する

### Requirement 4: 類似度スコア変換
**Objective:** データアナリストとして、LLMの回答を定量的な類似度スコアとして取得したい、既存システムとの互換性を保つため

#### Acceptance Criteria

1. WHEN LLMがテキストの類似度を評価した場合 THEN json_compare SHALL LLMの回答から0-1の数値スコアを抽出する
2. IF LLMの回答に数値スコアが含まれない場合 THEN json_compare SHALL 回答内容に基づいて自動的にスコアを推定する
3. WHEN LLMが「完全一致」「非常に類似」「類似」「やや類似」「低い類似度」のカテゴリで回答した場合 THEN json_compare SHALL 各カテゴリに対応する数値スコア（1.0, 0.8, 0.6, 0.4, 0.2）に変換する
4. WHERE LLMの回答が解析不能な場合 THE json_compare SHALL エラーとして処理し、該当行をスキップする
5. WHILE バッチ処理中 THE json_compare SHALL 各行のLLM判定結果と変換後のスコアをログに記録する

### Requirement 5: インターフェース統合
**Objective:** エンドユーザーとして、CLI、Web UI、APIのすべてのインターフェースでLLMベース類似度判定を利用したい、一貫した使用体験のため

#### Acceptance Criteria

1. WHEN Web UIでファイルをアップロードする場合 THEN システム SHALL 「LLMベース判定を使用」チェックボックスを表示する
2. IF APIリクエストに `use_llm: true` パラメータが含まれる場合 THEN API SHALL LLMベースの類似度判定を実行する
3. WHEN LLMベース判定が選択された場合 THEN Web UI SHALL プロンプトファイル選択オプションを表示する
4. WHERE CLIでdualコマンドを使用する場合 THE json_compare SHALL `--llm` フラグもサポートする
5. WHEN 結果が出力される場合 THEN json_compare SHALL 使用した判定方式（埋め込み/LLM）をメタデータに含める

### Requirement 6: パフォーマンスとエラーハンドリング
**Objective:** システム運用者として、LLMベース判定のパフォーマンスを監視し、エラーを適切に処理したい、安定したサービス提供のため

#### Acceptance Criteria

1. WHEN LLMベース判定を実行する場合 THEN json_compare SHALL 各APIコールの応答時間をメトリクスログに記録する
2. IF vLLM APIが5秒以内に応答しない場合 THEN json_compare SHALL プログレスバーに「LLM処理中」と表示する
3. WHEN API呼び出しが3回連続で失敗した場合 THEN json_compare SHALL 自動的に埋め込みベースモードにフォールバックする
4. WHERE レート制限エラーが発生した場合 THE json_compare SHALL 指数バックオフで自動リトライを実行する
5. WHILE 大量のファイルを処理中 THE json_compare SHALL API呼び出しを並列化せず、順次処理でレート制限を回避する

### Requirement 7: 設定ファイル管理
**Objective:** 開発者として、LLM関連の設定を一元管理したい、環境間での設定の一貫性を保つため

#### Acceptance Criteria

1. WHEN json_compare が初回実行される場合 THEN システム SHALL デフォルト設定ファイル（config/llm_config.yaml）を生成する
2. IF 設定ファイルが存在する場合 THEN json_compare SHALL ファイルから設定を読み込み、コマンドラインオプションで上書き可能にする
3. WHEN 設定ファイルに不正な値が含まれる場合 THEN json_compare SHALL 詳細なバリデーションエラーを表示する
4. WHERE 環境変数が設定されている場合 THE json_compare SHALL 環境変数 > CLIオプション > 設定ファイルの優先順位で値を適用する
5. WHEN `--save-config` フラグが指定された場合 THEN json_compare SHALL 現在の設定を設定ファイルに保存する

### Requirement 8: 比較方法の明示的識別と結果差別化
**Objective:** データサイエンティストとして、LLMベースと埋め込みベースの比較結果を明確に区別したい、同一データで異なる手法が同じ結果を出力する問題を解決するため

#### Acceptance Criteria

1. WHEN 類似度計算を実行する場合 THEN json_compare SHALL 出力結果に使用した比較手法を明示する `comparison_method` フィールドを含める（値："embedding" または "llm"）
2. IF LLMベース判定と埋め込みベース判定を同一データで実行した場合 THEN システム SHALL 異なるスコア値を生成することを保証する
3. WHEN LLMベース判定を使用する場合 THEN システム SHALL 追加のメタデータを出力に含める：
   - `llm_model_name`: 使用したLLMモデル名
   - `prompt_template`: 使用したプロンプトテンプレート名
   - `llm_response_time`: LLM API応答時間（秒）
   - `llm_raw_response`: LLMの生の応答テキスト（デバッグ用）
4. WHERE 埋め込みベース判定を使用する場合 THE システム SHALL 対応するメタデータを出力に含める：
   - `embedding_model_name`: 使用した埋め込みモデル名
   - `similarity_algorithm`: 類似度計算アルゴリズム（例："cosine_similarity"）
   - `embedding_dimension`: 埋め込みベクトルの次元数
5. WHEN スコア値が期待範囲外（0.0未満または1.0超過）の場合 THEN システム SHALL 警告メッセージを出力し、値を0.0-1.0の範囲にクランプする

### Requirement 9: 結果検証と品質保証
**Objective:** 品質保証エンジニアとして、LLMベースと埋め込みベースの計算結果の妥当性を検証したい、システムの信頼性を保証するため

#### Acceptance Criteria

1. WHEN 完全に同一のテキストペアを比較する場合 THEN 両手法とも1.0に近いスコア（≥0.95）を出力することを保証する
2. IF 明らかに異なるテキストペア（共通語彙なし）を比較する場合 THEN 両手法とも低いスコア（≤0.3）を出力することを保証する
3. WHEN LLMベース判定でスコア抽出に失敗した場合 THEN システム SHALL エラーログに詳細情報を記録し、明示的な失敗マーカー（"PARSE_FAILED"）を出力する
4. WHERE 同一入力でLLMベースと埋め込みベースのスコア差が0.05未満の場合 THE システム SHALL 警告ログを出力し、結果妥当性の確認を促す
5. WHEN バッチ処理中にスコア値の統計的分布が異常な場合（全て同一値、極端な偏り） THEN システム SHALL 統計レポートを生成し、計算方法の確認を推奨する