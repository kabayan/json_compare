"""スコア変換と結果処理システム

LLMレスポンスから数値スコアとカテゴリ情報を抽出し、
構造化された結果に変換するモジュール。
"""

import re
import logging
from typing import Dict, List, Optional, Any, Pattern
from dataclasses import dataclass
import unicodedata

logger = logging.getLogger(__name__)


class ScoreParsingError(Exception):
    """スコア解析関連のエラー"""
    pass


@dataclass
class ParsedScore:
    """解析されたスコア結果"""
    score: float
    category: str = ""
    reason: str = ""
    confidence: float = 0.0
    raw_response: str = ""
    line_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "score": self.score,
            "category": self.category,
            "reason": self.reason,
            "confidence": self.confidence
        }
        if self.line_number is not None:
            result["line_number"] = self.line_number
        return result


class CategoryScoreMapping:
    """カテゴリとスコアのマッピング管理"""

    def __init__(self):
        """初期化 - Requirement 4.3準拠"""
        self.category_scores = {
            "完全一致": 1.0,
            "非常に類似": 0.8,
            "類似": 0.6,
            "やや類似": 0.4,
            "低い類似度": 0.2
        }
        self.default_score = 0.5

    def get_score(self, category: str) -> float:
        """カテゴリからスコアを取得"""
        return self.category_scores.get(category, self.default_score)

    def get_category_from_score(self, score: float) -> str:
        """スコアから最も近いカテゴリを取得"""
        if score >= 0.95:
            return "完全一致"
        elif score >= 0.8:
            return "非常に類似"
        elif score >= 0.6:
            return "類似"
        elif score >= 0.4:
            return "やや類似"
        else:
            return "低い類似度"


class ScoreParser:
    """スコア解析エンジン"""

    def __init__(self, patterns: Optional[Dict[str, str]] = None):
        """
        ScoreParserを初期化

        Args:
            patterns: カスタムパターン辞書
        """
        self.category_mapping = CategoryScoreMapping()

        # デフォルトパターン
        default_patterns = {
            "score_pattern": r"\*\*スコア\*\*[：:]\s*([-]?[0-9.０-９．]+)",
            "category_pattern": r"\*\*カテゴリ\*\*[：:]\s*([^\n]+)",
            "reason_pattern": r"\*\*理由\*\*[：:]\s*(.+?)(?=\n\S|$)",
            "percentage_pattern": r"([-]?[0-9.０-９．]+)%",
            "number_pattern": r"([-]?[0-9.０-９．]+)"
        }

        # カスタムパターンでオーバーライド
        if patterns:
            default_patterns.update(patterns)

        self.patterns = {
            key: re.compile(pattern, re.MULTILINE | re.DOTALL)
            for key, pattern in default_patterns.items()
        }

        # 統計情報
        self.stats = {
            "total_parsed": 0,
            "successful_parsed": 0,
            "failed_parsed": 0
        }

    def _normalize_japanese_numbers(self, text: str) -> str:
        """全角数字を半角数字に変換"""
        return unicodedata.normalize('NFKC', text)

    def _extract_score(self, text: str) -> Optional[float]:
        """テキストからスコアを抽出"""
        normalized_text = self._normalize_japanese_numbers(text)

        # スコアパターンでの抽出を試行
        score_match = self.patterns["score_pattern"].search(normalized_text)
        if score_match:
            try:
                original_score = float(score_match.group(1))
                # Requirement 8.5: 範囲外の値に警告を出してクランプ
                if original_score < 0.0 or original_score > 1.0:
                    logger.warning(
                        f"スコア値が期待範囲外です: {original_score} -> "
                        f"{max(0.0, min(1.0, original_score))}にクランプしました"
                    )
                return max(0.0, min(1.0, original_score))
            except ValueError:
                pass

        # パーセンテージパターンでの抽出を試行
        percentage_match = self.patterns["percentage_pattern"].search(normalized_text)
        if percentage_match:
            try:
                percentage = float(percentage_match.group(1))
                score = percentage / 100.0
                # Requirement 8.5: 範囲外の値に警告を出してクランプ
                if score < 0.0 or score > 1.0:
                    logger.warning(
                        f"パーセンテージから変換されたスコアが範囲外です: {score} -> "
                        f"{max(0.0, min(1.0, score))}にクランプしました"
                    )
                return max(0.0, min(1.0, score))
            except ValueError:
                pass

        # 一般的な数値パターンでの抽出（最後に出現したもの）
        number_matches = list(self.patterns["number_pattern"].finditer(normalized_text))
        if number_matches:
            try:
                last_number = float(number_matches[-1].group(1))
                # 1より大きい値は百分率として扱うか、1.0でクランプ
                if last_number > 1:
                    if last_number <= 100:
                        score = last_number / 100.0
                        return max(0.0, min(1.0, score))
                    else:
                        # Requirement 8.5: 100超過の場合の警告
                        logger.warning(
                            f"数値が範囲外です: {last_number} -> 1.0にクランプしました"
                        )
                        return 1.0
                # 0-1の範囲ならそのまま使用
                else:
                    original_score = last_number
                    if original_score < 0.0:
                        logger.warning(
                            f"数値が範囲外です: {original_score} -> 0.0にクランプしました"
                        )
                    return max(0.0, original_score)
            except ValueError:
                pass

        return None

    def _extract_category(self, text: str) -> str:
        """テキストからカテゴリを抽出"""
        category_match = self.patterns["category_pattern"].search(text)
        if category_match:
            return category_match.group(1).strip()

        # パターンマッチしない場合、キーワードベースで推定（長いものを優先）
        found_categories = []
        for category in self.category_mapping.category_scores.keys():
            if category in text:
                found_categories.append(category)

        # 最も長いカテゴリ名を選択
        if found_categories:
            return max(found_categories, key=len)

        return ""

    def _extract_reason(self, text: str) -> str:
        """テキストから理由を抽出"""
        reason_match = self.patterns["reason_pattern"].search(text)
        if reason_match:
            return reason_match.group(1).strip()

        # パターンマッチしない場合、全文を理由として返す（構造化チェック時は除く）
        if "理由:" in text:
            # 理由:の後の部分を取得
            reason_part = text.split("理由:")[-1].strip()
            return reason_part

        return text.strip()

    def _calculate_confidence(self, response_text: str, has_score: bool, has_category: bool, has_reason: bool) -> float:
        """信頼度を計算"""
        confidence = 0.0

        # 構造化レベルに基づく基本信頼度
        if has_score and has_category and has_reason:
            confidence = 0.85  # 完全に構造化
        elif has_score and (has_category or has_reason):
            confidence = 0.6  # 部分的に構造化
        elif has_score:
            confidence = 0.4  # スコアのみ
        else:
            confidence = 0.2  # カテゴリのみ

        # 応答の長さによる調整
        if len(response_text) > 50:
            confidence += 0.1

        # キーワードの存在による調整
        if "類似" in response_text:
            confidence += 0.05

        # 構造化パターンの存在による追加調整
        if "スコア:" in response_text and "カテゴリ:" in response_text:
            confidence += 0.15

        return min(1.0, confidence)

    def infer_category_from_score(self, score: float) -> str:
        """スコアからカテゴリを推定"""
        return self.category_mapping.get_category_from_score(score)

    def parse_with_line_info(self, response_text: str, line_number: int, log_details: bool = True) -> ParsedScore:
        """行番号付きでLLMレスポンスを解析 - Requirement 4.5対応"""
        try:
            result = self.parse_response(response_text, log_details=log_details)
            result.line_number = line_number

            if log_details:
                logger.info(
                    f"line_processing_result: line={line_number}, score={result.score}, "
                    f"category={result.category}, confidence={result.confidence}"
                )

            return result
        except ScoreParsingError as e:
            logger.error(
                f"line_parsing_failed: line={line_number}, error={str(e)}, "
                f"response_length={len(response_text)}"
            )
            raise

    def parse_response(self, response_text: str, log_details: bool = False) -> ParsedScore:
        """
        LLMレスポンスを解析してParsedScoreに変換

        Args:
            response_text: LLMからのレスポンステキスト
            log_details: 詳細ログを出力するかどうか

        Returns:
            解析結果

        Raises:
            ScoreParsingError: 解析に失敗した場合
        """
        self.stats["total_parsed"] += 1

        if log_details:
            logger.info(f"レスポンス解析開始: {response_text[:100]}...")

        try:
            # スコア抽出
            score = self._extract_score(response_text)
            category_from_fallback = ""

            if score is None:
                # カテゴリからスコアを推定
                category = self._extract_category(response_text)
                if category:
                    score = self.category_mapping.get_score(category)
                else:
                    # 最後の手段：曖昧な類似性キーワードから推定
                    if any(keyword in response_text for keyword in ["似", "同じ", "近い", "類似"]):
                        score = 0.5  # デフォルトの中程度の類似度
                        category_from_fallback = "やや類似"
                    else:
                        self.stats["failed_parsed"] += 1
                        raise ScoreParsingError("数値スコアを抽出できません")

            # カテゴリ抽出（スコアから推定も含む）
            if not category_from_fallback:
                category = self._extract_category(response_text)
                if not category:
                    category = self.infer_category_from_score(score)
            else:
                category = category_from_fallback

            # 理由抽出
            reason = self._extract_reason(response_text)

            # 信頼度計算
            has_score = score is not None
            has_category = bool(self._extract_category(response_text))
            has_reason = bool(self.patterns["reason_pattern"].search(response_text))
            confidence = self._calculate_confidence(response_text, has_score, has_category, has_reason)

            result = ParsedScore(
                score=score,
                category=category,
                reason=reason,
                confidence=confidence,
                raw_response=response_text
            )

            self.stats["successful_parsed"] += 1

            if log_details:
                logger.debug(f"解析成功: スコア={score}, カテゴリ={category}, 信頼度={confidence}")

            return result

        except Exception as e:
            # ScoreParsingErrorの場合は既にfailed_parsedが更新されているのでスキップ
            if not isinstance(e, ScoreParsingError):
                self.stats["failed_parsed"] += 1
            if log_details:
                logger.error(f"解析失敗: {e}")
            raise

    def parse_batch_responses(self, responses: List[str], skip_errors: bool = False) -> List[ParsedScore]:
        """
        複数のレスポンスを一括解析

        Args:
            responses: レスポンステキストのリスト
            skip_errors: エラーをスキップするかどうか

        Returns:
            解析結果のリスト
        """
        results = []

        for i, response in enumerate(responses):
            try:
                result = self.parse_response(response)
                results.append(result)
            except ScoreParsingError as e:
                if skip_errors:
                    logger.warning(f"レスポンス {i+1} の解析をスキップ: {e}")
                    # skip_errorsの場合、統計は既にparse_responseで更新されているのでそのまま続行
                    continue
                else:
                    raise

        return results

    def get_parsing_statistics(self) -> Dict[str, Any]:
        """解析統計情報を取得"""
        total = self.stats["total_parsed"]
        return {
            "total_parsed": total,
            "successful_parsed": self.stats["successful_parsed"],
            "failed_parsed": self.stats["failed_parsed"],
            "success_rate": self.stats["successful_parsed"] / max(total, 1)
        }

    def reset_statistics(self):
        """統計情報をリセット"""
        self.stats = {
            "total_parsed": 0,
            "successful_parsed": 0,
            "failed_parsed": 0
        }