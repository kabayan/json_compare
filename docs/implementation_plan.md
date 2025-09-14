# 実装計画

## 目的
CLIツールとして動作するJSON比較ツールを実装する。uvxで実行可能で、シンプルな構成を維持する。

## フェーズ1: CLI基本構造（最優先）

### 1.1 エントリーポイント作成
- `src/__main__.py`を作成
- コマンドライン引数の処理（argparse使用）
- 2つのファイルパスと`--type`オプションを受け取る

### 1.2 メイン処理フロー
```python
def main():
    # 1. 引数解析
    # 2. ファイル読み込み
    # 3. 比較実行
    # 4. 結果出力
```

## フェーズ2: ファイル処理

### 2.1 ローカルファイル読み込み
- JSON/JSONLファイルの読み込み
- エラーハンドリング（ファイル存在確認）

### 2.2 外部API連携（オプション）
- URLが指定された場合の処理
- 192.168.1.24:28080のAPIを使用
- 最小限の実装のみ

## フェーズ3: 結果出力

### 3.1 scoreタイプ出力
- JSON形式で標準出力に出力（全体の平均値を1行で）
- 必須フィールド: file, score, meaning, json
- scoreは全行の平均値を算出
- meaningはスコアに基づく評価

### 3.2 fileタイプ出力
- 各行の詳細を含むJSON配列を出力
- 元データに類似度情報を追加
- similarity_scoreとsimilarity_detailsフィールドを付与

## フェーズ4: パッケージ構成

### 4.1 uvx対応設定
- `pyproject.toml`作成
- 最小限の依存関係定義
  - transformers
  - torch
  - scipy
  - json-repair

### 4.2 実行可能化
```bash
# scoreタイプ（全体平均）
uvx json_compare input.jsonl --type score

# fileタイプ（各行詳細）
uvx json_compare input.jsonl --type file -o output.json
```

## 実装順序

1. **CLI基本構造**（必須）
   - argparse実装
   - エントリーポイント

2. **既存コードとの統合**（必須）
   - similarity.pyの呼び出し
   - 結果のフォーマット

3. **ファイル読み込み**（必須）
   - ローカルファイル対応
   - エラーハンドリング

4. **uvx設定**（必須）
   - pyproject.toml作成
   - 実行テスト

## 除外事項

以下は実装しない：
- APIサーバー機能（0.0.0.0:18081）
- 認証・セキュリティ機能
- 並列処理・パフォーマンス最適化
- 詳細なログ出力
- fileタイプの完全実装

## テスト計画

### 基本動作確認
1. 2つの同一JSONファイルでスコア1.0確認
2. 異なるJSONファイルでスコア計算確認
3. 不正なファイルパスでエラー確認

### コマンド例
```bash
# 基本実行
uvx json_compare test1.json test2.json --type score

# JSONLファイル
uvx json_compare data1.jsonl data2.jsonl --type score
```

## 注意事項

- GPU必須（embedding.py）
- エラー時は標準エラー出力に簡潔なメッセージ
- 複雑な機能追加は避ける
- シンプルさを最優先