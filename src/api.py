#!/usr/bin/env python3
"""JSON比較ツールのAPIラッパー"""

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 既存実装から関数をインポート
from .__main__ import process_jsonl_file


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

            # TODO: 実際の処理呼び出し（タスク3で実装）
            # TODO: process_jsonl_file(temp_filepath, type) の呼び出し

            # 現在は一時ファイル作成成功のレスポンスを返す（実装途中）
            result = {
                "message": "一時ファイル作成が成功しました",
                "filename": file.filename,
                "temp_file": temp_filename,
                "file_size": f"{len(file_content) / (1024*1024):.2f}MB",
                "lines": len(lines),
                "type": type,
                "gpu": gpu,
                "status": "temp_file_created"
            }

            return result

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
            "health": "GET /health"
        }
    }


def main():
    """APIサーバーのメインエントリーポイント"""
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=18081, reload=False)


if __name__ == "__main__":
    main()