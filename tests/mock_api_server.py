#!/usr/bin/env python3
"""
UIテスト用のモックAPIサーバー
実際の処理は行わず、UIの表示と動作確認のみを行う
"""

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
import json
import time
import uuid

app = FastAPI()

# HTMLテンプレート（src/api.pyから抜粋、タブ機能を含む）
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON Compare - ファイルアップロード</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
            text-align: center;
        }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            border-bottom: 2px solid #e2e8f0;
        }
        .tab-button {
            padding: 12px 24px;
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            color: #666;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 14px;
        }
        .tab-button:hover {
            color: #667eea;
        }
        .tab-button.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }
        .mode-form {
            display: none;
        }
        .mode-form.active {
            display: block;
        }
        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
            margin-bottom: 20px;
        }
        .file-input-button {
            display: block;
            width: 100%;
            padding: 12px 20px;
            background: #f7f8fa;
            border: 2px dashed #cbd5e0;
            border-radius: 10px;
            color: #4a5568;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }
        input[type="file"] {
            position: absolute;
            left: -9999px;
        }
        .submit-button {
            width: 100%;
            padding: 14px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 10px;
        }
        .result-container {
            display: none;
            margin-top: 30px;
            padding: 20px;
            background: #f7f8fa;
            border-radius: 10px;
        }
        .result-container.active {
            display: block;
        }
        .file-inputs-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        input[type="text"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 14px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 JSON Compare</h1>
        <p style="text-align:center;margin-bottom:20px;color:#666;">JSONLファイルの類似度を計算します</p>

        <!-- タブナビゲーション -->
        <div class="tabs">
            <button class="tab-button active" data-mode="single" onclick="switchMode('single')">
                📄 単一ファイル比較
            </button>
            <button class="tab-button" data-mode="dual" onclick="switchMode('dual')">
                📑 2ファイル比較
            </button>
        </div>

        <!-- 単一ファイルモード -->
        <form id="uploadForm" class="mode-form active" data-mode="single">
            <div class="file-input-wrapper">
                <label for="file" class="file-input-button" id="fileLabel">
                    📁 クリックしてファイルを選択（.jsonl）
                </label>
                <input type="file" id="file" name="file" accept=".jsonl">
            </div>
            <button type="submit" class="submit-button" id="submitButton">
                📊 類似度を計算
            </button>
        </form>

        <!-- 2ファイル比較モード -->
        <form id="dualForm" class="mode-form" data-mode="dual">
            <div class="file-inputs-row">
                <div class="file-input-wrapper">
                    <label for="file1" class="file-input-button" id="file1Label">
                        📁 1つ目のファイル
                    </label>
                    <input type="file" id="file1" name="file1" accept=".jsonl">
                </div>
                <div class="file-input-wrapper">
                    <label for="file2" class="file-input-button" id="file2Label">
                        📁 2つ目のファイル
                    </label>
                    <input type="file" id="file2" name="file2" accept=".jsonl">
                </div>
            </div>
            <input type="text" id="column" name="column" placeholder="比較する列名" value="inference">
            <button type="submit" class="submit-button" id="dualSubmitButton">
                🔀 2ファイルの列を比較
            </button>
        </form>

        <div class="result-container" id="resultContainer">
            <h3 id="resultTitle">処理結果</h3>
            <pre id="resultContent" style="white-space:pre-wrap;"></pre>
        </div>
    </div>

    <script>
        function switchMode(mode) {
            // タブボタンの切り替え
            document.querySelectorAll('.tab-button').forEach(btn => {
                if (btn.dataset.mode === mode) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // フォームの切り替え
            document.querySelectorAll('.mode-form').forEach(form => {
                if (form.dataset.mode === mode) {
                    form.classList.add('active');
                } else {
                    form.classList.remove('active');
                }
            });

            // 結果をクリア
            document.getElementById('resultContainer').classList.remove('active');
        }

        // 単一ファイルフォームの送信処理
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resultContainer = document.getElementById('resultContainer');
            const resultTitle = document.getElementById('resultTitle');
            const resultContent = document.getElementById('resultContent');

            // モック結果を表示
            resultTitle.textContent = '✅ 処理完了（モック）';
            resultContent.textContent = JSON.stringify({
                "score": 0.8567,
                "meaning": "非常に類似",
                "total_lines": 10,
                "_metadata": {
                    "mode": "single",
                    "test": true
                }
            }, null, 2);
            resultContainer.classList.add('active');
        });

        // 2ファイルフォームの送信処理
        document.getElementById('dualForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resultContainer = document.getElementById('resultContainer');
            const resultTitle = document.getElementById('resultTitle');
            const resultContent = document.getElementById('resultContent');

            // モック結果を表示
            resultTitle.textContent = '✅ 2ファイル比較完了（モック）';
            resultContent.textContent = JSON.stringify({
                "score": 0.7234,
                "meaning": "類似",
                "total_lines": 20,
                "_metadata": {
                    "mode": "dual",
                    "column_compared": document.getElementById('column').value,
                    "test": true
                }
            }, null, 2);
            resultContainer.classList.add('active');
        });

        // ファイル選択時の表示更新
        document.getElementById('file').addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                document.getElementById('fileLabel').textContent = '✅ ' + this.files[0].name;
            }
        });

        document.getElementById('file1').addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                document.getElementById('file1Label').textContent = '✅ ' + this.files[0].name;
            }
        });

        document.getElementById('file2').addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                document.getElementById('file2Label').textContent = '✅ ' + this.files[0].name;
            }
        });
    </script>
</body>
</html>
'''


@app.get("/ui", response_class=HTMLResponse)
async def ui_page():
    """UIページを返す"""
    return HTMLResponse(content=HTML_TEMPLATE)


@app.post("/upload")
async def mock_upload(file: UploadFile = File(...)):
    """単一ファイルアップロードのモック"""
    return {
        "score": 0.8567,
        "meaning": "非常に類似",
        "total_lines": 10,
        "file": file.filename,
        "_metadata": {
            "processing_time": "0.5秒",
            "original_filename": file.filename,
            "gpu_used": False
        }
    }


@app.post("/api/compare/dual")
async def mock_dual_compare(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    column: str = Form("inference")
):
    """2ファイル比較のモック"""
    return {
        "score": 0.7234,
        "meaning": "類似",
        "total_lines": 20,
        "_metadata": {
            "source_files": {
                "file1": file1.filename,
                "file2": file2.filename
            },
            "column_compared": column,
            "rows_compared": 20,
            "gpu_used": False
        }
    }


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "cli_available": True}


if __name__ == "__main__":
    import uvicorn
    print("モックAPIサーバーを起動します（ポート: 18082）")
    uvicorn.run(app, host="0.0.0.0", port=18082)