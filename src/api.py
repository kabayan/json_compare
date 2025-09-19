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
import numpy as np

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette import EventSourceResponse

# 既存実装から関数をインポート
from .__main__ import process_jsonl_file
from .similarity import set_gpu_mode
from .dual_file_extractor import DualFileExtractor
from .jsonl_formatter import auto_fix_jsonl_file

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

# 進捗トラッカーのインポート
from .progress_tracker import ProgressTracker, TqdmInterceptor

# ロガーの初期化
logger = get_logger()
request_logger = get_request_logger()
metrics_collector = get_metrics_collector()

# グローバル進捗トラッカーの初期化
progress_tracker = ProgressTracker()
tqdm_interceptor = TqdmInterceptor()


app = FastAPI(
    title="JSON Compare API",
    description="JSON形式のデータを意味的類似度で比較するAPI",
    version="1.0.0"
)


def convert_numpy_types(obj):
    """numpy型をPython標準型に再帰的に変換"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    else:
        return obj


# バリデーション関数
def validate_llm_config(config: Dict[str, Any]) -> bool:
    """LLM設定を検証"""
    temperature = config.get("temperature", 0.2)
    max_tokens = config.get("max_tokens", 64)

    if not (0.0 <= temperature <= 1.0):
        raise ValueError("temperatureは0.0から1.0の間で指定してください")

    if max_tokens < 1:
        raise ValueError("max_tokensは1以上で指定してください")

    return True


def validate_prompt_file(prompt_data: Dict[str, Any]) -> bool:
    """プロンプトファイル形式を検証"""
    required_fields = ["user_prompt"]

    for field in required_fields:
        if field not in prompt_data:
            raise ValueError(f"{field}は必須フィールドです")

    return True


# LLM処理関数のプレースホルダ
async def process_jsonl_file_with_llm(file_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """LLM付きJSONLファイル処理（プレースホルダ）"""
    # 実際の実装では enhanced_cli の機能を使用
    from .enhanced_cli import EnhancedCLI, CLIConfig

    cli_config = CLIConfig(
        calculation_method="llm",
        llm_enabled=True,
        model_name=config.get("model", "qwen3-14b-awq"),
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 64)
    )

    enhanced_cli = EnhancedCLI()
    return await enhanced_cli.process_single_file(file_path, cli_config, config.get("type", "score"))


async def process_dual_files_with_llm(file1_path: str, file2_path: str, column: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """LLM付きデュアルファイル処理（プレースホルダ）"""
    from .enhanced_cli import EnhancedCLI, CLIConfig

    cli_config = CLIConfig(
        calculation_method="llm",
        llm_enabled=True,
        model_name=config.get("model", "qwen3-14b-awq"),
        temperature=config.get("temperature", 0.2),
        max_tokens=config.get("max_tokens", 64)
    )

    enhanced_cli = EnhancedCLI()
    return await enhanced_cli.process_dual_files(file1_path, file2_path, column, cli_config, config.get("type", "score"))


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


class LLMConfig(BaseModel):
    """LLM設定のモデル"""
    model: str = "qwen3-14b-awq"
    temperature: float = 0.2
    max_tokens: int = 64
    prompt_file: Optional[str] = None


class CompareRequestWithLLM(BaseModel):
    """LLM付き比較リクエストのモデル"""
    file_content: str
    type: str = "score"
    use_llm: bool = False
    llm_config: Optional[LLMConfig] = None
    fallback_enabled: bool = True


class DualFileCompareRequestWithLLM(BaseModel):
    """LLM付きデュアルファイル比較リクエストのモデル"""
    file1_content: str
    file2_content: str
    column: str = "inference"
    type: str = "score"
    use_llm: bool = False
    llm_config: Optional[LLMConfig] = None
    fallback_enabled: bool = True


class PromptUploadResponse(BaseModel):
    """プロンプトアップロードレスポンスのモデル"""
    status: str
    prompt_id: str
    message: Optional[str] = None


class PromptListResponse(BaseModel):
    """プロンプト一覧レスポンスのモデル"""
    prompts: List[Dict[str, Any]]


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


@app.post("/api/compare/single")
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

            # JSONLファイルのフォーマットを自動修正
            try:
                fixed_path = auto_fix_jsonl_file(temp_filepath)
                if fixed_path != temp_filepath:
                    # 修正されたファイルを使用
                    temp_filepath = fixed_path
            except ValueError as format_error:
                print(f"警告: JSONLフォーマット修正に失敗: {format_error}")

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
                    # resultに既にcalculation_methodがある場合はそれを使用
                    existing_method = result.get("calculation_method", "embedding")

                    result["_metadata"] = {
                        "processing_time": f"{processing_time:.2f}秒",
                        "original_filename": file.filename,
                        "gpu_used": gpu,
                        "calculation_method": existing_method  # 実際の推論方法を使用
                    }
                    if error_messages:
                        result["_metadata"]["data_repairs"] = len(error_messages)

                    # calculation_methodがトップレベルにある場合は削除（_metadataに移動済み）
                    if "calculation_method" in result:
                        del result["calculation_method"]

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

        # まず生のコンテンツを一時ファイルに保存
        with open(temp_file1_path, 'w', encoding='utf-8') as f:
            f.write(content1)

        with open(temp_file2_path, 'w', encoding='utf-8') as f:
            f.write(content2)

        # JSONLファイルのフォーマットを自動修正（マルチライン→シングルライン）
        try:
            fixed_path1 = auto_fix_jsonl_file(temp_file1_path)
            if fixed_path1 != temp_file1_path:
                temp_file1_path = fixed_path1
                # 修正されたファイルの内容を読み込む
                with open(fixed_path1, 'r', encoding='utf-8') as f:
                    content1 = f.read()

            fixed_path2 = auto_fix_jsonl_file(temp_file2_path)
            if fixed_path2 != temp_file2_path:
                temp_file2_path = fixed_path2
                # 修正されたファイルの内容を読み込む
                with open(fixed_path2, 'r', encoding='utf-8') as f:
                    content2 = f.read()
        except ValueError as format_error:
            print(f"警告: JSONLフォーマット修正に失敗: {format_error}")

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

        # 検証済みデータを一時ファイルに保存（必要な場合）
        if len(errors1) > 0 or len(errors2) > 0:
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

        # 処理を実行（タイムアウトなし - 大きなファイルに対応）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            extractor.compare_dual_files,
            temp_file1_path,
            temp_file2_path,
            column,
            type,
            gpu
        )

        processing_time = time.time() - start_time

        # メタデータを更新
        if isinstance(result, dict):
            if '_metadata' not in result:
                result['_metadata'] = {}
            result["_metadata"]["processing_time"] = f"{processing_time:.2f}秒"
            result["_metadata"]["original_files"] = {
                "file1": file1.filename,
                "file2": file2.filename
            }
            result["_metadata"]["calculation_method"] = "embedding"  # 埋め込みベースの計算方法を明示
            result["_metadata"]["gpu_used"] = gpu
            if errors1 or errors2:
                result["_metadata"]["data_repairs"] = {
                    "file1": len(errors1),
                    "file2": len(errors2)
                }

        # 成功をログに記録（システムメトリクスを記録）
        logger.log_metrics()

        # イベント情報を通常のログに記録
        print(f"✅ Dual file comparison success - File1: {file1.filename}, File2: {file2.filename}, Column: {column}, Time: {processing_time:.3f}s")

        # メトリクスを更新
        metrics_collector.record_upload(
            success=True,
            processing_time=processing_time,
            file_size=len(file1_content) + len(file2_content)
        )

        return result

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

        input[type="number"] {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            font-size: 14px;
            color: #333;
            background: white;
            transition: border-color 0.3s ease;
        }

        input[type="number"]:focus {
            outline: none;
            border-color: #667eea;
        }

        .llm-config-section {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 15px;
            padding: 20px;
            margin-top: 15px;
            transition: all 0.3s ease;
        }

        .llm-config-section.active {
            background: #eef2ff;
            border-color: #c3d4ff;
        }

        /* 進捗表示セクションのスタイリング */
        .progress-section {
            margin: 30px 0;
            animation: fadeIn 0.3s ease-in;
        }

        .progress-container {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 15px;
            padding: 25px;
            transition: all 0.3s ease;
        }

        .progress-title {
            color: #333;
            font-size: 18px;
            margin-bottom: 20px;
            text-align: center;
        }

        .progress-bar-container {
            margin-bottom: 20px;
        }

        .progress-bar {
            width: 100%;
            height: 12px;
            border-radius: 6px;
            margin-bottom: 10px;
            appearance: none;
            -webkit-appearance: none;
        }

        .progress-bar::-webkit-progress-bar {
            background-color: #e2e8f0;
            border-radius: 6px;
        }

        .progress-bar::-webkit-progress-value {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 6px;
        }

        .progress-bar::-moz-progress-bar {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 6px;
        }

        .progress-labels {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            color: #555;
        }

        .progress-percentage {
            font-weight: 600;
            color: #667eea;
        }

        .progress-text {
            color: #666;
        }

        .time-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }

        .time-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
        }

        .time-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 5px;
        }

        .time-value {
            font-size: 16px;
            font-weight: 600;
            color: #333;
        }

        .status-message {
            background: #dbeafe;
            border: 1px solid #93c5fd;
            color: #1e40af;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 14px;
        }

        .error-message {
            background: #fef2f2;
            border: 1px solid #fca5a5;
            color: #dc2626;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 14px;
        }

        .warning-message {
            background: #fefbf2;
            border: 1px solid #fbbf24;
            color: #d97706;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 14px;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
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

        /* ユーザーインタラクション要素のスタイル */
        .interaction-controls {
            display: flex;
            gap: 12px;
            margin-top: 20px;
            flex-wrap: wrap;
            align-items: center;
        }

        .cancel-button, .retry-button, .download-button {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .cancel-button {
            background: #fca5a5;
            color: #dc2626;
        }

        .cancel-button:hover {
            background: #f87171;
        }

        .retry-button {
            background: #fbbf24;
            color: #92400e;
        }

        .retry-button:hover {
            background: #f59e0b;
        }

        .download-button {
            background: #93c5fd;
            color: #1e40af;
        }

        .download-button:hover {
            background: #60a5fa;
        }

        .split-suggestion {
            background: #fef3c7;
            border: 1px solid #f59e0b;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }

        .split-suggestion-content h4 {
            margin: 0 0 10px 0;
            color: #92400e;
            font-size: 16px;
        }

        .split-message {
            margin: 0 0 10px 0;
            color: #92400e;
            font-size: 14px;
        }

        .split-details {
            color: #92400e;
            font-size: 13px;
            font-weight: 500;
        }

        @media (max-width: 640px) {
            .interaction-controls {
                flex-direction: column;
                align-items: stretch;
            }

            .cancel-button, .retry-button, .download-button {
                width: 100%;
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
        <form id="uploadForm" action="/api/compare/async" method="post" enctype="multipart/form-data" class="mode-form active" data-mode="single">
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

            <!-- LLM設定セクション -->
            <div class="form-group">
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="use_llm" name="use_llm" value="true" onclick="toggleLLMConfig()">
                    <label for="use_llm" class="checkbox-label">🤖 LLMベース判定を使用</label>
                </div>
            </div>

            <div id="llm_config_section" class="llm-config-section" style="display: none;">
                <div class="form-group">
                    <label for="prompt_file">プロンプトファイル</label>
                    <div class="file-input-wrapper">
                        <label for="prompt_file" class="file-input-button" id="promptFileLabel">
                            📄 プロンプトファイルを選択（.yaml）
                        </label>
                        <input type="file" id="prompt_file" name="prompt_file" accept=".yaml,.yml">
                    </div>
                </div>

                <div class="form-group">
                    <label for="model_name">LLMモデル名</label>
                    <input type="text" id="model_name" name="model_name" placeholder="qwen3-14b-awq" value="qwen3-14b-awq">
                </div>

                <div class="form-group">
                    <div class="file-inputs-row">
                        <div>
                            <label for="temperature">生成温度</label>
                            <input type="number" id="temperature" name="temperature" min="0" max="1" step="0.1" value="0.2">
                        </div>
                        <div>
                            <label for="max_tokens">最大トークン数</label>
                            <input type="number" id="max_tokens" name="max_tokens" min="1" max="512" value="64">
                        </div>
                    </div>
                </div>
            </div>

            <button type="submit" class="submit-button" id="submitButton">
                📊 類似度を計算
            </button>
        </form>

        <!-- 2ファイル比較モード -->
        <form id="dualForm" action="/api/compare/dual" method="post" enctype="multipart/form-data" class="mode-form" data-mode="dual">
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

            <!-- LLM設定セクション (デュアルファイル用) -->
            <div class="form-group">
                <div class="checkbox-wrapper">
                    <input type="checkbox" id="use_llm2" name="use_llm" value="true" onclick="toggleLLMConfig2()">
                    <label for="use_llm2" class="checkbox-label">🤖 LLMベース判定を使用</label>
                </div>
            </div>

            <div id="llm_config_section2" class="llm-config-section" style="display: none;">
                <div class="form-group">
                    <label for="prompt_file2">プロンプトファイル</label>
                    <div class="file-input-wrapper">
                        <label for="prompt_file2" class="file-input-button" id="promptFileLabel2">
                            📄 プロンプトファイルを選択（.yaml）
                        </label>
                        <input type="file" id="prompt_file2" name="prompt_file" accept=".yaml,.yml">
                    </div>
                </div>

                <div class="form-group">
                    <label for="model_name2">LLMモデル名</label>
                    <input type="text" id="model_name2" name="model_name" placeholder="qwen3-14b-awq" value="qwen3-14b-awq">
                </div>

                <div class="form-group">
                    <div class="file-inputs-row">
                        <div>
                            <label for="temperature2">生成温度</label>
                            <input type="number" id="temperature2" name="temperature" min="0" max="1" step="0.1" value="0.2">
                        </div>
                        <div>
                            <label for="max_tokens2">最大トークン数</label>
                            <input type="number" id="max_tokens2" name="max_tokens" min="1" max="512" value="64">
                        </div>
                    </div>
                </div>
            </div>

            <button type="submit" class="submit-button" id="dualSubmitButton">
                🔀 2ファイルの列を比較
            </button>
        </form>

        <!-- 進捗表示セクション -->
        <div id="progress-section" class="progress-section" style="display: none;">
            <div id="progress-container" class="progress-container">
                <h3 class="progress-title">📊 処理進捗</h3>

                <!-- プログレスバー -->
                <div class="progress-bar-container">
                    <progress id="progress-bar" class="progress-bar" max="100" value="0"></progress>
                    <div class="progress-labels">
                        <span id="progress-percentage" class="progress-percentage">0%</span>
                        <span id="progress-text" class="progress-text">
                            <span id="progress-current">0</span>/<span id="progress-total">0</span>行
                        </span>
                    </div>
                </div>

                <!-- 時間情報 -->
                <div class="time-info">
                    <div class="time-item">
                        <span class="time-label">経過時間:</span>
                        <span id="elapsed-time" class="time-value">00:00:00</span>
                    </div>
                    <div class="time-item">
                        <span class="time-label">推定残り時間:</span>
                        <span id="remaining-time" class="time-value">計算中...</span>
                    </div>
                    <div class="time-item">
                        <span class="time-label">処理速度:</span>
                        <span id="processing-speed" class="time-value">-- 行/秒</span>
                    </div>
                </div>

                <!-- ステータスメッセージ -->
                <div id="status-message" class="status-message" style="display: none;"></div>

                <!-- エラーメッセージ -->
                <div id="error-message" class="error-message" style="display: none;"></div>

                <!-- 警告メッセージ -->
                <div id="warning-message" class="warning-message" style="display: none;"></div>

                <!-- ユーザーインタラクション要素 -->
                <div class="interaction-controls">
                    <!-- キャンセルボタン -->
                    <button id="cancel-button" class="cancel-button" style="display: none;">
                        ❌ 処理をキャンセル
                    </button>

                    <!-- 再試行ボタン -->
                    <button id="retry-button" class="retry-button" style="display: none;">
                        🔄 再試行
                    </button>

                    <!-- 部分結果ダウンロードボタン -->
                    <button id="download-partial-results" class="download-button" style="display: none;">
                        💾 部分結果をダウンロード
                    </button>
                </div>

                <!-- ファイル分割提案 -->
                <div id="split-suggestion" class="split-suggestion" style="display: none;">
                    <div class="split-suggestion-content">
                        <h4>📂 ファイルサイズ分割提案</h4>
                        <p class="split-message">ファイルが大きすぎるため、処理を分割することをお勧めします。</p>
                        <div class="split-details">
                            <span id="suggested-split-size" class="split-size">推奨分割サイズ: 計算中...</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>

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

        // LLM設定の表示/非表示切り替え（単一ファイル用）
        function toggleLLMConfig() {
            const useLLMCheckbox = document.getElementById('use_llm');
            const llmConfigSection = document.getElementById('llm_config_section');

            if (useLLMCheckbox.checked) {
                llmConfigSection.style.display = 'block';
                llmConfigSection.classList.add('active');
            } else {
                llmConfigSection.style.display = 'none';
                llmConfigSection.classList.remove('active');
            }
        }

        // 進捗表示関数
        function showProgress() {
            const progressSection = document.getElementById('progress-section');
            progressSection.style.display = 'block';
        }

        function hideProgress() {
            const progressSection = document.getElementById('progress-section');
            progressSection.style.display = 'none';
        }

        function formatTime(seconds) {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = Math.floor(seconds % 60);

            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }

        function updateProgress(progressData) {
            // プログレスバーを更新
            const progressBar = document.getElementById('progress-bar');
            const progressPercentage = document.getElementById('progress-percentage');
            const progressCurrent = document.getElementById('progress-current');
            const progressTotal = document.getElementById('progress-total');
            const elapsedTime = document.getElementById('elapsed-time');
            const remainingTime = document.getElementById('remaining-time');
            const processingSpeed = document.getElementById('processing-speed');

            if (progressBar) progressBar.value = progressData.percentage || 0;
            if (progressPercentage) progressPercentage.textContent = `${Math.round(progressData.percentage || 0)}%`;
            if (progressCurrent) progressCurrent.textContent = progressData.current || 0;
            if (progressTotal) progressTotal.textContent = progressData.total || 0;
            if (elapsedTime) elapsedTime.textContent = formatTime(progressData.elapsed_seconds || 0);

            if (remainingTime) {
                if (progressData.remaining_seconds) {
                    remainingTime.textContent = formatTime(progressData.remaining_seconds);
                } else {
                    remainingTime.textContent = '計算中...';
                }
            }

            if (processingSpeed) {
                const speed = progressData.processing_speed || 0;
                processingSpeed.textContent = `${speed.toFixed(2)} 行/秒`;
            }
        }

        function showError(message) {
            const errorDiv = document.getElementById('error-message');
            if (errorDiv) {
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
            }
        }

        function showWarning(message) {
            const warningDiv = document.getElementById('warning-message');
            if (warningDiv) {
                warningDiv.textContent = message;
                warningDiv.style.display = 'block';
            }
        }

        function showStatus(message) {
            const statusDiv = document.getElementById('status-message');
            if (statusDiv) {
                statusDiv.textContent = message;
                statusDiv.style.display = 'block';
            }
        }

        function clearMessages() {
            const errorDiv = document.getElementById('error-message');
            const warningDiv = document.getElementById('warning-message');
            const statusDiv = document.getElementById('status-message');

            if (errorDiv) errorDiv.style.display = 'none';
            if (warningDiv) warningDiv.style.display = 'none';
            if (statusDiv) statusDiv.style.display = 'none';
        }

        // Polling クライアント機能
        let currentPollingInterval = null;
        let currentTaskId = null;
        let pollingErrorCount = 0;
        const maxPollingErrors = 5;

        // SSE互換性のための変数（レガシー）
        const maxReconnectAttempts = 5;
        let currentReconnectAttempts = 0;

        function startPolling(taskId) {
            // 既存のポーリングがあれば停止
            if (currentPollingInterval) {
                stopPolling();
            }

            currentTaskId = taskId;
            pollingErrorCount = 0;

            // 1秒ごとにポーリング
            currentPollingInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/progress/${taskId}`);

                    if (!response.ok) {
                        if (response.status === 404) {
                            console.error('Task not found:', taskId);
                            stopPolling();
                            showError('タスクが見つかりません');
                            return;
                        }
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const data = await response.json();

                    // 進捗更新
                    updateProgress(data);

                    // エラー状態の場合
                    if (data.status === 'error') {
                        stopPolling();
                        showError(data.error_message || 'エラーが発生しました');
                    }
                    // 完了状態の場合
                    else if (data.status === 'completed') {
                        stopPolling();
                        handlePollingComplete(data);
                    }

                    // エラーカウンターをリセット
                    pollingErrorCount = 0;

                } catch (error) {
                    console.error('Polling error:', error);
                    pollingErrorCount++;

                    // 最大エラー数を超えた場合は停止
                    if (pollingErrorCount >= maxPollingErrors) {
                        stopPolling();
                        showError(`接続エラーが続いたため、処理を停止しました (${pollingErrorCount}回連続失敗)`);
                    }
                }
            }, 1000); // 1秒間隔

            console.log(`Started polling for task: ${taskId}`);
        }

        function stopPolling() {
            if (currentPollingInterval) {
                clearInterval(currentPollingInterval);
                currentPollingInterval = null;
                console.log('Stopped polling');
            }
            currentTaskId = null;
        }


        function handleSSEError(event) {
            console.error('SSE connection error:', event);

            // ポーリングエラーは自動的に処理される
            console.log('Polling errors are handled automatically');
        }

        function handlePollingComplete(data) {
            stopPolling();
            displayCompletionMessage(data);

            // ポーリング時は結果がdataに含まれている
            if (data.result) {
                showResults(data);  // data全体を渡す（data.resultではなく）
            } else {
                showResults(data);
            }
        }

        // ポーリングモードでは再接続ロジックは不要（自動リトライ）

        function showResults(data) {
            hideProgress();

            // 既存の結果セクションを削除
            const existingResults = document.querySelectorAll('[id*="result"], [id*="complete-results"]');
            existingResults.forEach(el => el.remove());

            // 結果データがある場合のみ表示
            if (data && data.result) {
                // 新しい結果セクションを動的に作成
                const resultDiv = document.createElement('div');
                resultDiv.id = 'resultContainer';
                resultDiv.style.cssText = 'padding: 20px; margin: 20px 0; border: 2px solid #28a745; border-radius: 8px; background: #f8fff9;';

                let resultHTML = '';

                // 配列形式（ファイル出力）かオブジェクト形式（スコア出力）かを判定
                if (Array.isArray(data.result)) {
                    // ファイル（詳細結果）形式の場合
                    resultHTML = `
                        <h3 style="color: #28a745; margin-bottom: 15px;">✅ 処理完了 - ファイル形式</h3>
                        <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0;">
                            <h4>📊 詳細比較結果</h4>
                            <p><strong>総レコード数:</strong> ${data.result.length}</p>
                        </div>
                        <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0; max-height: 400px; overflow-y: auto;">
                            <h4>📋 各レコードの詳細</h4>
                            ${data.result.map((item, index) => {
                                // inference1/2が文字列の場合はパースを試みる
                                let inf1 = item.inference1;
                                let inf2 = item.inference2;

                                if (typeof inf1 === 'string') {
                                    try {
                                        inf1 = JSON.parse(inf1);
                                    } catch (e) {
                                        inf1 = {response: inf1};
                                    }
                                }
                                if (typeof inf2 === 'string') {
                                    try {
                                        inf2 = JSON.parse(inf2);
                                    } catch (e) {
                                        inf2 = {response: inf2};
                                    }
                                }

                                // 入力テキストの表示
                                const inputText = item.input || '';

                                // 推論結果の取得（response, text, scoreなど様々なフィールドに対応）
                                const inf1Text = inf1?.response || inf1?.text || (typeof inf1 === 'object' ? JSON.stringify(inf1) : inf1) || 'N/A';
                                const inf1Score = inf1?.score !== undefined ? inf1.score : '';
                                const inf2Text = inf2?.response || inf2?.text || (typeof inf2 === 'object' ? JSON.stringify(inf2) : inf2) || 'N/A';
                                const inf2Score = inf2?.score !== undefined ? inf2.score : '';

                                return `
                                <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px;">
                                    <h5>レコード ${index + 1}</h5>
                                    ${inputText ? `<p><strong>入力:</strong> ${inputText.substring(0, 100)}${inputText.length > 100 ? '...' : ''}</p>` : ''}
                                    <p><strong>推論1:</strong> ${inf1Text}</p>
                                    ${inf1Score !== '' ? `<p><strong>推論1スコア:</strong> ${inf1Score}</p>` : ''}
                                    <p><strong>推論2:</strong> ${inf2Text}</p>
                                    ${inf2Score !== '' ? `<p><strong>推論2スコア:</strong> ${inf2Score}</p>` : ''}
                                    <p><strong>類似度スコア:</strong> ${item.similarity_score !== undefined ? item.similarity_score : 'N/A'}</p>
                                    <p><strong>フィールド一致率:</strong> ${item.similarity_details?.field_match_ratio !== undefined ? item.similarity_details.field_match_ratio : 'N/A'}</p>
                                    <p><strong>値類似度:</strong> ${item.similarity_details?.value_similarity !== undefined ? item.similarity_details.value_similarity : 'N/A'}</p>
                                </div>
                            `;
                            }).join('')}
                        </div>
                    `;
                } else {
                    // スコア（全体平均）形式の場合
                    // LLMモードとEmbeddingモードで構造が異なる
                    let score, meaning, totalLines, calculationMethod, processingTime, gpuUsed, outputType;
                    let fieldMatchRatio = 'N/A', valueSimilarity = 'N/A', finalScore = 'N/A';

                    if (data.result.summary) {
                        // LLMモードの場合
                        score = data.result.summary.average_score;
                        totalLines = data.result.summary.total_comparisons;
                        // スコアから意味を判定
                        if (score >= 0.8) meaning = '高い類似度';
                        else if (score >= 0.5) meaning = '中程度の類似度';
                        else meaning = '低い類似度';

                        calculationMethod = data.result._metadata?.calculation_method || 'N/A';
                        processingTime = data.result._metadata?.processing_time || 'N/A';
                        gpuUsed = data.result._metadata?.gpu_used ? 'Yes' : 'No';
                        outputType = data.result._metadata?.output_type || 'N/A';

                        // LLMモードの詳細データ（summaryから取得）
                        fieldMatchRatio = data.result.summary.score_distribution ?
                            `最高: ${data.result.summary.score_distribution.max}, 最低: ${data.result.summary.score_distribution.min}` :
                            'N/A';
                        valueSimilarity = data.result.summary.confidence_level || 'N/A';
                        finalScore = data.result.summary.average_score || 'N/A';
                    } else {
                        // Embeddingモードの場合
                        score = data.result.score;
                        meaning = data.result.meaning;
                        totalLines = data.result.total_lines;
                        calculationMethod = data.result._metadata?.calculation_method || 'N/A';
                        processingTime = data.result._metadata?.processing_time || 'N/A';
                        gpuUsed = data.result._metadata?.gpu_used ? 'Yes' : 'No';
                        outputType = data.result._metadata?.output_type || 'N/A';

                        // 詳細データ
                        fieldMatchRatio = data.result.json?.field_match_ratio || 'N/A';
                        valueSimilarity = data.result.json?.value_similarity || 'N/A';
                        finalScore = data.result.json?.final_score || 'N/A';
                    }

                    resultHTML = `
                        <h3 style="color: #28a745; margin-bottom: 15px;">✅ 処理完了 - スコア形式</h3>
                        <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0;">
                            <h4>📊 類似度結果</h4>
                            <p><strong>スコア:</strong> <span style="font-size: 18px; color: #dc3545; font-weight: bold;">${score}</span></p>
                            <p><strong>意味:</strong> ${meaning}</p>
                            <p><strong>処理行数:</strong> ${totalLines}</p>
                            <p><strong>計算方法:</strong> ${calculationMethod}</p>
                            <p><strong>処理時間:</strong> ${processingTime}</p>
                        </div>

                        <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0;">
                            <h4>📋 詳細データ</h4>
                            ${calculationMethod === 'llm' ? `
                                <p><strong>スコア分布:</strong> ${fieldMatchRatio}</p>
                                <p><strong>信頼度レベル:</strong> ${valueSimilarity}</p>
                                <p><strong>平均スコア:</strong> ${finalScore}</p>
                            ` : `
                                <p><strong>フィールド一致率:</strong> ${fieldMatchRatio}</p>
                                <p><strong>値類似度:</strong> ${valueSimilarity}</p>
                                <p><strong>最終スコア:</strong> ${finalScore}</p>
                            `}
                        </div>

                        <div style="background: #e9ecef; padding: 15px; border-radius: 6px; margin: 10px 0;">
                            <h4>🔧 処理情報</h4>
                            <p><strong>GPU使用:</strong> ${gpuUsed}</p>
                            <p><strong>出力形式:</strong> ${outputType}</p>
                        </div>
                    `;
                }

                resultDiv.innerHTML = resultHTML;

                // 結果をページの上部に挿入
                document.body.insertBefore(resultDiv, document.body.firstChild);

                console.log('Results displayed successfully:', data.result);
            }

            // ダウンロードボタンは結果セクション内に含まれているため、ここでは処理不要
            console.log('showResults function completed');
        }

        function hideResults() {
            const resultsSection = document.getElementById('resultContainer');
            if (resultsSection) {
                resultsSection.style.display = 'none';
            }
        }

        function displayCompletionMessage(data) {
            const message = data.error_message ?
                `処理が完了しましたが、エラーが発生しました: ${data.error_message}` :
                `処理が正常に完了しました (${data.current}/${data.total})`;

            showStatus(message);
        }

        // ユーザーインタラクション機能
        // currentTaskId は上で既に宣言済み

        function cancelProcessing() {
            if (currentTaskId) {
                // SSE接続を切断
                stopPolling();

                // UIをリセット
                hideProgress();
                showStatus('処理がキャンセルされました');

                // キャンセルボタンを非表示
                const cancelBtn = document.getElementById('cancel-button');
                if (cancelBtn) cancelBtn.style.display = 'none';

                currentTaskId = null;
            }
        }

        function retryProcessing() {
            // 再試行ボタンを非表示
            const retryBtn = document.getElementById('retry-button');
            if (retryBtn) retryBtn.style.display = 'none';

            // エラーメッセージをクリア
            clearMessages();

            // 処理を再開（実際のファイル再処理は別途実装）
            showStatus('処理を再試行しています...');
        }

        function showRetryButton() {
            const retryBtn = document.getElementById('retry-button');
            if (retryBtn) {
                retryBtn.style.display = 'block';
            }
        }

        function downloadPartialResults() {
            if (currentTaskId) {
                // 部分結果のダウンロード処理（実際のダウンロード機能は別途実装）
                showStatus('部分結果をダウンロードしています...');

                // 模擬的なダウンロード処理
                setTimeout(() => {
                    showStatus('部分結果のダウンロードが完了しました');
                }, 1000);
            }
        }

        function enablePartialDownload() {
            const downloadBtn = document.getElementById('download-partial-results');
            if (downloadBtn) {
                downloadBtn.style.display = 'block';
            }
        }

        function showSplitSuggestion(fileSize, optimalSize) {
            const splitDiv = document.getElementById('split-suggestion');
            const splitSizeSpan = document.getElementById('suggested-split-size');

            if (splitDiv && splitSizeSpan) {
                const suggestedSize = optimalSize || calculateOptimalSplitSize(fileSize);
                splitSizeSpan.textContent = `推奨分割サイズ: ${suggestedSize}行`;
                splitDiv.style.display = 'block';
            }
        }

        function hideSplitSuggestion() {
            const splitDiv = document.getElementById('split-suggestion');
            if (splitDiv) {
                splitDiv.style.display = 'none';
            }
        }

        function calculateOptimalSplitSize(fileSize) {
            // ファイルサイズに基づいて最適な分割サイズを計算
            if (fileSize > 100000) {
                return Math.floor(fileSize / 10); // 10分割
            } else if (fileSize > 50000) {
                return Math.floor(fileSize / 5); // 5分割
            } else if (fileSize > 10000) {
                return Math.floor(fileSize / 2); // 2分割
            }
            return fileSize; // 分割不要
        }

        // 進捗表示機能をwindowオブジェクトに追加（テスト用）
        window.updateProgress = updateProgress;
        window.showProgress = showProgress;
        window.hideProgress = hideProgress;
        window.formatTime = formatTime;
        window.showError = showError;
        window.showWarning = showWarning;
        window.showStatus = showStatus;
        window.clearMessages = clearMessages;

        // SSE機能をwindowオブジェクトに追加（テスト用）
        // Polling functions for global access
        window.startPolling = startPolling;
        window.stopPolling = stopPolling;
        window.handlePollingComplete = handlePollingComplete;
        window.handleSSEError = handleSSEError; // Keep for compatibility
        window.maxReconnectAttempts = maxReconnectAttempts;
        window.currentReconnectAttempts = currentReconnectAttempts;
        window.showResults = showResults;
        window.hideResults = hideResults;
        window.displayCompletionMessage = displayCompletionMessage;

        // ユーザーインタラクション機能をwindowオブジェクトに追加（テスト用）
        window.cancelProcessing = cancelProcessing;
        window.retryProcessing = retryProcessing;
        window.showRetryButton = showRetryButton;
        window.downloadPartialResults = downloadPartialResults;
        window.enablePartialDownload = enablePartialDownload;
        window.showSplitSuggestion = showSplitSuggestion;
        window.hideSplitSuggestion = hideSplitSuggestion;
        window.calculateOptimalSplitSize = calculateOptimalSplitSize;

        // 既存WebUI改修機能
        function handleAsyncUpload(formData, formElement) {
            // 非同期アップロード処理
            showProgress();

            // フォームをFetch APIで送信
            const actionUrl = formElement.action;

            fetch(actionUrl, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.task_id) {
                    currentTaskId = data.task_id;
                    startPolling(data.task_id);
                } else {
                    displayUnifiedError('非同期処理の開始に失敗しました');
                }
            })
            .catch(error => {
                handleFormError(error, formElement);
            });
        }

        function startAsyncProcessing(formElement) {
            // フォームバリデーション
            if (!validateForm(formElement)) {
                return false;
            }

            // フォームデータを準備
            const formData = new FormData(formElement);

            // 非同期アップロードを開始
            handleAsyncUpload(formData, formElement);

            return false; // フォームの通常送信を防ぐ
        }

        function validateForm(formElement) {
            // 基本的なフォームバリデーション
            const fileInputs = formElement.querySelectorAll('input[type="file"]');

            for (let fileInput of fileInputs) {
                if (fileInput.required && !fileInput.files.length) {
                    displayUnifiedError(`${fileInput.name}ファイルを選択してください`);
                    return false;
                }
            }

            // ファイルサイズチェック
            for (let fileInput of fileInputs) {
                if (fileInput.files.length > 0) {
                    const file = fileInput.files[0];
                    const maxSize = 100 * 1024 * 1024; // 100MB

                    if (file.size > maxSize) {
                        showSplitSuggestion(file.size);
                        return false;
                    }
                }
            }

            return true;
        }

        function handleFormError(error, formElement) {
            console.error('Form submission error:', error);

            hideProgress();

            let errorMessage = 'ファイルアップロードエラーが発生しました';
            if (error.message) {
                errorMessage += ': ' + error.message;
            }

            displayUnifiedError(errorMessage);
            showRetryButton();
        }

        function displayUnifiedError(message) {
            // 既存のエラー表示と統合
            showError(message);

            // 追加のエラー処理
            const errorDiv = document.getElementById('error-message');
            if (errorDiv) {
                errorDiv.style.display = 'block';
                errorDiv.textContent = message;
            }
        }

        // フォームにイベントリスナーを設定
        function setupAsyncFormHandlers() {
            const uploadForm = document.getElementById('uploadForm');
            const dualForm = document.getElementById('dualForm');

            if (uploadForm) {
                uploadForm.onsubmit = function(e) {
                    e.preventDefault();
                    return startAsyncProcessing(this);
                };
            }

            if (dualForm) {
                dualForm.onsubmit = function(e) {
                    e.preventDefault();
                    return startAsyncProcessing(this);
                };
            }
        }

        // 既存WebUI改修機能をwindowオブジェクトに追加（テスト用）
        window.handleAsyncUpload = handleAsyncUpload;
        window.startAsyncProcessing = startAsyncProcessing;
        window.validateForm = validateForm;
        window.handleFormError = handleFormError;
        window.displayUnifiedError = displayUnifiedError;

        // ページ読み込み完了時にフォームハンドラを設定
        document.addEventListener('DOMContentLoaded', setupAsyncFormHandlers);

        // LLM設定の表示/非表示切り替え（デュアルファイル用）
        function toggleLLMConfig2() {
            const useLLMCheckbox = document.getElementById('use_llm2');
            const llmConfigSection = document.getElementById('llm_config_section2');

            if (useLLMCheckbox.checked) {
                llmConfigSection.style.display = 'block';
                llmConfigSection.classList.add('active');
            } else {
                llmConfigSection.style.display = 'none';
                llmConfigSection.classList.remove('active');
            }
        }

        // プロンプトファイル選択時の表示更新（単一ファイル用）
        const promptFileInput = document.getElementById('prompt_file');
        const promptFileLabel = document.getElementById('promptFileLabel');

        if (promptFileInput) {
            promptFileInput.addEventListener('change', function() {
                if (this.files && this.files.length > 0) {
                    const fileName = this.files[0].name;
                    promptFileLabel.textContent = `✅ ${fileName}`;
                    promptFileLabel.classList.add('file-selected');
                } else {
                    promptFileLabel.textContent = '📄 プロンプトファイルを選択（.yaml）';
                    promptFileLabel.classList.remove('file-selected');
                }
            });
        }

        // プロンプトファイル選択時の表示更新（デュアルファイル用）
        const promptFileInput2 = document.getElementById('prompt_file2');
        const promptFileLabel2 = document.getElementById('promptFileLabel2');

        if (promptFileInput2) {
            promptFileInput2.addEventListener('change', function() {
                if (this.files && this.files.length > 0) {
                    const fileName = this.files[0].name;
                    promptFileLabel2.textContent = `✅ ${fileName}`;
                    promptFileLabel2.classList.add('file-selected');
                } else {
                    promptFileLabel2.textContent = '📄 プロンプトファイルを選択（.yaml）';
                    promptFileLabel2.classList.remove('file-selected');
                }
            });
        }


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
            "compare_single": "POST /api/compare/single",
            "compare_dual": "POST /api/compare/dual",
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


# LLM機能統合API
@app.post("/api/compare/llm")
async def compare_with_llm(
    file: UploadFile = File(...),
    type: str = Form("score"),
    gpu: str = Form("false"),
    use_llm: str = Form("false"),
    model: str = Form("qwen3-14b-awq"),
    temperature: float = Form(0.2),
    max_tokens: int = Form(64)
):
    """LLM付き比較API（FormData対応）"""
    start_time = time.time()
    processing_time = 0
    temp_file_created = False
    temp_filepath = ""
    error_id = None
    client_ip = "127.0.0.1"  # Web UI経由の場合

    try:
        # ファイル検証
        if not file.filename.endswith('.jsonl'):
            raise HTTPException(status_code=400, detail="JSONLファイルのみサポートされています")

        # ファイル内容読み込み
        file_content = await file.read()
        file_content = file_content.decode('utf-8')

        # 一時ファイル作成
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write(file_content)
            temp_filepath = f.name
            temp_file_created = True

        # LLM設定の準備
        use_llm_bool = use_llm.lower() == "true"
        gpu_bool = gpu.lower() == "true"

        try:
            if use_llm_bool:
                try:
                    # LLMベース処理
                    config = {
                        "model": model,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "type": type
                    }
                    result = await process_jsonl_file_with_llm(temp_filepath, config)

                    # メタデータにcalculation_methodを追加
                    if isinstance(result, dict):
                        if "_metadata" not in result:
                            result["_metadata"] = {}
                        result["_metadata"]["calculation_method"] = "llm"
                        result["_metadata"]["original_filename"] = file.filename
                        result["_metadata"]["gpu_used"] = gpu_bool

                except Exception as llm_error:
                    # フォールバックとして埋め込みベース処理を実行
                    print(f"LLM計算に失敗、埋め込みモードにフォールバック: {llm_error}")
                    result = process_jsonl_file(temp_filepath, type, gpu_bool)

                    # 結果にフォールバックメタデータを追加
                    if isinstance(result, dict):
                        if "_metadata" not in result:
                            result["_metadata"] = {}
                        result["_metadata"]["calculation_method"] = "embedding"
                        result["_metadata"]["fallback_reason"] = f"LLM処理失敗: {str(llm_error)}"
                        result["_metadata"]["original_filename"] = file.filename
                        result["_metadata"]["gpu_used"] = gpu_bool
            else:
                # 通常の埋め込みベース処理
                result = process_jsonl_file(temp_filepath, type, gpu_bool)
                # メタデータを追加
                if isinstance(result, dict):
                    if "_metadata" not in result:
                        result["_metadata"] = {}
                    result["_metadata"]["calculation_method"] = "embedding"
                    result["_metadata"]["original_filename"] = file.filename
                    result["_metadata"]["gpu_used"] = gpu_bool

            processing_time = time.time() - start_time

            # 処理時間をメタデータに追加
            if isinstance(result, dict) and "_metadata" in result:
                result["_metadata"]["processing_time"] = f"{processing_time:.2f}秒"

            # numpy型をPython標準型に変換してJSONシリアライゼーションエラーを防ぐ
            result = convert_numpy_types(result)

            return result

        finally:
            # 一時ファイルのクリーンアップ
            if temp_file_created and os.path.exists(temp_filepath):
                try:
                    os.unlink(temp_filepath)
                except Exception as cleanup_error:
                    print(f"一時ファイル削除エラー: {cleanup_error}")

    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_id = str(uuid.uuid4())
        print(f"LLM API エラー: {e}")
        raise HTTPException(status_code=500, detail=f"処理中にエラーが発生しました: {str(e)}")


@app.post("/api/compare/dual/llm")
async def compare_dual_with_llm(request: DualFileCompareRequestWithLLM):
    """LLM付きデュアルファイル比較API"""
    try:
        # LLM設定の検証
        if request.use_llm and request.llm_config:
            validate_llm_config(request.llm_config.model_dump())

        # 一時ファイルに内容を書き込み
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f1:
            f1.write(request.file1_content)
            temp_file1_path = f1.name

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f2:
            f2.write(request.file2_content)
            temp_file2_path = f2.name

        try:
            if request.use_llm:
                # LLMベース処理
                config = request.llm_config.model_dump() if request.llm_config else {}
                config["type"] = request.type
                result = await process_dual_files_with_llm(
                    temp_file1_path, temp_file2_path, request.column, config
                )
            else:
                # 通常の埋め込みベース処理（既存機能を使用）
                extractor = DualFileExtractor()
                result = extractor.compare_dual_files(
                    temp_file1_path, temp_file2_path, request.column, request.type
                )

            return result

        finally:
            # 一時ファイルのクリーンアップ
            os.unlink(temp_file1_path)
            os.unlink(temp_file2_path)

    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.log_error(error_id, "llm_dual_api_error", str(e), context={"request_type": "dual_compare_llm"})
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prompts/upload", response_model=PromptUploadResponse)
async def upload_prompt(file: UploadFile = File(...)):
    """プロンプトファイルアップロードAPI"""
    try:
        if not file.filename.endswith(('.yaml', '.yml')):
            raise HTTPException(status_code=400, detail="プロンプトファイルは.yamlまたは.yml形式である必要があります")

        # ファイル内容を読み取り
        content = await file.read()

        # YAML形式の検証
        import yaml
        try:
            prompt_data = yaml.safe_load(content.decode('utf-8'))
            validate_prompt_file(prompt_data)
        except yaml.YAMLError:
            raise HTTPException(status_code=400, detail="無効なYAML形式です")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # プロンプトファイルを保存（一意のIDを生成）
        prompt_id = str(uuid.uuid4())
        prompt_dir = Path("prompts")
        prompt_dir.mkdir(exist_ok=True)

        saved_path = prompt_dir / f"{prompt_id}.yaml"
        with open(saved_path, 'wb') as f:
            f.write(content)

        return PromptUploadResponse(
            status="success",
            prompt_id=prompt_id,
            message=f"プロンプトファイルが保存されました: {file.filename}"
        )

    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.log_error(error_id, "prompt_upload_error", str(e), context={"request_type": "prompt_upload"})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/prompts", response_model=PromptListResponse)
async def list_prompts():
    """プロンプト一覧取得API"""
    try:
        prompt_dir = Path("prompts")
        prompts = []

        # デフォルトプロンプトを追加
        prompts.append({
            "name": "default_similarity.yaml",
            "id": "default",
            "description": "デフォルトの類似度判定プロンプト"
        })

        # アップロードされたプロンプトを追加
        if prompt_dir.exists():
            for prompt_file in prompt_dir.glob("*.yaml"):
                if prompt_file.stem != "default_similarity":
                    prompts.append({
                        "name": prompt_file.name,
                        "id": prompt_file.stem,
                        "description": f"カスタムプロンプト: {prompt_file.name}"
                    })

        return PromptListResponse(prompts=prompts)

    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.log_error(error_id, "prompt_list_error", str(e), context={"request_type": "prompt_list"})
        raise HTTPException(status_code=500, detail=str(e))


# === WebUI進捗表示システム: SSE配信とタスク管理API ===

@app.get("/api/progress/stream/{task_id}")
async def stream_progress(task_id: str, request: Request):
    """SSE (Server-Sent Events) で進捗をリアルタイム配信"""

    async def event_generator():
        try:
            # 進捗をストリーミング
            async for event in progress_tracker.stream_progress(task_id, timeout=300.0):
                # クライアント接続確認
                if await request.is_disconnected():
                    break

                yield event

        except Exception as e:
            error_id = str(uuid.uuid4())
            logger.log_error(error_id, "sse_streaming_error", str(e), context={
                "task_id": task_id
            })
            yield {
                "event": "error",
                "data": json.dumps({
                    "error_message": f"ストリーミングエラーが発生しました: {str(e)}",
                    "error_id": error_id
                })
            }

    return EventSourceResponse(event_generator())


@app.get("/api/progress/{task_id}")
async def get_task_progress(task_id: str):
    """特定タスクの進捗状況を取得（ポーリング用）

    処理完了時は結果データも含めて返却する
    """
    try:
        progress = progress_tracker.get_progress(task_id)
        if progress is None:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        response_data = {
            "task_id": progress.task_id,
            "current": progress.current,
            "total": progress.total,
            "percentage": progress.percentage,
            "elapsed_seconds": progress.elapsed_time,
            "estimated_remaining_seconds": progress.estimated_remaining,
            "status": progress.status,
            "error_message": progress.error_message,
            "processing_speed": progress.processing_speed,
            "slow_processing_warning": progress.slow_processing_warning
        }

        # 処理完了時は結果データを含める
        if progress.status == "completed" and task_id in progress_tracker.tasks:
            task = progress_tracker.tasks[task_id]
            if task.result:
                response_data["result"] = task.result

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.log_error(error_id, "progress_get_error", str(e), context={
            "task_id": task_id
        })
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare/async")
async def compare_async(
    file: UploadFile = File(...),
    type: str = Form("score"),
    gpu: bool = Form(False),
    use_llm: bool = Form(False)
):
    """非同期でファイル比較を実行し、タスクIDを返す"""
    try:
        # ファイルを一時保存
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.jsonl', delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # ファイル行数を推定してタスクを作成
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)

        # 進捗トラッカーにタスクを作成（タスクIDを取得）
        task_id = progress_tracker.create_task(total_items=total_lines)

        # バックグラウンドで比較処理を開始
        asyncio.create_task(
            process_comparison_async(task_id, temp_file_path, type, gpu, use_llm)
        )

        return {
            "task_id": task_id,
            "message": "比較処理を開始しました",
            "total_items": total_lines,
            "status": "processing"
        }

    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.log_error(error_id, "async_compare_start_error", str(e))
        raise HTTPException(status_code=500, detail=f"非同期処理の開始に失敗しました: {str(e)}")


async def process_comparison_async(task_id: str, file_path: str, output_type: str, gpu: bool, use_llm: bool = False):
    """バックグラウンドでファイル比較を実行"""
    start_time = time.time()

    try:
        # GPU設定
        if gpu:
            set_gpu_mode(True)

        # tqdm出力をキャプチャして進捗更新
        with tqdm_interceptor.capture_tqdm(task_id, progress_tracker):
            # LLMベース判定を使用する場合
            if use_llm:
                # LLM付き処理を実行
                config = {
                    "type": output_type,
                    "model": "qwen3-14b-awq",  # デフォルトモデル
                    "temperature": 0.2,
                    "max_tokens": 64
                }
                result = await process_jsonl_file_with_llm(file_path, config)
                # 実際に使用された方法を判定（method_breakdownから）
                if isinstance(result, dict):
                    method_breakdown = result.get("summary", {}).get("method_breakdown", {})
                    # 最も使用された方法を判定
                    if method_breakdown:
                        # embedding_fallbackがある場合はフォールバックが発生
                        if "embedding_fallback" in method_breakdown:
                            actual_method = "embedding_fallback"
                        # llmが含まれていればLLM処理成功
                        elif "llm" in method_breakdown:
                            actual_method = "llm"
                        # それ以外は埋め込みモード
                        else:
                            actual_method = "embedding"
                    else:
                        # method_breakdownがない場合はLLMとして扱う（後方互換性）
                        actual_method = "llm"
                    result["calculation_method"] = actual_method
            else:
                # 通常の埋め込みベース処理を実行
                result = await asyncio.get_event_loop().run_in_executor(
                    None, process_jsonl_file, file_path, output_type
                )

        # メタデータを追加
        if isinstance(result, dict):
            # resultに既にcalculation_methodがある場合はそれを使用
            existing_method = result.get("calculation_method", "embedding")

            # _metadataがまだ無い場合は新規作成、ある場合は更新
            if "_metadata" not in result:
                result["_metadata"] = {}

            result["_metadata"].update({
                "calculation_method": existing_method,  # 実際の推論方法を使用
                "processing_time": f"{time.time() - start_time:.2f}秒",
                "gpu_used": gpu,
                "output_type": output_type
            })

            # calculation_methodがトップレベルにある場合は削除（_metadataに移動済み）
            if "calculation_method" in result and result["calculation_method"] == existing_method:
                del result["calculation_method"]

        # 処理完了
        duration = time.time() - start_time
        progress_tracker.complete_task(task_id, success=True, result_data=result)
        progress_tracker.log_task_completion(task_id, success=True, duration=duration)

        # メトリクス記録
        progress_tracker.record_metrics(task_id, {
            "output_type": output_type,
            "gpu_enabled": gpu,
            "processing_duration": duration,
            "result_count": len(result) if isinstance(result, list) else 1
        })

    except Exception as e:
        duration = time.time() - start_time
        error_message = f"比較処理エラー: {str(e)}"

        progress_tracker.complete_task(task_id, success=False, error_message=error_message)
        progress_tracker.log_task_completion(task_id, success=False, duration=duration)
        progress_tracker.log_error(task_id, error_message, e)

    finally:
        # 一時ファイルをクリーンアップ
        try:
            os.unlink(file_path)
        except:
            pass


@app.post("/api/compare/dual/async")
async def compare_dual_async(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    column1: str = Form("inference1"),
    column2: str = Form("inference2"),
    output_type: str = Form("score"),
    gpu: bool = Form(False)
):
    """非同期で2ファイル比較を実行し、タスクIDを返す"""
    try:
        # タスクIDを生成
        task_id = str(uuid.uuid4())

        # ファイルを一時保存
        temp_files = []
        for file in [file1, file2]:
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.jsonl', delete=False) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_files.append(temp_file.name)

        # ファイル行数を推定してタスクを作成
        with open(temp_files[0], 'r', encoding='utf-8') as f:
            total_lines = sum(1 for _ in f)

        # 進捗トラッカーにタスクを作成
        progress_tracker.create_task(total_items=total_lines)
        progress_tracker.log_task_creation(task_id, total_lines)

        # バックグラウンドで比較処理を開始
        asyncio.create_task(
            process_dual_comparison_async(
                task_id, temp_files[0], temp_files[1], column1, column2, output_type, gpu
            )
        )

        return {
            "task_id": task_id,
            "message": "2ファイル比較処理を開始しました",
            "total_items": total_lines,
            "status": "processing"
        }

    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.log_error(error_id, "async_dual_compare_start_error", str(e))
        raise HTTPException(status_code=500, detail=f"非同期処理の開始に失敗しました: {str(e)}")


async def process_dual_comparison_async(
    task_id: str, file1_path: str, file2_path: str, column1: str, column2: str, output_type: str, gpu: bool
):
    """バックグラウンドで2ファイル比較を実行"""
    start_time = time.time()

    try:
        # GPU設定
        if gpu:
            set_gpu_mode(True)

        # DualFileExtractorで処理
        extractor = DualFileExtractor()

        # tqdm出力をキャプチャして進捗更新
        with tqdm_interceptor.capture_tqdm(task_id, progress_tracker):
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                extractor.process,
                file1_path, file2_path, column1, column2, output_type
            )

        # 処理完了
        duration = time.time() - start_time
        progress_tracker.complete_task(task_id, success=True, result_data=result)
        progress_tracker.log_task_completion(task_id, success=True, duration=duration)

        # メトリクス記録
        progress_tracker.record_metrics(task_id, {
            "comparison_type": "dual_file",
            "column1": column1,
            "column2": column2,
            "output_type": output_type,
            "gpu_enabled": gpu,
            "processing_duration": duration,
            "result_count": len(result) if isinstance(result, list) else 1
        })

    except Exception as e:
        duration = time.time() - start_time
        error_message = f"2ファイル比較処理エラー: {str(e)}"

        progress_tracker.complete_task(task_id, success=False, error_message=error_message)
        progress_tracker.log_task_completion(task_id, success=False, duration=duration)
        progress_tracker.log_error(task_id, error_message, e)

    finally:
        # 一時ファイルをクリーンアップ
        for file_path in [file1_path, file2_path]:
            try:
                os.unlink(file_path)
            except:
                pass


def main():
    """APIサーバーのメインエントリーポイント"""
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=18081, reload=False)


if __name__ == "__main__":
    main()