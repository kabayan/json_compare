# Requirements Document

## はじめに

JSON Compare WebUIは、機械学習モデルの出力結果を視覚的に比較・評価するためのWebインターフェースです。本機能では、Playwright MCP (Model Context Protocol)ツールを活用し、このWebUIの包括的な自動テストシステムを構築します。これにより、UIの動作確認、レグレッションテスト、および継続的インテグレーションにおける品質保証を実現します。

## 要件

### 要件1: Playwright MCP環境の構築と管理
**目的:** テスト自動化エンジニアとして、Playwright MCPツールを使用したテスト環境を構築し、WebUIテストを効率的に実行したい。これにより、手動テストの工数を削減し、品質を向上させる。

#### 受入基準
1. WHEN テスト実行を開始する THEN テストシステム SHALL Playwright MCPツールの初期化と接続を確立する
2. IF ブラウザが未インストール THEN テストシステム SHALL mcp__playwright__browser_install を実行してブラウザをインストールする
3. WHEN テスト完了時 THEN テストシステム SHALL mcp__playwright__browser_close を実行してリソースを解放する
4. WHERE テスト実行中にエラーが発生した場合 THE テストシステム SHALL エラー詳細とスクリーンショットを記録する
5. WHILE テストスイートが実行中 THE テストシステム SHALL 各テストケースの進捗状況をログに記録する

### 要件2: ページナビゲーションと初期表示テスト
**目的:** エンドユーザーとして、WebUIの基本的なナビゲーションとページ表示が正常に動作することを検証したい。

#### 受入基準
1. WHEN mcp__playwright__browser_navigate でWebUIにアクセスした THEN テストシステム SHALL ページの正常読み込みを確認する
2. IF ポート18081でAPIサーバーが起動している THEN テストシステム SHALL http://localhost:18081/ui への接続を確立する
3. WHEN ページが読み込まれた THEN テストシステム SHALL mcp__playwright__browser_snapshot を使用してページ構造を検証する
4. WHERE 404エラーやネットワークエラーが発生した場合 THE テストシステム SHALL エラーを記録し、テストを失敗とマークする
5. WHEN ページのリサイズが必要な場合 THEN テストシステム SHALL mcp__playwright__browser_resize を使用して適切なビューポートサイズを設定する

### 要件3: ファイルアップロード機能のテスト
**目的:** ユーザーとして、JSONLファイルのアップロードと処理が正常に動作することを確認したい。

#### 受入基準
1. WHEN 単一JSONLファイルをアップロードする THEN テストシステム SHALL mcp__playwright__browser_file_upload を使用してファイルを選択する
2. IF 2ファイル比較モードが選択されている THEN テストシステム SHALL 2つのファイルフィールドにそれぞれファイルをアップロードする
3. WHILE ファイル処理中 THE テストシステム SHALL mcp__playwright__browser_wait_for を使用して処理完了を待機する
4. WHEN 無効なファイル形式がアップロードされた THEN テストシステム SHALL エラーメッセージの表示を確認する
5. WHERE ファイルサイズが100MBを超える場合 THE テストシステム SHALL 適切なエラーハンドリングを検証する

### 要件4: フォーム入力とUIインタラクションテスト
**目的:** ユーザーとして、すべてのフォーム要素とUIコントロールが正しく機能することを検証したい。

#### 受入基準
1. WHEN フォームフィールドに値を入力する THEN テストシステム SHALL mcp__playwright__browser_type を使用して文字入力をシミュレートする
2. IF 複数のフォームフィールドが存在する THEN テストシステム SHALL mcp__playwright__browser_fill_form を使用して一括入力する
3. WHEN ドロップダウンメニューを操作する THEN テストシステム SHALL mcp__playwright__browser_select_option を使用してオプションを選択する
4. WHERE チェックボックスやラジオボタンが存在する場合 THE テストシステム SHALL mcp__playwright__browser_click を使用して選択状態を変更する
5. WHEN フォームを送信する THEN テストシステム SHALL submitボタンのクリックと送信処理を検証する

### 要件5: 比較結果の表示とダウンロード機能テスト
**目的:** ユーザーとして、比較結果が正しく表示され、各種形式でダウンロードできることを確認したい。

#### 受入基準
1. WHEN 比較処理が完了した THEN テストシステム SHALL mcp__playwright__browser_evaluate を使用して結果要素の存在を確認する
2. IF スコアサマリーが表示される THEN テストシステム SHALL 数値の妥当性と書式を検証する
3. WHEN CSV形式でダウンロードする THEN テストシステム SHALL ダウンロードリンクのクリックとファイル生成を確認する
4. WHERE エラーが発生した場合 THE テストシステム SHALL エラーメッセージとエラーIDの表示を検証する
5. WHILE 大量データを処理中 THE テストシステム SHALL プログレスバーの表示と更新を確認する

### 要件6: LLMモード特有の機能テスト
**目的:** ユーザーとして、LLMベースの比較機能が正しく動作することを検証したい。

#### 受入基準
1. WHEN LLMモードを選択する THEN テストシステム SHALL モデル選択オプションの表示を確認する
2. IF カスタムプロンプトテンプレートをアップロードする THEN テストシステム SHALL YAMLファイルの受け入れと反映を検証する
3. WHERE vLLM APIが利用不可能な場合 THE テストシステム SHALL 適切なエラーメッセージとフォールバック動作を確認する
4. WHEN LLM処理が実行される THEN テストシステム SHALL タイムアウト設定とキャンセル機能を検証する
5. WHILE LLM処理中 THE テストシステム SHALL メトリクス（トークン数、処理時間）の表示を確認する

### 要件7: コンソールエラーとネットワーク監視
**目的:** 開発者として、WebUIの実行中にコンソールエラーや異常なネットワーク通信がないことを確認したい。

#### 受入基準
1. WHILE テスト実行中 THE テストシステム SHALL mcp__playwright__browser_console_messages を使用してコンソールメッセージを監視する
2. WHEN JavaScriptエラーが発生した THEN テストシステム SHALL エラー内容を記録し、テストを失敗とマークする
3. IF ネットワークリクエストが発生する THEN テストシステム SHALL mcp__playwright__browser_network_requests を使用してリクエストを記録する
4. WHERE APIエンドポイントへのリクエストが失敗した場合 THE テストシステム SHALL HTTPステータスコードとエラー内容を記録する
5. WHEN 予期しないダイアログが表示された THEN テストシステム SHALL mcp__playwright__browser_handle_dialog を使用して処理する

### 要件8: レスポンシブデザインとブラウザ互換性テスト
**目的:** ユーザーとして、異なる画面サイズとブラウザ環境でWebUIが正しく動作することを確認したい。

#### 受入基準
1. WHEN 異なる画面サイズでテストを実行する THEN テストシステム SHALL mcp__playwright__browser_resize を使用して各サイズでの表示を検証する
2. IF モバイルビューポートサイズが設定された THEN テストシステム SHALL レスポンシブレイアウトの適用を確認する
3. WHERE ドラッグ&ドロップ機能が存在する場合 THE テストシステム SHALL mcp__playwright__browser_drag を使用して動作を検証する
4. WHEN ホバーエフェクトが存在する THEN テストシステム SHALL mcp__playwright__browser_hover を使用して表示を確認する
5. WHILE ページ遷移が発生する場合 THE テストシステム SHALL mcp__playwright__browser_navigate_back を使用して履歴管理を検証する

### 要件9: テスト結果レポートとCI/CD統合
**目的:** 開発チームとして、テスト結果を追跡し、CI/CDパイプラインに統合したい。

#### 受入基準
1. WHEN テストスイートが完了した THEN テストシステム SHALL 詳細なテストレポートを生成する
2. IF テストが失敗した THEN テストシステム SHALL mcp__playwright__browser_take_screenshot を使用して失敗時点のスクリーンショットを保存する
3. WHERE CI環境で実行される場合 THE テストシステム SHALL JUnit形式のレポートを出力する
4. WHEN パフォーマンス計測が必要な場合 THEN テストシステム SHALL ページロード時間とAPI応答時間を記録する
5. WHILE 複数のテストケースが実行される場合 THE テストシステム SHALL 並列実行をサポートする

### 要件10: タブ管理とマルチウィンドウテスト
**目的:** ユーザーとして、複数タブやウィンドウでの操作が正しく動作することを確認したい。

#### 受入基準
1. WHEN 新しいタブが開かれる THEN テストシステム SHALL mcp__playwright__browser_tabs を使用してタブ管理を行う
2. IF 複数のタブが開いている THEN テストシステム SHALL タブ間の切り替えと状態管理を検証する
3. WHERE 外部リンクが新しいタブで開く場合 THE テストシステム SHALL タブの作成と内容を確認する
4. WHEN タブを閉じる操作を行う THEN テストシステム SHALL 適切なリソース解放を確認する
5. WHILE タブ間でデータを共有する場合 THE テストシステム SHALL セッションストレージとローカルストレージの動作を検証する