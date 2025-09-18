"""拡張結果フォーマットモジュール

メタデータ管理と結果フォーマット拡張を実装。
既存フォーマットとの互換性を保ちながら、LLM固有メタデータや
パフォーマンス情報を含む拡張結果を提供。
"""

import time
import platform
import sys
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from .similarity_strategy import StrategyResult


@dataclass
class LLMMetadata:
    """LLM固有メタデータ - Requirement 5.5対応"""
    model_name: str
    prompt_file: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 64
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    prompt_version: Optional[str] = None
    system_prompt_hash: Optional[str] = None
    user_prompt_template: Optional[str] = None
    llm_version: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        """初期化後処理"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.llm_version is None:
            self.llm_version = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timestamp": self.timestamp,
            "llm_version": self.llm_version
        }

        # Optional fields
        if self.prompt_file:
            result["prompt_file"] = self.prompt_file
        if self.tokens_used is not None:
            result["tokens_used"] = self.tokens_used
        if self.prompt_tokens is not None:
            result["prompt_tokens"] = self.prompt_tokens
        if self.completion_tokens is not None:
            result["completion_tokens"] = self.completion_tokens
        if self.prompt_version:
            result["prompt_version"] = self.prompt_version
        if self.system_prompt_hash:
            result["system_prompt_hash"] = self.system_prompt_hash
        if self.user_prompt_template:
            result["user_prompt_template"] = self.user_prompt_template

        return result


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標 - Requirement 6.1対応"""
    api_call_time: float
    total_processing_time: float
    queue_wait_time: Optional[float] = None
    token_generation_rate: Optional[float] = None
    retry_count: int = 0
    retry_total_time: float = 0.0
    fallback_used: bool = False
    memory_usage_mb: Optional[float] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        """初期化後処理"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def calculate_efficiency_ratio(self) -> float:
        """効率比率の計算（API時間/総処理時間）"""
        if self.total_processing_time <= 0:
            return 0.0
        return self.api_call_time / self.total_processing_time

    def calculate_throughput(self, tokens_generated: int) -> float:
        """スループット計算（トークン/秒）"""
        if self.api_call_time <= 0:
            return 0.0
        return tokens_generated / self.api_call_time

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "api_call_time": self.api_call_time,
            "total_processing_time": self.total_processing_time,
            "retry_count": self.retry_count,
            "retry_total_time": self.retry_total_time,
            "fallback_used": self.fallback_used,
            "timestamp": self.timestamp
        }

        # Optional fields
        if self.queue_wait_time is not None:
            result["queue_wait_time"] = self.queue_wait_time
        if self.token_generation_rate is not None:
            result["token_generation_rate"] = self.token_generation_rate
        if self.memory_usage_mb is not None:
            result["memory_usage_mb"] = self.memory_usage_mb

        return result


@dataclass
class EnhancedResult:
    """拡張された類似度計算結果"""
    score: float
    method: str
    processing_time: float
    input_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None
    llm_metadata: Optional[LLMMetadata] = None
    performance_metrics: Optional[PerformanceMetrics] = None
    fallback_reason: Optional[str] = None
    original_method: Optional[str] = None

    def __post_init__(self):
        """初期化後処理"""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    @classmethod
    def from_strategy_result(
        cls,
        strategy_result: StrategyResult,
        input_data: Dict[str, Any]
    ) -> 'EnhancedResult':
        """
        StrategyResultから拡張結果を作成

        Args:
            strategy_result: 戦略パターンの結果
            input_data: 入力データ情報

        Returns:
            拡張結果インスタンス
        """
        return cls(
            score=strategy_result.score,
            method=strategy_result.method,
            processing_time=strategy_result.processing_time,
            input_data=input_data,
            metadata=strategy_result.metadata.copy()
        )

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "score": self.score,
            "method": self.method,
            "processing_time": self.processing_time,
            "input_data": self.input_data,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

        # LLMメタデータ
        if self.llm_metadata:
            result["llm_metadata"] = self.llm_metadata.to_dict()

        # パフォーマンス指標
        if self.performance_metrics:
            result["performance_metrics"] = self.performance_metrics.to_dict()

        # フォールバック情報
        if self.fallback_reason:
            result["fallback_reason"] = self.fallback_reason
        if self.original_method:
            result["original_method"] = self.original_method

        return result


class MetadataCollector:
    """メタデータ収集器"""

    def __init__(self):
        """初期化"""
        self.version = "1.0.0"  # アプリケーションバージョン

    def collect_system_metadata(self) -> Dict[str, Any]:
        """
        システムメタデータを収集

        Returns:
            システム情報の辞書
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "version": self.version,
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor() or "unknown"
        }

    def collect_performance_metadata(self, strategy_result: StrategyResult) -> Dict[str, Any]:
        """
        パフォーマンスメタデータを収集

        Args:
            strategy_result: 戦略結果

        Returns:
            パフォーマンス情報の辞書
        """
        processing_time = strategy_result.processing_time

        # 処理時間カテゴリの判定
        if processing_time < 0.5:
            performance_category = "fast"
        elif processing_time < 2.0:
            performance_category = "medium"
        else:
            performance_category = "slow"

        return {
            "processing_time": processing_time,
            "calculation_method": strategy_result.method,
            "performance_category": performance_category
        }

    def collect_llm_metadata(self, strategy_result: StrategyResult) -> Dict[str, Any]:
        """
        LLM固有メタデータを収集

        Args:
            strategy_result: LLM戦略結果

        Returns:
            LLMメタデータの辞書
        """
        metadata = strategy_result.metadata
        llm_metadata = {}

        # 基本LLM情報
        if "model_used" in metadata:
            llm_metadata["model_used"] = metadata["model_used"]
        if "confidence" in metadata:
            llm_metadata["confidence"] = metadata["confidence"]
        if "tokens_used" in metadata:
            llm_metadata["tokens_used"] = metadata["tokens_used"]
        if "category" in metadata:
            llm_metadata["category"] = metadata["category"]
        if "reason" in metadata:
            llm_metadata["reason"] = metadata["reason"]

        # 計算メトリクス
        if "tokens_used" in metadata and strategy_result.processing_time > 0:
            tokens_per_second = metadata["tokens_used"] / strategy_result.processing_time
            llm_metadata["tokens_per_second"] = round(tokens_per_second, 2)

        return llm_metadata


class ResultFormatter:
    """結果フォーマッター"""

    def __init__(self):
        """初期化"""
        self.metadata_collector = MetadataCollector()

    def _get_meaning_from_score(self, score: float) -> str:
        """スコアから意味を取得"""
        if score >= 0.99:
            return "完全一致"
        elif score >= 0.8:
            return "非常に類似"
        elif score >= 0.6:
            return "類似"
        elif score >= 0.4:
            return "やや類似"
        else:
            return "低い類似度"

    def format_score_output(self, enhanced_result: EnhancedResult) -> Dict[str, Any]:
        """
        scoreタイプの出力フォーマット

        Args:
            enhanced_result: 拡張結果

        Returns:
            フォーマット済み結果
        """
        # 基本フォーマット（既存互換性）
        file_info = enhanced_result.input_data.get("file1", "unknown")
        if "file2" in enhanced_result.input_data:
            file_info += f" vs {enhanced_result.input_data['file2']}"
        elif "file" in enhanced_result.input_data:
            file_info = enhanced_result.input_data["file"]

        formatted = {
            "file": file_info,
            "score": round(enhanced_result.score, 4),
            "meaning": self._get_meaning_from_score(enhanced_result.score),
            "method_used": enhanced_result.method,  # Requirement 5.5
            "processing_time": enhanced_result.processing_time,  # Task 4.2
            "json": {
                "field_match_ratio": enhanced_result.metadata.get("field_match_ratio", 0.0),
                "value_similarity": enhanced_result.metadata.get("value_similarity", 0.0),
                "final_score": round(enhanced_result.score, 4)
            }
        }

        # 拡張メタデータ
        metadata = {
            "calculation_method": enhanced_result.method,
            "comparison_method": enhanced_result.method,  # Requirement 8.1: 判定方式の明示的識別
            "processing_time": enhanced_result.processing_time,
            **self.metadata_collector.collect_system_metadata()
        }

        # LLM固有メタデータ
        if enhanced_result.method in ["llm", "llm_fallback"]:
            llm_details = self.metadata_collector.collect_llm_metadata(
                StrategyResult(
                    score=enhanced_result.score,
                    method=enhanced_result.method,
                    processing_time=enhanced_result.processing_time,
                    metadata=enhanced_result.metadata
                )
            )
            if llm_details:
                metadata["llm_details"] = llm_details

        formatted["metadata"] = metadata

        return formatted

    def format_file_output(self, enhanced_result: EnhancedResult) -> Dict[str, Any]:
        """
        fileタイプの出力フォーマット

        Args:
            enhanced_result: 拡張結果

        Returns:
            フォーマット済み結果
        """
        # 元のデータから開始
        original_row = enhanced_result.input_data.get("original_row", {})
        formatted = original_row.copy()

        # 既存の類似度情報（互換性）
        formatted["similarity_score"] = round(enhanced_result.score, 4)
        formatted["similarity_details"] = {
            "field_match_ratio": enhanced_result.metadata.get("field_match_ratio", 0.0),
            "value_similarity": enhanced_result.metadata.get("value_similarity", 0.0)
        }

        # 拡張メタデータ
        calculation_metadata = {
            "method": enhanced_result.method,
            "processing_time": enhanced_result.processing_time,
            "timestamp": enhanced_result.timestamp
        }

        # LLM固有メタデータ
        if enhanced_result.method in ["llm", "llm_fallback"]:
            llm_details = self.metadata_collector.collect_llm_metadata(
                StrategyResult(
                    score=enhanced_result.score,
                    method=enhanced_result.method,
                    processing_time=enhanced_result.processing_time,
                    metadata=enhanced_result.metadata
                )
            )
            if llm_details:
                calculation_metadata["llm_details"] = llm_details

        formatted["calculation_metadata"] = calculation_metadata

        return formatted

    def format_batch_results(
        self,
        enhanced_results: List[EnhancedResult],
        output_type: str = "score"
    ) -> Dict[str, Any]:
        """
        バッチ結果のフォーマット

        Args:
            enhanced_results: 拡張結果のリスト
            output_type: 出力タイプ

        Returns:
            フォーマット済みバッチ結果
        """
        if not enhanced_results:
            return {
                "summary": {
                    "total_comparisons": 0,
                    "average_score": 0.0,
                    "total_processing_time": 0.0
                },
                "detailed_results": []
            }

        # 統計計算
        total_comparisons = len(enhanced_results)
        total_score = sum(r.score for r in enhanced_results)
        average_score = total_score / total_comparisons
        total_processing_time = sum(r.processing_time for r in enhanced_results)

        # 方法別統計
        method_breakdown = {}
        for result in enhanced_results:
            method = result.method
            method_breakdown[method] = method_breakdown.get(method, 0) + 1

        # 詳細結果
        if output_type == "score":
            detailed_results = [
                self.format_score_output(result) for result in enhanced_results
            ]
        else:  # file
            detailed_results = [
                self.format_file_output(result) for result in enhanced_results
            ]

        # 基本レスポンス構造
        result = {
            "summary": {
                "total_comparisons": total_comparisons,
                "average_score": round(average_score, 4),
                "total_processing_time": round(total_processing_time, 2),
                "method_breakdown": method_breakdown
            },
            "metadata": self.metadata_collector.collect_system_metadata()
        }

        # ファイル形式の場合のみ詳細結果を含める
        if output_type == "file":
            result["detailed_results"] = detailed_results

        return result


class CompatibilityLayer:
    """互換性レイヤー"""

    def __init__(self):
        """初期化"""
        self.metadata_collector = MetadataCollector()

    def convert_to_legacy_format(self, enhanced_result: EnhancedResult) -> Dict[str, Any]:
        """
        拡張結果をレガシーフォーマットに変換

        Args:
            enhanced_result: 拡張結果

        Returns:
            レガシーフォーマットの辞書
        """
        file_info = enhanced_result.input_data.get("file1", "unknown")
        if "file2" in enhanced_result.input_data:
            file_info += f" vs {enhanced_result.input_data['file2']}"
        elif "file" in enhanced_result.input_data:
            file_info = enhanced_result.input_data["file"]

        meaning = self._get_meaning_from_score(enhanced_result.score)

        return {
            "file": file_info,
            "score": round(enhanced_result.score, 4),
            "meaning": meaning,
            "json": {
                "field_match_ratio": enhanced_result.metadata.get("field_match_ratio", 0.0),
                "value_similarity": enhanced_result.metadata.get("value_similarity", 0.0),
                "final_score": round(enhanced_result.score, 4)
            }
        }

    def detect_format_version(self, data: Dict[str, Any]) -> str:
        """
        フォーマットバージョンを検出

        Args:
            data: 結果データ

        Returns:
            フォーマットバージョン（"legacy" または "enhanced"）
        """
        if "metadata" in data and "calculation_method" in data.get("metadata", {}):
            return "enhanced"
        else:
            return "legacy"

    def upgrade_legacy_format(self, legacy_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        レガシーフォーマットを拡張フォーマットにアップグレード

        Args:
            legacy_data: レガシーデータ

        Returns:
            拡張フォーマットのデータ
        """
        enhanced_data = legacy_data.copy()

        # 拡張メタデータを追加
        enhanced_data["metadata"] = {
            "calculation_method": "unknown",  # レガシーデータでは不明
            "format_version": "enhanced",
            **self.metadata_collector.collect_system_metadata()
        }

        return enhanced_data

    def ensure_backward_compatibility(self, enhanced_result: EnhancedResult) -> Dict[str, Any]:
        """
        後方互換性を確保した結果を生成

        Args:
            enhanced_result: 拡張結果

        Returns:
            後方互換性のある結果
        """
        file_info = enhanced_result.input_data.get("file1", "unknown")
        if "file2" in enhanced_result.input_data:
            file_info += f" vs {enhanced_result.input_data['file2']}"
        elif "file" in enhanced_result.input_data:
            file_info = enhanced_result.input_data["file"]

        # 必須フィールドを確保
        result = {
            "file": file_info,
            "score": round(enhanced_result.score, 4),
            "meaning": self._get_meaning_from_score(enhanced_result.score),
            "json": {
                "field_match_ratio": enhanced_result.metadata.get("field_match_ratio", 0.0),
                "value_similarity": enhanced_result.metadata.get("value_similarity", 0.0),
                "final_score": round(enhanced_result.score, 4)
            }
        }

        # 拡張メタデータ（オプション）
        result["metadata"] = {
            "calculation_method": enhanced_result.method,
            "processing_time": enhanced_result.processing_time,
            **self.metadata_collector.collect_system_metadata()
        }

        return result

    def _get_meaning_from_score(self, score: float) -> str:
        """スコアから意味を取得"""
        if score >= 0.99:
            return "完全一致"
        elif score >= 0.8:
            return "非常に類似"
        elif score >= 0.6:
            return "類似"
        elif score >= 0.4:
            return "やや類似"
        else:
            return "低い類似度"


# ファクトリー関数
def create_enhanced_result_from_strategy(
    strategy_result: StrategyResult,
    input_data: Dict[str, Any]
) -> EnhancedResult:
    """
    StrategyResultから拡張結果を作成するファクトリー関数

    Args:
        strategy_result: 戦略結果
        input_data: 入力データ情報

    Returns:
        拡張結果
    """
    return EnhancedResult.from_strategy_result(strategy_result, input_data)


def format_enhanced_result(
    enhanced_result: EnhancedResult,
    output_type: str = "score",
    legacy_compatible: bool = False
) -> Dict[str, Any]:
    """
    拡張結果をフォーマットするファクトリー関数

    Args:
        enhanced_result: 拡張結果
        output_type: 出力タイプ（"score" または "file"）
        legacy_compatible: レガシー互換性モード

    Returns:
        フォーマット済み結果
    """
    formatter = ResultFormatter()
    compatibility = CompatibilityLayer()

    if legacy_compatible:
        return compatibility.convert_to_legacy_format(enhanced_result)
    elif output_type == "score":
        return formatter.format_score_output(enhanced_result)
    else:
        return formatter.format_file_output(enhanced_result)


def create_enhanced_result_from_strategy(
    strategy_result: StrategyResult,
    input_data: Dict[str, Any],
    llm_config: Optional[Dict[str, Any]] = None,
    performance_data: Optional[Dict[str, Any]] = None
) -> EnhancedResult:
    """
    StrategyResultから拡張結果を作成 - Task 4.2

    Args:
        strategy_result: 戦略パターンの結果
        input_data: 入力データ情報
        llm_config: LLM設定（LLMメタデータ作成用）
        performance_data: パフォーマンスデータ

    Returns:
        拡張結果インスタンス
    """
    # 基本的な拡張結果を作成
    enhanced_result = EnhancedResult(
        score=strategy_result.score,
        method=strategy_result.method,
        processing_time=strategy_result.processing_time,
        input_data=input_data,
        metadata=strategy_result.metadata.copy()
    )

    # LLMメタデータの作成（LLMモードの場合）
    if strategy_result.method in ["llm", "llm_fallback"] and llm_config:
        llm_metadata = LLMMetadata(
            model_name=llm_config.get("model", "unknown"),
            prompt_file=llm_config.get("prompt_file"),
            temperature=llm_config.get("temperature", 0.2),
            max_tokens=llm_config.get("max_tokens", 64),
            tokens_used=strategy_result.metadata.get("tokens_used"),
            prompt_tokens=strategy_result.metadata.get("prompt_tokens"),
            completion_tokens=strategy_result.metadata.get("completion_tokens")
        )
        enhanced_result.llm_metadata = llm_metadata

    # パフォーマンス指標の作成
    if performance_data:
        perf_metrics = PerformanceMetrics(
            api_call_time=performance_data.get("api_call_time", strategy_result.processing_time),
            total_processing_time=performance_data.get("total_processing_time", strategy_result.processing_time),
            queue_wait_time=performance_data.get("queue_wait_time"),
            token_generation_rate=performance_data.get("token_generation_rate"),
            retry_count=performance_data.get("retry_count", 0),
            retry_total_time=performance_data.get("retry_total_time", 0.0),
            fallback_used=strategy_result.method.endswith("_fallback"),
            memory_usage_mb=performance_data.get("memory_usage_mb")
        )
        enhanced_result.performance_metrics = perf_metrics

    # フォールバック情報の設定
    if strategy_result.method.endswith("_fallback"):
        enhanced_result.fallback_reason = strategy_result.metadata.get("fallback_reason", "Unknown")
        # Task 4.2: メタデータのoriginal_methodを優先、なければmethod名から推測
        enhanced_result.original_method = strategy_result.metadata.get("original_method",
                                                                      strategy_result.method.replace("_fallback", ""))

    return enhanced_result