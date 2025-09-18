# Requirements Document

## 概要
このドキュメントは、JSON Compare APIにHTMLフォームベースのファイルアップロード機能を追加するための要件を定義します。この機能により、WebブラウザからJSONLファイルをアップロードし、類似度計算結果をダウンロード可能な形式で取得できるようになります。これにより、技術的な知識が限定的なユーザーでもWeb UIを通じて簡単に類似度計算機能を利用できるようになり、プロダクトのアクセシビリティが大幅に向上します。

**重要な制約:** 既存コードの修正は基本的に禁止とし、新規エンドポイントとモジュールの追加により機能を実装します。

## Requirements

### Requirement 1: ファイルアップロードエンドポイント
**目的:** エンドユーザーとして、HTMLフォームからJSONLファイルをアップロードし、類似度計算を実行できるようにしたい。これにより、コマンドラインを使用せずに簡単にツールを利用できる。

#### 受け入れ基準

1. WHEN ユーザーが/uploadエンドポイントにPOSTリクエストでファイルを送信する THEN JSON Compare API SHALL multipart/form-dataとして送信されたJSONLファイルを受け入れる

2. WHEN アップロードされたファイルがJSONL形式でない THEN JSON Compare API SHALL HTTPステータス400とエラーメッセージを返す

3. IF アップロードされたファイルサイズが100MBを超える THEN JSON Compare API SHALL HTTPステータス413とファイルサイズ超過エラーを返す

4. WHEN 有効なJSONLファイルがアップロードされる THEN JSON Compare API SHALL ファイルを一時ディレクトリに保存し、既存のprocess_jsonl_file関数を呼び出す

5. WHERE アップロードが成功した場合 THE JSON Compare API SHALL 計算結果を同期的に返す

### Requirement 2: HTML UIインターフェース
**目的:** 一般ユーザーとして、シンプルで直感的なWebインターフェースからファイルをアップロードし、結果を確認したい。これにより、技術的な専門知識なしにツールを使用できる。

#### 受け入れ基準

1. WHEN ユーザーが/ui エンドポイントにアクセスする THEN JSON Compare API SHALL ファイルアップロード用のHTMLフォームページを表示する

2. IF ユーザーがファイル選択ボタンをクリックする THEN JSON Compare API SHALL .jsonl拡張子のファイルのみを選択可能にするファイルダイアログを表示する

3. WHILE ファイルがアップロード・処理中 THE JSON Compare API SHALL プログレスインジケータまたはローディング状態を表示する

4. WHEN ユーザーが出力形式（scoreまたはfile）を選択する THEN JSON Compare API SHALL 選択された形式で結果を生成する

5. WHERE GPUオプションが利用可能な環境 THE JSON Compare API SHALL GPU使用オプションをチェックボックスとして提供する

### Requirement 3: 同期処理とレスポンス
**目的:** システム管理者として、アップロードされたファイルを同期的に処理し、即座に結果を返したい。これにより、システムの複雑性を最小限に抑えられる。

#### 受け入れ基準

1. WHEN ファイル処理が開始される THEN JSON Compare API SHALL 既存のprocess_jsonl_file関数を同期的に実行する

2. WHILE 類似度計算が実行中 THE JSON Compare API SHALL HTTPコネクションを維持し、処理完了まで待機する

3. IF 処理中にエラーが発生する THEN JSON Compare API SHALL エラー詳細を含むHTTPエラーレスポンスを即座に返す

4. WHEN 処理が完了する THEN JSON Compare API SHALL 計算結果を含むHTTPレスポンスを返す

5. WHERE 処理が30秒以上経過した場合 THE JSON Compare API SHALL タイムアウトエラーを返す

### Requirement 4: 結果のダウンロード
**目的:** エンドユーザーとして、処理完了後に結果をさまざまな形式でダウンロードしたい。これにより、結果を他のシステムやワークフローで活用できる。

#### 受け入れ基準

1. WHEN ユーザーが結果のダウンロードを要求する THEN JSON Compare API SHALL 処理結果を指定された形式でダウンロード可能にする

2. IF ユーザーがJSON形式でのダウンロードを要求する THEN JSON Compare API SHALL application/jsonのContent-Typeで結果を返す

3. IF ユーザーがCSV形式でのダウンロードを要求する THEN JSON Compare API SHALL text/csvのContent-Typeで結果を返す

4. WHEN ダウンロード要求が送信される THEN JSON Compare API SHALL 適切なContent-Dispositionヘッダーを設定する

5. WHERE 結果データが存在する場合 THE JSON Compare API SHALL ファイル名に処理日時を含める

### Requirement 5: データ管理とログ
**目的:** システム管理者として、アップロードされたファイルと処理結果が適切に管理されることを確実にしたい。これにより、ディスク容量の問題を防げる。

#### 受け入れ基準

1. WHEN ファイルがアップロードされる THEN JSON Compare API SHALL ファイル内容の基本的な検証を実行する

2. WHILE 一時ファイルが保存されている THE JSON Compare API SHALL システムの一時ディレクトリを使用する

3. WHERE 処理完了から1時間経過した THE JSON Compare API SHALL 一時ファイルを自動的に削除する

4. WHEN ユーザーがファイルをアップロードする THEN JSON Compare API SHALL アップロードログ（タイムスタンプ、ファイルサイズ、処理時間）を記録する

5. IF ディスク容量が不足する THEN JSON Compare API SHALL HTTPステータス507を返す

### Requirement 6: エラーハンドリングとユーザーフィードバック
**目的:** エンドユーザーとして、エラーが発生した際に明確で実用的なフィードバックを受け取りたい。これにより、問題を迅速に解決できる。

#### 受け入れ基準

1. WHEN JSONLファイル内に無効な行がある THEN JSON Compare API SHALL 既存のjson-repair機能で自動修復を試み、修復不可能な場合は具体的な行番号とエラー内容を報告する

2. IF inference1またはinference2フィールドが欠落している THEN JSON Compare API SHALL 欠落しているフィールドと該当行を特定するエラーメッセージを返す

3. WHEN サーバーリソース（メモリ、CPU）が不足する THEN JSON Compare API SHALL HTTPステータス503と再試行推奨時間を返す

4. WHERE 処理中に予期しないエラーが発生した場合 THE JSON Compare API SHALL エラーIDを生成し、ユーザーにサポート連絡用の参照番号を提供する

5. WHILE エラーが表示される THE JSON Compare API SHALL ユーザーが取るべき次のアクション（ファイル修正、再アップロード等）を明確に示す

### Requirement 7: 既存コードとの統合
**目的:** 開発者として、既存のコードベースを保護しながら新機能を追加したい。これにより、既存機能の安定性を維持できる。

#### 受け入れ基準

1. WHEN 新しいエンドポイントを追加する THEN JSON Compare API SHALL 既存のapi.pyファイルを修正せず、新しいモジュール（例：upload.py）を作成する

2. IF 既存の処理関数を呼び出す必要がある THEN JSON Compare API SHALL __main__.pyのprocess_jsonl_file関数をインポートして使用する

3. WHILE 新機能を実装する THE JSON Compare API SHALL 既存のCLIコマンドの動作に影響を与えない

4. WHERE 設定が必要な場合 THE JSON Compare API SHALL 環境変数または新規設定ファイルを使用し、既存の設定を変更しない

5. WHEN エラーハンドリングを実装する THEN JSON Compare API SHALL 既存のエラー処理パターンと一貫性を保つ