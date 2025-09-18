# JSONLフォーマット修正ツール

## 概要
複数行にまたがるJSONオブジェクトを含むJSONLファイルを、正しい1行1オブジェクト形式に修正するヘルパープログラムです。

## 使い方

### 単一ファイルの修正
```bash
python3 fix_jsonl_format.py data.jsonl
```

### ディレクトリ内のすべてのJSONLファイルを修正
```bash
python3 fix_jsonl_format.py --dir ./datas
```

### サブディレクトリも含めて修正
```bash
python3 fix_jsonl_format.py --dir . --recursive
```

### ドライラン（実際には修正しない）
```bash
python3 fix_jsonl_format.py --dir ./datas --dry-run
```

### ファイルの検証のみ
```bash
python3 fix_jsonl_format.py --validate data.jsonl
```

## オプション
- `--dir`: ディレクトリ内のファイルを一括処理
- `--pattern`: ファイルパターン（デフォルト: *.jsonl）
- `--recursive` または `-r`: サブディレクトリも処理
- `--output` または `-o`: 出力先ファイル（単一ファイル処理時のみ）
- `--no-backup`: バックアップを作成しない
- `--dry-run`: 実際には修正せず対象ファイルを表示
- `--validate`: JSONLファイルの検証のみ実行
- `--verbose` または `-v`: 詳細情報を出力

## 機能
- 複数行にまたがるJSONオブジェクトを自動検出
- 1行1オブジェクト形式に変換
- 日本語を含むUnicode文字を正しく処理
- 自動バックアップ作成（.bakファイル）
- 処理前後の行数表示

## 実行例

### datasディレクトリのJSONLファイルを修正
```bash
$ python3 fix_jsonl_format.py --dir datas --verbose
📂 2 個のファイルを処理します

[1/2] 処理中: classification.infer.jsonl
  ✓ オブジェクト 1 をパース（行 4）
  ✓ オブジェクト 2 をパース（行 8）
  ...
📁 バックアップ作成: classification.infer.jsonl.bak
✅ 修正完了: classification.infer.jsonl
   - 147 個のJSONオブジェクトを処理
   - 元のファイル: 588 行 → 修正後: 147 行
```

### ファイルの検証
```bash
$ python3 fix_jsonl_format.py --validate data.jsonl
✅ data.jsonl は正しいJSONL形式です
```