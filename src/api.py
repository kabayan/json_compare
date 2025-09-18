#!/usr/bin/env python3
"""JSON比較ツールのAPIラッパー"""

import asyncio
import csv
import io
import json
import os
import tempfile
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 既存実装から関数をインポート
from .__main__ import process_jsonl_file
from .similarity import set_gpu_mode
from .dual_file_extractor import DualFileExtractor

# エラーハンドリングとロギング
from .error_handler import ErrorHandler, ErrorRecovery, JsonRepair
from .logger import (
    get_logger,
    get_request_logger,
    get_metrics_collector,
    SystemLogger,
    RequestLogger,
    MetricsCollector
)

# ロガーの初期化
logger = get_logger()
request_logger = get_request_logger()
metrics_collector = get_metrics_collector()


app = FastAPI(
    title="JSON Compare API",
    description="JSON形式のデータを意味的類似度で比較するAPI",
    version="1.0.0"
)

# リクエストロギングミドルウェア
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """全HTTPリクエストをログに記録"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # リクエスト開始をログ
    request_logger.log_request_start(request_id)

    # クライアントIPを取得
    client_ip = request.client.host if request.client else None

    try:
        # リクエストを処理
        response = await call_next(request)

        # リクエスト終了をログ
        request_logger.log_request_end(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            client_ip=client_ip
        )

        return response

    except Exception as e:
        # エラーの場合もログに記録
        request_logger.log_request_end(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=500,
            client_ip=client_ip
        )
        raise


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
    request: Request,
    file: UploadFile = File(...),
    type: str = Form("score"),
    gpu: bool = Form(False)
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    ファイルをアップロードして類似度計算を実行する

    Args:
        request: FastAPIのRequestオブジェクト
        file: アップロードされたJSONLファイル
        type: 出力タイプ（"score" または "file"）
        gpu: GPU使用フラグ

    Returns:
        比較結果（scoreまたはfile形式）

    Raises:
        HTTPException: ファイルバリデーションエラー、処理エラーなど
    """
    start_time = time.time()
    error_id = None
    client_ip = request.client.host if request.client else None

    try:
        # システムリソースチェック
        resource_ok, resource_msg = ErrorHandler.check_system_resources()
        if not resource_ok:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="insufficient_memory" if "メモリ" in resource_msg else "insufficient_storage",
                details={"resource_check": resource_msg}
            )
            logger.log_error(
                error_id=error_id,
                error_type="resource_error",
                error_message=resource_msg,
                context={"filename": file.filename, "client_ip": client_ip}
            )
            raise HTTPException(status_code=503, detail=error_response)
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
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={"filename": file.filename, "expected": ".jsonl"}
            )
            logger.log_error(
                error_id=error_id,
                error_type="invalid_file_type",
                error_message=f"Invalid file type: {file.filename}",
                context={"filename": file.filename, "client_ip": client_ip}
            )
            metrics_collector.record_upload(
                success=False,
                processing_time=time.time() - start_time,
                file_size=0
            )
            raise HTTPException(status_code=400, detail=error_response)

        # ファイルサイズの確認（100MB制限）
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={
                    "file_size_mb": len(file_content) / (1024*1024),
                    "limit_mb": 100
                }
            )
            logger.log_error(
                error_id=error_id,
                error_type="file_too_large",
                error_message=f"File too large: {len(file_content) / (1024*1024):.1f}MB",
                context={"filename": file.filename, "client_ip": client_ip}
            )
            metrics_collector.record_upload(
                success=False,
                processing_time=time.time() - start_time,
                file_size=len(file_content)
            )
            raise HTTPException(status_code=413, detail=error_response)

        # ファイルポインタをリセット
        await file.seek(0)

        # JSONLファイルの検証と修復
        try:
            content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={"encoding": "UTF-8エンコーディングが必要です"}
            )
            logger.log_error(
                error_id=error_id,
                error_type="encoding_error",
                error_message="Invalid UTF-8 encoding",
                context={"filename": file.filename, "client_ip": client_ip}
            )
            raise HTTPException(status_code=400, detail=error_response)

        # JSONLの検証と修復
        repaired_data, error_messages, validation_ok = ErrorHandler.validate_and_repair_jsonl(content)

        if not validation_ok:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={
                    "errors": error_messages[:5],  # 最初の5件のエラー
                    "total_errors": len(error_messages)
                }
            )
            logger.log_error(
                error_id=error_id,
                error_type="validation_error",
                error_message="JSONL validation failed",
                context={
                    "filename": file.filename,
                    "errors": error_messages[:10],
                    "client_ip": client_ip
                }
            )
            raise HTTPException(status_code=400, detail=error_response)

        # 警告があった場合はログに記録（修復済み）
        if error_messages:
            logger.access_logger.warning(json.dumps({
                "event": "jsonl_repaired",
                "filename": file.filename,
                "repairs": error_messages[:5],
                "total_repairs": len(error_messages),
                "client_ip": client_ip
            }))

        # 修復済みデータをJSONL形式に戻す
        repaired_content = '\n'.join(json.dumps(item, ensure_ascii=False) for item in repaired_data)

        # 一時ファイルの作成と保存
        temp_dir = tempfile.gettempdir()
        unique_id = str(uuid.uuid4())
        temp_filename = f"json_compare_{unique_id}.jsonl"
        temp_filepath = os.path.join(temp_dir, temp_filename)

        temp_file_created = False
        try:
            # 一時ファイルに修復済み内容を保存
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                f.write(repaired_content)
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
                    if error_messages:
                        result["_metadata"]["data_repairs"] = len(error_messages)

                # 成功をログに記録
                logger.log_upload(
                    filename=file.filename,
                    file_size=len(file_content),
                    processing_time=processing_time,
                    result="success",
                    gpu_mode=gpu,
                    client_ip=client_ip
                )

                # メトリクスを更新
                metrics_collector.record_upload(
                    success=True,
                    processing_time=processing_time,
                    file_size=len(file_content)
                )

                return result

            except asyncio.TimeoutError:
                error_id = ErrorHandler.generate_error_id()
                processing_time = time.time() - start_time

                error_response = ErrorHandler.format_user_error(
                    error_id=error_id,
                    error_type="processing_timeout",
                    details={
                        "timeout": "60秒",
                        "file_size_mb": len(file_content) / (1024*1024)
                    }
                )

                logger.log_upload(
                    filename=file.filename,
                    file_size=len(file_content),
                    processing_time=processing_time,
                    result="timeout",
                    gpu_mode=gpu,
                    error="Timeout after 60 seconds",
                    client_ip=client_ip
                )

                logger.log_error(
                    error_id=error_id,
                    error_type="timeout",
                    error_message="Processing timeout",
                    context={
                        "filename": file.filename,
                        "file_size": len(file_content),
                        "gpu_mode": gpu,
                        "client_ip": client_ip
                    }
                )

                metrics_collector.record_upload(
                    success=False,
                    processing_time=processing_time,
                    file_size=len(file_content)
                )

                raise HTTPException(status_code=504, detail=error_response)
            except MemoryError:
                error_id = ErrorHandler.generate_error_id()
                processing_time = time.time() - start_time

                error_response = ErrorHandler.format_user_error(
                    error_id=error_id,
                    error_type="insufficient_memory",
                    details={"file_size_mb": len(file_content) / (1024*1024)}
                )

                logger.log_upload(
                    filename=file.filename,
                    file_size=len(file_content),
                    processing_time=processing_time,
                    result="error",
                    gpu_mode=gpu,
                    error="Memory error",
                    client_ip=client_ip
                )

                logger.log_error(
                    error_id=error_id,
                    error_type="memory_error",
                    error_message="Insufficient memory",
                    context={
                        "filename": file.filename,
                        "file_size": len(file_content),
                        "gpu_mode": gpu,
                        "client_ip": client_ip
                    }
                )

                metrics_collector.record_upload(
                    success=False,
                    processing_time=processing_time,
                    file_size=len(file_content)
                )

                raise HTTPException(status_code=503, detail=error_response)

        except OSError as e:
            # ディスク容量不足などのOSエラー
            if temp_file_created and os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass

            error_id = ErrorHandler.generate_error_id()
            processing_time = time.time() - start_time

            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="insufficient_storage",
                details={"os_error": str(e)}
            )

            logger.log_upload(
                filename=file.filename,
                file_size=len(file_content),
                processing_time=processing_time,
                result="error",
                gpu_mode=gpu,
                error=f"OS error: {str(e)}",
                client_ip=client_ip
            )

            logger.log_error(
                error_id=error_id,
                error_type="storage_error",
                error_message=str(e),
                context={
                    "filename": file.filename,
                    "client_ip": client_ip
                }
            )

            metrics_collector.record_upload(
                success=False,
                processing_time=processing_time,
                file_size=len(file_content)
            )

            raise HTTPException(status_code=507, detail=error_response)

        finally:
            # 一時ファイルのクリーンアップ
            if temp_file_created and os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except Exception as cleanup_error:
                    logger.error_logger.warning(json.dumps({
                        "event": "cleanup_failed",
                        "file": temp_filepath,
                        "error": str(cleanup_error)
                    }))

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        # 予期しないエラー
        error_id = ErrorHandler.generate_error_id() if not error_id else error_id
        processing_time = time.time() - start_time

        error_response = ErrorHandler.format_user_error(
            error_id=error_id,
            error_type="internal_error",
            details={"exception": str(e)}
        )

        logger.log_upload(
            filename=file.filename if file else "unknown",
            file_size=len(file_content) if 'file_content' in locals() else 0,
            processing_time=processing_time,
            result="error",
            gpu_mode=gpu,
            error=str(e),
            client_ip=client_ip
        )

        logger.log_error(
            error_id=error_id,
            error_type="internal_error",
            error_message=str(e),
            stack_trace=traceback.format_exc(),
            context={
                "filename": file.filename if file else "unknown",
                "client_ip": client_ip
            }
        )

        metrics_collector.record_upload(
            success=False,
            processing_time=processing_time,
            file_size=len(file_content) if 'file_content' in locals() else 0
        )

        raise HTTPException(status_code=500, detail=error_response)


@app.post("/api/compare/dual")
async def compare_dual_files(
    request: Request,
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    column: str = Form("inference"),
    type: str = Form("score"),
    gpu: bool = Form(False)
) -> Dict[str, Any]:
    """
    2つのJSONLファイルの指定列を比較する

    Args:
        request: FastAPIのRequestオブジェクト
        file1: 1つ目のJSONLファイル
        file2: 2つ目のJSONLファイル
        column: 比較する列名（デフォルト: inference）
        type: 出力タイプ（"score" または "file"）
        gpu: GPU使用フラグ

    Returns:
        比較結果（scoreまたはfile形式）

    Raises:
        HTTPException: ファイルバリデーションエラー、処理エラーなど
    """
    start_time = time.time()
    error_id = None
    client_ip = request.client.host if request.client else None
    temp_file1_path = None
    temp_file2_path = None

    try:
        # システムリソースチェック
        resource_ok, resource_msg = ErrorHandler.check_system_resources()
        if not resource_ok:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="insufficient_memory" if "メモリ" in resource_msg else "insufficient_storage",
                details={"resource_check": resource_msg}
            )
            logger.log_error(
                error_id=error_id,
                error_type="resource_error",
                error_message=resource_msg,
                context={
                    "file1": file1.filename,
                    "file2": file2.filename,
                    "client_ip": client_ip
                }
            )
            raise HTTPException(status_code=503, detail=error_response)

        # typeパラメータの検証
        if type not in ["score", "file"]:
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid type parameter", "detail": "type must be 'score' or 'file'"}
            )

        # ファイルの検証
        for file_num, file in enumerate([file1, file2], 1):
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "No file provided", "detail": f"ファイル{file_num}が選択されていません"}
                )

            if not file.filename.lower().endswith('.jsonl'):
                error_id = ErrorHandler.generate_error_id()
                error_response = ErrorHandler.format_user_error(
                    error_id=error_id,
                    error_type="file_validation",
                    details={"filename": file.filename, "expected": ".jsonl", "file_number": file_num}
                )
                logger.log_error(
                    error_id=error_id,
                    error_type="invalid_file_type",
                    error_message=f"Invalid file type for file{file_num}: {file.filename}",
                    context={"filename": file.filename, "client_ip": client_ip}
                )
                raise HTTPException(status_code=400, detail=error_response)

        # ファイルサイズの確認（100MB制限）
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

        file1_content = await file1.read()
        if len(file1_content) > MAX_FILE_SIZE:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={
                    "file": file1.filename,
                    "file_size_mb": len(file1_content) / (1024*1024),
                    "limit_mb": 100
                }
            )
            raise HTTPException(status_code=413, detail=error_response)

        file2_content = await file2.read()
        if len(file2_content) > MAX_FILE_SIZE:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={
                    "file": file2.filename,
                    "file_size_mb": len(file2_content) / (1024*1024),
                    "limit_mb": 100
                }
            )
            raise HTTPException(status_code=413, detail=error_response)

        # 一時ファイルの作成
        temp_dir = tempfile.gettempdir()
        unique_id1 = str(uuid.uuid4())
        unique_id2 = str(uuid.uuid4())
        temp_file1_path = os.path.join(temp_dir, f"json_compare_{unique_id1}.jsonl")
        temp_file2_path = os.path.join(temp_dir, f"json_compare_{unique_id2}.jsonl")

        # ファイル内容をデコードして一時ファイルに保存
        try:
            content1 = file1_content.decode('utf-8')
            content2 = file2_content.decode('utf-8')
        except UnicodeDecodeError as e:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={"encoding": "UTF-8エンコーディングが必要です"}
            )
            raise HTTPException(status_code=400, detail=error_response)

        # JSONLの検証と修復
        repaired_data1, errors1, ok1 = ErrorHandler.validate_and_repair_jsonl(content1)
        if not ok1:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={
                    "file": file1.filename,
                    "errors": errors1[:5],
                    "total_errors": len(errors1)
                }
            )
            raise HTTPException(status_code=400, detail=error_response)

        repaired_data2, errors2, ok2 = ErrorHandler.validate_and_repair_jsonl(content2)
        if not ok2:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="file_validation",
                details={
                    "file": file2.filename,
                    "errors": errors2[:5],
                    "total_errors": len(errors2)
                }
            )
            raise HTTPException(status_code=400, detail=error_response)

        # 修復済みデータを一時ファイルに保存
        with open(temp_file1_path, 'w', encoding='utf-8') as f:
            for item in repaired_data1:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        with open(temp_file2_path, 'w', encoding='utf-8') as f:
            for item in repaired_data2:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        # GPUモードの設定
        if gpu:
            set_gpu_mode(True)
        else:
            set_gpu_mode(False)

        # DualFileExtractorを使用して比較
        extractor = DualFileExtractor()

        # タイムアウト付きで処理を実行（60秒制限）
        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    extractor.compare_dual_files,
                    temp_file1_path,
                    temp_file2_path,
                    column,
                    type,
                    gpu
                ),
                timeout=60.0
            )

            processing_time = time.time() - start_time

            # メタデータを更新
            if isinstance(result, dict) and '_metadata' in result:
                result["_metadata"]["processing_time"] = f"{processing_time:.2f}秒"
                result["_metadata"]["original_files"] = {
                    "file1": file1.filename,
                    "file2": file2.filename
                }
                if errors1 or errors2:
                    result["_metadata"]["data_repairs"] = {
                        "file1": len(errors1),
                        "file2": len(errors2)
                    }

            # 成功をログに記録
            logger.log_metrics({
                "event": "dual_file_comparison_success",
                "file1": file1.filename,
                "file2": file2.filename,
                "column": column,
                "processing_time": processing_time,
                "gpu_mode": gpu,
                "client_ip": client_ip
            })

            # メトリクスを更新
            metrics_collector.record_upload(
                success=True,
                processing_time=processing_time,
                file_size=len(file1_content) + len(file2_content)
            )

            return result

        except asyncio.TimeoutError:
            error_id = ErrorHandler.generate_error_id()
            error_response = ErrorHandler.format_user_error(
                error_id=error_id,
                error_type="timeout",
                details={"timeout_seconds": 60}
            )

            logger.log_error(
                error_id=error_id,
                error_type="timeout_error",
                error_message="Dual file comparison timeout",
                context={
                    "file1": file1.filename,
                    "file2": file2.filename,
                    "column": column,
                    "gpu_mode": gpu,
                    "client_ip": client_ip
                }
            )

            metrics_collector.record_upload(
                success=False,
                processing_time=60.0,
                file_size=len(file1_content) + len(file2_content)
            )

            raise HTTPException(status_code=504, detail=error_response)

    except HTTPException:
        raise
    except Exception as e:
        error_id = ErrorHandler.generate_error_id() if not error_id else error_id
        processing_time = time.time() - start_time

        error_response = ErrorHandler.format_user_error(
            error_id=error_id,
            error_type="processing_error",
            details={"error": str(e)}
        )

        logger.log_error(
            error_id=error_id,
            error_type="dual_comparison_error",
            error_message=str(e),
            context={
                "file1": file1.filename if file1 else None,
                "file2": file2.filename if file2 else None,
                "column": column,
                "client_ip": client_ip
            },
            stack_trace=traceback.format_exc()
        )

        metrics_collector.record_upload(
            success=False,
            processing_time=processing_time,
            file_size=0
        )

        raise HTTPException(status_code=500, detail=error_response)

    finally:
        # 一時ファイルのクリーンアップ
        for temp_file in [temp_file1_path, temp_file2_path]:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass


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

        /* タブスタイル */
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
            color: #333;
            background: white;
            transition: border-color 0.3s ease;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }

        @media (max-width: 640px) {
            .container {
                padding: 30px 20px;
            }

            h1 {
                font-size: 24px;
            }

            .file-inputs-row {
                grid-template-columns: 1fr;
            }

            .tabs {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 JSON Compare</h1>
        <p class="subtitle">JSONLファイルの類似度を計算します</p>

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
        <form id="uploadForm" enctype="multipart/form-data" class="mode-form active" data-mode="single">
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

        <!-- 2ファイル比較モード -->
        <form id="dualForm" enctype="multipart/form-data" class="mode-form" data-mode="dual">
            <div class="form-group">
                <label>比較するJSONLファイルを選択</label>
                <div class="file-inputs-row">
                    <div class="file-input-wrapper">
                        <label for="file1" class="file-input-button" id="file1Label">
                            📁 1つ目のファイル（.jsonl）
                        </label>
                        <input type="file" id="file1" name="file1" accept=".jsonl" required>
                    </div>
                    <div class="file-input-wrapper">
                        <label for="file2" class="file-input-button" id="file2Label">
                            📁 2つ目のファイル（.jsonl）
                        </label>
                        <input type="file" id="file2" name="file2" accept=".jsonl" required>
                    </div>
                </div>
            </div>

            <div class="form-group">
                <label for="column">比較する列名</label>
                <input type="text" id="column" name="column" placeholder="inference" value="inference">
            </div>

            <div class="form-group">
                <label for="type2">出力形式</label>
                <select id="type2" name="type">
                    <option value="score">スコア（全体平均）</option>
                    <option value="file">ファイル（詳細結果）</option>
                </select>
            </div>

            <div class="form-group">
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="gpu2" name="gpu" value="true">
                    <label for="gpu2" class="checkbox-label">GPU を使用する（高速処理）</label>
                </div>
            </div>

            <button type="submit" class="submit-button" id="dualSubmitButton">
                🔀 2ファイルの列を比較
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
        const dualForm = document.getElementById('dualForm');
        const fileInput = document.getElementById('file');
        const fileLabel = document.getElementById('fileLabel');
        const file1Input = document.getElementById('file1');
        const file1Label = document.getElementById('file1Label');
        const file2Input = document.getElementById('file2');
        const file2Label = document.getElementById('file2Label');
        const loading = document.getElementById('loading');
        const submitButton = document.getElementById('submitButton');
        const dualSubmitButton = document.getElementById('dualSubmitButton');
        const resultContainer = document.getElementById('resultContainer');
        const resultTitle = document.getElementById('resultTitle');
        const resultContent = document.getElementById('resultContent');
        const downloadButtons = document.getElementById('downloadButtons');
        const downloadJsonButton = document.getElementById('downloadJsonButton');
        const downloadCsvButton = document.getElementById('downloadCsvButton');
        let lastResult = null;
        let lastType = 'score';
        let currentMode = 'single';

        // モード切り替え関数
        function switchMode(mode) {
            currentMode = mode;

            // タブボタンのアクティブ状態を更新
            document.querySelectorAll('.tab-button').forEach(btn => {
                if (btn.dataset.mode === mode) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            });

            // フォームの表示切り替え
            document.querySelectorAll('.mode-form').forEach(form => {
                if (form.dataset.mode === mode) {
                    form.classList.add('active');
                } else {
                    form.classList.remove('active');
                }
            });

            // 結果をクリア
            resultContainer.classList.remove('active');
        }

        // 単一ファイル選択時の表示更新
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

        // 2ファイル選択時の表示更新
        file1Input.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                const fileName = this.files[0].name;
                file1Label.textContent = `✅ ${fileName}`;
                file1Label.classList.add('file-selected');
            } else {
                file1Label.textContent = '📁 1つ目のファイル（.jsonl）';
                file1Label.classList.remove('file-selected');
            }
        });

        file2Input.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                const fileName = this.files[0].name;
                file2Label.textContent = `✅ ${fileName}`;
                file2Label.classList.add('file-selected');
            } else {
                file2Label.textContent = '📁 2つ目のファイル（.jsonl）';
                file2Label.classList.remove('file-selected');
            }
        });

        // 単一ファイルフォーム送信処理
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

                    // CSVダウンロードボタン
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

        // 2ファイルフォーム送信処理
        dualForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(dualForm);

            // チェックボックスの値を調整
            if (!document.getElementById('gpu2').checked) {
                formData.set('gpu', 'false');
            }

            // UI状態の更新
            dualSubmitButton.disabled = true;
            loading.classList.add('active');
            resultContainer.classList.remove('active');

            try {
                const response = await fetch('/api/compare/dual', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    // 成功時の処理
                    lastResult = data;
                    resultTitle.textContent = '✅ 2ファイル比較完了';
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
                    downloadJsonButton.download = `dual_result_${timestamp}.json`;

                    // CSVダウンロードボタン
                    downloadCsvButton.onclick = async (e) => {
                        e.preventDefault();
                        const csvContent = convertToCSV(data, lastType);
                        const csvBlob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                        const csvUrl = URL.createObjectURL(csvBlob);
                        const a = document.createElement('a');
                        a.href = csvUrl;
                        a.download = `dual_result_${timestamp}.csv`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(csvUrl);
                    };

                } else {
                    // エラー時の処理
                    resultTitle.textContent = '❌ エラーが発生しました';
                    resultContent.textContent = data.detail ?
                        (typeof data.detail === 'object' ?
                            `${data.detail.error || 'Error'}: ${data.detail.detail || JSON.stringify(data.detail)}` :
                            data.detail) :
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
                dualSubmitButton.disabled = false;
            }
        });

        // CSV変換関数
        function convertToCSV(data, type) {
            let csv = '';

            if (type === 'score') {
                // スコアモードの場合
                csv = '項目,値\\n';

                // 基本スコア
                if (data.score !== undefined) {
                    csv += `類似度スコア,${data.score}\\n`;
                }
                if (data.meaning !== undefined) {
                    csv += `意味,${data.meaning}\\n`;
                }
                if (data.total_lines !== undefined) {
                    csv += `総行数,${data.total_lines}\\n`;
                }

                // JSON詳細
                if (data.json) {
                    csv += `\\n詳細\\n`;
                    csv += `フィールド一致率,${data.json.field_match_ratio || 0}\\n`;
                    csv += `値類似度,${data.json.value_similarity || 0}\\n`;
                    csv += `最終スコア,${data.json.final_score || 0}\\n`;
                }

                // 統計情報
                if (data.statistics) {
                    const stats = data.statistics;
                    csv += `\\n統計\\n`;
                    csv += `平均類似度,${(stats.mean || 0).toFixed(4)}\\n`;
                    csv += `中央値,${(stats.median || 0).toFixed(4)}\\n`;
                    csv += `標準偏差,${(stats.std_dev || 0).toFixed(4)}\\n`;
                    csv += `最小値,${(stats.min || 0).toFixed(4)}\\n`;
                    csv += `最大値,${(stats.max || 0).toFixed(4)}\\n`;
                }

                // メタデータ
                if (data._metadata) {
                    csv += `\\nメタデータ\\n`;
                    csv += `処理時間,${data._metadata.processing_time || 'N/A'}\\n`;

                    // 単一ファイルの場合
                    if (data._metadata.original_filename) {
                        csv += `元ファイル名,${data._metadata.original_filename}\\n`;
                    }

                    // 2ファイル比較の場合
                    if (data._metadata.source_files) {
                        csv += `ファイル1,${data._metadata.source_files.file1}\\n`;
                        csv += `ファイル2,${data._metadata.source_files.file2}\\n`;
                    }
                    if (data._metadata.column_compared) {
                        csv += `比較列,${data._metadata.column_compared}\\n`;
                    }
                    if (data._metadata.rows_compared !== undefined) {
                        csv += `比較行数,${data._metadata.rows_compared}\\n`;
                    }
                    csv += `GPU使用,${data._metadata.gpu_used ? '有' : '無'}\\n`;
                }
            } else if (type === 'file') {
                // ファイルモードの場合
                if (Array.isArray(data) && data.length > 0) {
                    // ヘッダー行の生成
                    const headers = [];
                    const firstItem = data[0];
                    if ('line_number' in firstItem) headers.push('行番号');
                    if ('similarity_score' in firstItem) headers.push('類似度スコア');
                    if ('inference1' in firstItem) headers.push('推論1');
                    if ('inference2' in firstItem) headers.push('推論2');
                    if ('similarity_details' in firstItem) {
                        headers.push('フィールド一致率');
                        headers.push('値類似度');
                    }

                    csv = headers.join(',') + '\\n';

                    // データ行の生成
                    data.forEach((item, index) => {
                        const row = [];
                        if ('line_number' in item) row.push(item.line_number || index + 1);
                        if ('similarity_score' in item) row.push((item.similarity_score || 0).toFixed(4));
                        if ('inference1' in item) row.push(`"${String(item.inference1).replace(/"/g, '""')}"`);
                        if ('inference2' in item) row.push(`"${String(item.inference2).replace(/"/g, '""')}"`);
                        if ('similarity_details' in item) {
                            row.push((item.similarity_details.field_match_ratio || 0).toFixed(4));
                            row.push((item.similarity_details.value_similarity || 0).toFixed(4));
                        }
                        csv += row.join(',') + '\\n';
                    });
                }
            }

            // BOMを追加（Excelでの文字化け防止）
            return '\uFEFF' + csv;
        }

        // switchMode関数をグローバルに設定
        window.switchMode = switchMode;

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

    # システムメトリクスをログに記録
    logger.log_metrics()

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
            "health": "GET /health",
            "metrics": "GET /metrics"
        }
    }


@app.get("/metrics")
async def get_metrics():
    """
    メトリクス情報を取得

    Returns:
        アップロード統計とシステムメトリクス
    """
    # メトリクスサマリーをログに記録
    metrics_collector.log_summary()

    # 現在のメトリクスを返す
    return {
        "upload_metrics": metrics_collector.get_summary(),
        "timestamp": datetime.now().isoformat()
    }


def main():
    """APIサーバーのメインエントリーポイント"""
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=18081, reload=False)


if __name__ == "__main__":
    main()