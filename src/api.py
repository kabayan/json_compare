#!/usr/bin/env python3
"""JSON比較ツールのAPIラッパー"""

import asyncio
import csv
import io
import json
import os
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, HTMLResponse, Response
from pydantic import BaseModel

# 既存実装から関数をインポート
from .__main__ import process_jsonl_file
from .similarity import set_gpu_mode


app = FastAPI(
    title="JSON Compare API",
    description="JSON形式のデータを意味的類似度で比較するAPI",
    version="1.0.0"
)


class CompareRequest(BaseModel):
    """比較リクエストのモデル"""
    file1: str
    file2: Optional[str] = None
    type: str = "score"
    output: Optional[str] = None


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンスのモデル"""
    status: str
    cli_available: bool


@app.post("/compare")
async def compare(request: CompareRequest) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    JSONファイルを比較する

    Args:
        request: 比較リクエスト

    Returns:
        比較結果（scoreまたはfile形式）

    Raises:
        HTTPException: ファイルが見つからない、処理エラーなど
    """
    try:
        # typeパラメータの検証
        if request.type not in ["score", "file"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid type parameter", "detail": "type must be 'score' or 'file'"}
            )

        # file1の存在確認
        file1_path = Path(request.file1)
        if not file1_path.exists():
            raise HTTPException(
                status_code=400,
                detail={"error": "File not found", "detail": f"入力ファイルが見つかりません: {request.file1}"}
            )

        # file2が指定された場合の処理（現在の実装ではfile1内のinference1/2を比較）
        if request.file2:
            # 将来の拡張用プレースホルダー
            # 現在はfile1内のinference1とinference2を比較する仕様
            pass

        # process_jsonl_file関数を呼び出し
        result = process_jsonl_file(request.file1, request.type)

        # outputパラメータが指定された場合はファイルに保存
        if request.output:
            output_path = Path(request.output)

            # 親ディレクトリが存在しない場合は作成
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 結果をファイルに保存
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            # ファイル保存時のレスポンス
            return {
                "message": f"結果を {request.output} に保存しました",
                "output_path": str(output_path.absolute())
            }

        # 通常のレスポンス
        return result

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "File not found", "detail": str(e)}
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "JSON parse error", "detail": f"JSONパースエラー: {str(e)}"}
        )
    except Exception as e:
        # その他のエラー
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(e)}
        )


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    type: str = Form("score"),
    gpu: bool = Form(False)
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    ファイルをアップロードして類似度計算を実行する

    Args:
        file: アップロードされたJSONLファイル
        type: 出力タイプ（"score" または "file"）
        gpu: GPU使用フラグ

    Returns:
        比較結果（scoreまたはfile形式）

    Raises:
        HTTPException: ファイルバリデーションエラー、処理エラーなど
    """
    try:
        # typeパラメータの検証
        if type not in ["score", "file"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid type parameter", "detail": "type must be 'score' or 'file'"}
            )

        # 基本的なファイル情報の確認
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail={"error": "No file provided", "detail": "ファイルが選択されていません"}
            )

        # ファイル拡張子の検証
        if not file.filename.lower().endswith('.jsonl'):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid file type",
                    "detail": "JSONLファイル(.jsonl拡張子)のみサポートされています"
                }
            )

        # ファイルサイズの確認（100MB制限）
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "File too large",
                    "detail": f"ファイルサイズが制限（100MB）を超えています: {len(file_content) / (1024*1024):.1f}MB"
                }
            )

        # ファイルポインタをリセット
        await file.seek(0)

        # 基本的なJSONL構造の検証
        try:
            # ファイル内容を文字列として読み取り
            content = file_content.decode('utf-8')
            lines = content.strip().split('\n')

            if not lines or lines == ['']:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Empty file",
                        "detail": "ファイルが空です"
                    }
                )

            # 最初の数行をJSONとして検証
            for i, line in enumerate(lines[:5]):  # 最初の5行を検証
                if line.strip():
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "Invalid JSON format",
                                "detail": f"行 {i+1} でJSONパースエラー: {str(e)}"
                            }
                        )

        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid encoding",
                    "detail": "ファイルはUTF-8エンコーディングである必要があります"
                }
            )

        # 一時ファイルの作成と保存
        temp_dir = tempfile.gettempdir()
        unique_id = str(uuid.uuid4())
        temp_filename = f"json_compare_{unique_id}.jsonl"
        temp_filepath = os.path.join(temp_dir, temp_filename)

        temp_file_created = False
        try:
            # 一時ファイルに内容を保存
            with open(temp_filepath, 'wb') as f:
                f.write(file_content)
            temp_file_created = True

            # GPUモードの設定
            if gpu:
                set_gpu_mode(True)
            else:
                set_gpu_mode(False)

            # タイムアウト付きで処理を実行（30秒制限）
            start_time = time.time()

            try:
                # 非同期関数内で同期関数を実行
                # asyncio.to_threadを使用して別スレッドで実行
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, process_jsonl_file, temp_filepath, type),
                    timeout=60.0  # Increased timeout for model loading
                )

                processing_time = time.time() - start_time

                # メタデータを追加
                if isinstance(result, dict):
                    result["_metadata"] = {
                        "processing_time": f"{processing_time:.2f}秒",
                        "original_filename": file.filename,
                        "gpu_used": gpu
                    }

                return result

            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": "Processing timeout",
                        "detail": "処理が60秒以内に完了しませんでした。より小さいファイルで再試行してください。"
                    }
                )
            except MemoryError:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "Insufficient memory",
                        "detail": "メモリ不足により処理を完了できませんでした。"
                    }
                )

        except OSError as e:
            # ディスク容量不足などのOSエラー
            if temp_file_created and os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass  # クリーンアップ失敗は無視

            raise HTTPException(
                status_code=507,
                detail={
                    "error": "Insufficient storage",
                    "detail": f"一時ファイルの作成に失敗しました: {str(e)}"
                }
            )

        finally:
            # 一時ファイルのクリーンアップ（処理完了後）
            # 注意: 実際の処理実装時はprocess_jsonl_file完了後にクリーンアップ
            if temp_file_created and os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass  # クリーンアップ失敗をログに記録（本来はloggingを使用）

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        # その他のエラー
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error", "detail": str(e)}
        )


@app.get("/ui", response_class=HTMLResponse)
async def ui_form():
    """
    ファイルアップロード用のWebインターフェース

    Returns:
        HTMLフォームページ
    """
    html_content = '''
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

        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }

        .form-group {
            margin-bottom: 25px;
        }

        label {
            display: block;
            color: #555;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }

        .file-input-wrapper {
            position: relative;
            overflow: hidden;
            display: inline-block;
            width: 100%;
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

        .file-input-button:hover {
            background: #edf2f7;
            border-color: #a0aec0;
        }

        input[type="file"] {
            position: absolute;
            left: -9999px;
        }

        .file-selected {
            background: #f0fff4;
            border-color: #48bb78;
            color: #22543d;
        }

        select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 14px;
            color: #333;
            background: white;
            cursor: pointer;
            transition: border-color 0.3s ease;
        }

        select:focus {
            outline: none;
            border-color: #667eea;
        }

        .checkbox-wrapper {
            display: flex;
            align-items: center;
            padding: 12px 15px;
            background: #f7f8fa;
            border-radius: 10px;
        }

        input[type="checkbox"] {
            width: 18px;
            height: 18px;
            margin-right: 10px;
            cursor: pointer;
        }

        .checkbox-label {
            cursor: pointer;
            user-select: none;
            font-size: 14px;
            color: #555;
            flex: 1;
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
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            margin-top: 10px;
        }

        .submit-button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px -5px rgba(102, 126, 234, 0.4);
        }

        .submit-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .loading {
            display: none;
            text-align: center;
            margin-top: 30px;
        }

        .loading.active {
            display: block;
        }

        .spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f4f6;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .loading-text {
            color: #666;
            margin-top: 15px;
            font-size: 14px;
        }

        .result-container {
            display: none;
            margin-top: 30px;
            padding: 20px;
            background: #f7f8fa;
            border-radius: 10px;
            border-left: 4px solid #48bb78;
        }

        .result-container.active {
            display: block;
        }

        .result-container.error {
            border-left-color: #f56565;
            background: #fff5f5;
        }

        .result-title {
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
        }

        .result-content {
            font-size: 14px;
            color: #555;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            background: white;
            padding: 15px;
            border-radius: 8px;
            max-height: 400px;
            overflow-y: auto;
        }

        .download-buttons {
            margin-top: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .download-button {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            text-decoration: none;
            transition: transform 0.2s, box-shadow 0.2s;
            font-weight: 600;
            font-size: 14px;
            flex: 1;
            text-align: center;
            min-width: 200px;
        }

        .download-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        }

        .csv-button {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        }

        .csv-button:hover {
            box-shadow: 0 10px 25px rgba(72, 187, 120, 0.3);
        }

        @media (max-width: 640px) {
            .container {
                padding: 30px 20px;
            }

            h1 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 JSON Compare</h1>
        <p class="subtitle">JSONLファイルの類似度を計算します</p>

        <form id="uploadForm" enctype="multipart/form-data">
            <div class="form-group">
                <label for="file">JSONLファイルを選択</label>
                <div class="file-input-wrapper">
                    <label for="file" class="file-input-button" id="fileLabel">
                        📁 クリックしてファイルを選択（.jsonl）
                    </label>
                    <input type="file" id="file" name="file" accept=".jsonl" required>
                </div>
            </div>

            <div class="form-group">
                <label for="type">出力形式</label>
                <select id="type" name="type">
                    <option value="score">スコア（全体平均）</option>
                    <option value="file">ファイル（詳細結果）</option>
                </select>
            </div>

            <div class="form-group">
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="gpu" name="gpu" value="true">
                    <label for="gpu" class="checkbox-label">GPU を使用する（高速処理）</label>
                </div>
            </div>

            <button type="submit" class="submit-button" id="submitButton">
                📊 類似度を計算
            </button>
        </form>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p class="loading-text">処理中... しばらくお待ちください</p>
        </div>

        <div class="result-container" id="resultContainer">
            <h3 class="result-title" id="resultTitle">処理結果</h3>
            <pre class="result-content" id="resultContent"></pre>
            <div class="download-buttons" id="downloadButtons" style="display: none;">
                <a href="#" class="download-button" id="downloadJsonButton">
                    📄 JSON形式でダウンロード
                </a>
                <a href="#" class="download-button csv-button" id="downloadCsvButton">
                    📊 CSV形式でダウンロード
                </a>
            </div>
        </div>
    </div>

    <script>
        const form = document.getElementById('uploadForm');
        const fileInput = document.getElementById('file');
        const fileLabel = document.getElementById('fileLabel');
        const loading = document.getElementById('loading');
        const submitButton = document.getElementById('submitButton');
        const resultContainer = document.getElementById('resultContainer');
        const resultTitle = document.getElementById('resultTitle');
        const resultContent = document.getElementById('resultContent');
        const downloadButtons = document.getElementById('downloadButtons');
        const downloadJsonButton = document.getElementById('downloadJsonButton');
        const downloadCsvButton = document.getElementById('downloadCsvButton');
        let lastResult = null;
        let lastType = 'score';

        // ファイル選択時の表示更新
        fileInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                const fileName = this.files[0].name;
                fileLabel.textContent = `✅ ${fileName}`;
                fileLabel.classList.add('file-selected');
            } else {
                fileLabel.textContent = '📁 クリックしてファイルを選択（.jsonl）';
                fileLabel.classList.remove('file-selected');
            }
        });

        // フォーム送信処理
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(form);

            // チェックボックスの値を調整
            if (!document.getElementById('gpu').checked) {
                formData.set('gpu', 'false');
            }

            // UI状態の更新
            submitButton.disabled = true;
            loading.classList.add('active');
            resultContainer.classList.remove('active');

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    // 成功時の処理
                    lastResult = data;
                    resultTitle.textContent = '✅ 処理完了';
                    resultContent.textContent = JSON.stringify(data, null, 2);
                    resultContainer.classList.remove('error');
                    resultContainer.classList.add('active');

                    // ダウンロードボタンの設定
                    lastType = formData.get('type');
                    downloadButtons.style.display = 'flex';

                    // JSONダウンロードボタン
                    const jsonBlob = new Blob([JSON.stringify(data, null, 2)],
                                         { type: 'application/json' });
                    const jsonUrl = URL.createObjectURL(jsonBlob);
                    downloadJsonButton.href = jsonUrl;
                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
                    downloadJsonButton.download = `result_${timestamp}.json`;

                    // CSVダウンロードボタン - CSVへの変換をクライアントサイドで実装
                    downloadCsvButton.onclick = async (e) => {
                        e.preventDefault();
                        const csvContent = convertToCSV(data, lastType);
                        const csvBlob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                        const csvUrl = URL.createObjectURL(csvBlob);
                        const a = document.createElement('a');
                        a.href = csvUrl;
                        a.download = `result_${timestamp}.csv`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(csvUrl);
                    };

                } else {
                    // エラー時の処理
                    resultTitle.textContent = '❌ エラーが発生しました';
                    resultContent.textContent = data.detail ?
                        `${data.detail.error}: ${data.detail.detail}` :
                        JSON.stringify(data, null, 2);
                    resultContainer.classList.add('error');
                    resultContainer.classList.add('active');
                    downloadButtons.style.display = 'none';
                }
            } catch (error) {
                // ネットワークエラーなど
                resultTitle.textContent = '❌ 通信エラー';
                resultContent.textContent = `エラー: ${error.message}`;
                resultContainer.classList.add('error');
                resultContainer.classList.add('active');
                downloadButtons.style.display = 'none';
            } finally {
                loading.classList.remove('active');
                submitButton.disabled = false;
            }
        });

        // CSV変換関数
        function convertToCSV(data, type) {
            let csv = '';

            if (type === 'score') {
                // スコアモードの場合
                csv = '項目,値\\n';
                if (data.overall_similarity !== undefined) {
                    csv += `全体類似度,${data.overall_similarity.toFixed(4)}\\n`;
                }
                if (data.statistics) {
                    const stats = data.statistics;
                    csv += `平均類似度,${(stats.mean || 0).toFixed(4)}\\n`;
                    csv += `中央値,${(stats.median || 0).toFixed(4)}\\n`;
                    csv += `標準偏差,${(stats.std_dev || 0).toFixed(4)}\\n`;
                    csv += `最小値,${(stats.min || 0).toFixed(4)}\\n`;
                    csv += `最大値,${(stats.max || 0).toFixed(4)}\\n`;
                }
                if (data._metadata) {
                    csv += '\\n';
                    csv += `処理時間,${data._metadata.processing_time || 'N/A'}\\n`;
                    csv += `元ファイル名,${data._metadata.original_filename || 'N/A'}\\n`;
                    csv += `GPU使用,${data._metadata.gpu_used ? '有' : '無'}\\n`;
                }
            } else if (type === 'file') {
                // ファイルモードの場合
                if (Array.isArray(data) && data.length > 0) {
                    // ヘッダー行の生成
                    const headers = [];
                    const firstItem = data[0];
                    if ('line_number' in firstItem) headers.push('行番号');
                    if ('similarity' in firstItem) headers.push('類似度');
                    if ('inference1' in firstItem) headers.push('推論1');
                    if ('inference2' in firstItem) headers.push('推論2');

                    csv = headers.join(',') + '\\n';

                    // データ行の生成
                    data.forEach(item => {
                        const row = [];
                        if ('line_number' in item) row.push(item.line_number);
                        if ('similarity' in item) row.push(item.similarity.toFixed(4));
                        if ('inference1' in item) row.push(`"${String(item.inference1).replace(/"/g, '""')}"`);
                        if ('inference2' in item) row.push(`"${String(item.inference2).replace(/"/g, '""')}"`);
                        csv += row.join(',') + '\\n';
                    });
                }
            }

            // BOMを追加（Excelでの文字化け防止）
            return '\uFEFF' + csv;
        }

        // ページロード時の初期化
        document.addEventListener('DOMContentLoaded', () => {
            fileLabel.classList.remove('file-selected');
        });
    </script>
</body>
</html>
    '''
    return HTMLResponse(content=html_content, status_code=200)


def json_to_csv(data: Union[Dict[str, Any], List[Dict[str, Any]]], type_mode: str) -> str:
    """
    JSON結果をCSV形式に変換する

    Args:
        data: 処理結果のJSONデータ
        type_mode: 出力タイプ（"score" または "file"）

    Returns:
        CSV形式の文字列
    """
    output = io.StringIO()

    if type_mode == "score":
        # スコアモードの場合：統計情報を表形式で出力
        writer = csv.writer(output)

        # ヘッダー行
        writer.writerow(["項目", "値"])

        # 基本情報（新形式対応）
        if "score" in data:
            writer.writerow(["全体スコア", f"{data['score']:.4f}"])
        elif "overall_similarity" in data:
            writer.writerow(["全体類似度", f"{data['overall_similarity']:.4f}"])

        if "meaning" in data:
            writer.writerow(["評価", data["meaning"]])

        if "total_lines" in data:
            writer.writerow(["総行数", data["total_lines"]])

        # JSON形式の詳細情報
        if "json" in data:
            json_data = data["json"]
            if "field_match_ratio" in json_data:
                writer.writerow(["フィールド一致率", f"{json_data['field_match_ratio']:.4f}"])
            if "value_similarity" in json_data:
                writer.writerow(["値の類似度", f"{json_data['value_similarity']:.4f}"])
            if "final_score" in json_data:
                writer.writerow(["最終スコア", f"{json_data['final_score']:.4f}"])

        # 統計情報（旧形式対応）
        if "statistics" in data:
            stats = data["statistics"]
            writer.writerow(["平均類似度", f"{stats.get('mean', 0):.4f}"])
            writer.writerow(["中央値", f"{stats.get('median', 0):.4f}"])
            writer.writerow(["標準偏差", f"{stats.get('std_dev', 0):.4f}"])
            writer.writerow(["最小値", f"{stats.get('min', 0):.4f}"])
            writer.writerow(["最大値", f"{stats.get('max', 0):.4f}"])

        # メタデータ
        if "_metadata" in data:
            meta = data["_metadata"]
            writer.writerow(["", ""])  # 空行
            writer.writerow(["処理時間", meta.get("processing_time", "N/A")])
            writer.writerow(["元ファイル名", meta.get("original_filename", "N/A")])
            writer.writerow(["GPU使用", "有" if meta.get("gpu_used", False) else "無"])

    elif type_mode == "file":
        # ファイルモードの場合：各行の詳細を出力
        if isinstance(data, list) and len(data) > 0:
            # データから動的にヘッダーを生成
            headers = []
            first_item = data[0]

            # 基本フィールド
            if "line_number" in first_item:
                headers.append("行番号")
            if "similarity" in first_item:
                headers.append("類似度")

            # inference1とinference2の内容
            if "inference1" in first_item:
                headers.append("推論1")
            if "inference2" in first_item:
                headers.append("推論2")

            # 追加フィールド
            for key in first_item.keys():
                if key not in ["line_number", "similarity", "inference1", "inference2", "_metadata"]:
                    headers.append(key)

            writer = csv.writer(output)
            writer.writerow(headers)

            # データ行の書き込み
            for item in data:
                row = []
                if "line_number" in item:
                    row.append(item["line_number"])
                if "similarity" in item:
                    row.append(f"{item['similarity']:.4f}")
                if "inference1" in item:
                    row.append(str(item["inference1"]))
                if "inference2" in item:
                    row.append(str(item["inference2"]))

                # 追加フィールド
                for key in item.keys():
                    if key not in ["line_number", "similarity", "inference1", "inference2", "_metadata"]:
                        row.append(str(item.get(key, "")))

                writer.writerow(row)

    # BOMを追加（Excelでの文字化け防止）
    return '\uFEFF' + output.getvalue()


@app.post("/download/csv")
async def download_csv(
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    type: str = "score"
) -> Response:
    """
    JSON結果をCSV形式でダウンロード

    Args:
        data: 処理結果のJSONデータ
        type: 出力タイプ（"score" または "file"）

    Returns:
        CSVファイルレスポンス
    """
    try:
        # JSONデータをCSVに変換
        csv_content = json_to_csv(data, type)

        # ファイル名の生成（日時を含む）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"json_compare_result_{timestamp}.csv"

        # CSVレスポンスを返す
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "CSV conversion error", "detail": str(e)}
        )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    ヘルスチェックエンドポイント

    Returns:
        サーバーの状態
    """
    try:
        # process_jsonl_fileが正しくインポートされているか確認
        cli_available = callable(process_jsonl_file)
    except:
        cli_available = False

    return HealthResponse(
        status="healthy",
        cli_available=cli_available
    )


@app.get("/")
async def root():
    """
    ルートエンドポイント

    Returns:
        APIの基本情報
    """
    return {
        "name": "JSON Compare API",
        "version": "1.0.0",
        "endpoints": {
            "compare": "POST /compare",
            "upload": "POST /upload",
            "download_csv": "POST /download/csv",
            "ui": "GET /ui",
            "health": "GET /health"
        }
    }


def main():
    """APIサーバーのメインエントリーポイント"""
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=18081, reload=False)


if __name__ == "__main__":
    main()