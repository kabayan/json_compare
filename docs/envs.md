## ファイル保存・フォーマット変換api

### 保存
curl -X POST http://192.168.1.24:28080/file_upload/  -F "file=@data.json"

### 変換とダウンロード
curl "http://192.168.1.24:28080/download/?format=json" -o output.json

### 対応形式
- `csv` - CSV形式
- `json` - JSON形式
- `jsonl` - JSONL形式（行区切りJSON）
- `xlsx` - Excel形式
- `yaml` - YAML形式
- `huggingface` - Parquet形式（HuggingFace datasets互換