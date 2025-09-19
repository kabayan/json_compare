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
from fastapi.staticfiles import StaticFiles
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

# 静的ファイルの設定
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


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
    静的ファイルからHTMLを提供

    Returns:
        HTMLファイルの内容
    """
    static_file_path = Path(__file__).parent.parent / "static" / "index.html"

    if not static_file_path.exists():
        raise HTTPException(status_code=404, detail="UIファイルが見つかりません")

    with open(static_file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

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