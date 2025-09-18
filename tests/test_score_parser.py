"""スコア変換と結果処理システムのテスト"""

import pytest
from unittest.mock import MagicMock, patch
import logging

# これから実装するモジュールをインポート
from src.score_parser import (
    ScoreParser,
    ScoreParsingError,
    ParsedScore,
    CategoryScoreMapping
)


class TestScoreParser:
    """スコア解析処理のテストクラス"""

    @pytest.fixture
    def score_parser(self):
        """ScoreParserインスタンスを返すフィクスチャ"""
        return ScoreParser()

    def test_parse_structured_response(self, score_parser):
        """構造化されたレスポンスの解析テスト"""
        response_text = """
        スコア: 0.85
        カテゴリ: 非常に類似
        理由: 両テキストは同じ概念について述べており、表現は異なるが意味は非常に近い。
        """

        result = score_parser.parse_response(response_text)

        assert isinstance(result, ParsedScore)
        assert result.score == 0.85
        assert result.category == "非常に類似"
        assert result.reason == "両テキストは同じ概念について述べており、表現は異なるが意味は非常に近い。"
        assert result.confidence > 0.8  # 構造化されたレスポンスは高い信頼度

    def test_parse_unstructured_response_with_number(self, score_parser):
        """数値を含む非構造化レスポンスの解析テスト"""
        response_text = "テキストを比較すると、類似度は0.75程度で、やや類似していると言えます。"

        result = score_parser.parse_response(response_text)

        assert result.score == 0.75
        assert result.category == "やや類似"  # 自動推定
        assert result.confidence < 0.7  # 非構造化は信頼度が低い

    def test_parse_categorical_response(self, score_parser):
        """カテゴリのみのレスポンスの解析テスト"""
        response_text = "これらのテキストは非常に類似しています。"

        result = score_parser.parse_response(response_text)

        assert result.category == "非常に類似"
        assert result.score == 0.8  # カテゴリマッピングから自動算出 (Requirement 4.3準拠)
        assert result.reason == "これらのテキストは非常に類似しています。"

    def test_parse_percentage_score(self, score_parser):
        """パーセンテージ形式のスコア解析テスト"""
        response_text = "類似度: 85%"

        result = score_parser.parse_response(response_text)

        assert result.score == 0.85

    def test_parse_out_of_range_score(self, score_parser):
        """範囲外のスコアの正規化テスト"""
        response_text = "スコア: 1.5"  # 1.0を超える

        result = score_parser.parse_response(response_text)

        assert result.score == 1.0  # 上限にクランプ

        response_text2 = "スコア: -0.2"  # 0.0未満
        result2 = score_parser.parse_response(response_text2)

        assert result2.score == 0.0  # 下限にクランプ

    def test_parse_multiple_scores(self, score_parser):
        """複数のスコアが含まれる場合のテスト"""
        response_text = """
        第一印象の類似度: 0.6
        詳細分析の結果: 0.8
        最終スコア: 0.75
        """

        result = score_parser.parse_response(response_text)

        # 最後に出現したスコアを使用
        assert result.score == 0.75

    def test_parse_failed_response(self, score_parser):
        """解析不能なレスポンスのエラーテスト"""
        response_text = "申し訳ありませんが、比較できませんでした。"

        with pytest.raises(ScoreParsingError, match="数値スコアを抽出できません"):
            score_parser.parse_response(response_text)

    def test_category_score_mapping(self):
        """カテゴリスコアマッピングのテスト - Requirement 4.3準拠"""
        mapping = CategoryScoreMapping()

        # Requirement 4.3で指定された正確な値
        assert mapping.get_score("完全一致") == 1.0
        assert mapping.get_score("非常に類似") == 0.8
        assert mapping.get_score("類似") == 0.6
        assert mapping.get_score("やや類似") == 0.4
        assert mapping.get_score("低い類似度") == 0.2

        # 未知のカテゴリ
        assert mapping.get_score("不明なカテゴリ") == 0.5  # デフォルト値

    def test_category_inference_from_score(self, score_parser):
        """スコアからのカテゴリ推定テスト - Requirement 4.3準拠"""
        assert score_parser.infer_category_from_score(0.95) == "完全一致"
        assert score_parser.infer_category_from_score(0.8) == "非常に類似"  # 正確な境界値
        assert score_parser.infer_category_from_score(0.6) == "類似"      # 正確な境界値
        assert score_parser.infer_category_from_score(0.4) == "やや類似"    # 正確な境界値
        assert score_parser.infer_category_from_score(0.2) == "低い類似度" # 正確な境界値

    def test_confidence_calculation(self, score_parser):
        """信頼度計算のテスト"""
        # 構造化されたレスポンス（高い信頼度）
        structured_response = "スコア: 0.8\nカテゴリ: 非常に類似\n理由: 詳細な説明"
        result1 = score_parser.parse_response(structured_response)
        assert result1.confidence > 0.8

        # 部分的に構造化されたレスポンス（中程度の信頼度）
        partial_response = "類似度は0.8です"
        result2 = score_parser.parse_response(partial_response)
        assert 0.4 < result2.confidence < 0.8

        # 非構造化レスポンス（低い信頼度）
        unstructured_response = "似ているようです"
        result3 = score_parser.parse_response(unstructured_response)
        assert result3.confidence < 0.5

    def test_custom_patterns(self):
        """カスタムパターンでのScoreParserテスト"""
        custom_patterns = {
            "score_pattern": r"評価[：:]\s*([0-9.]+)",
            "category_pattern": r"分類[：:]\s*([^\n]+)",
            "reason_pattern": r"根拠[：:]\s*([^\n]+)"
        }

        parser = ScoreParser(patterns=custom_patterns)

        response_text = """
        評価: 0.75
        分類: 類似
        根拠: カスタムパターンでの解析
        """

        result = parser.parse_response(response_text)

        assert result.score == 0.75
        assert result.category == "類似"
        assert result.reason == "カスタムパターンでの解析"

    def test_japanese_text_handling(self, score_parser):
        """日本語テキストの処理テスト"""
        response_text = """
        評価スコア：０．８５
        判定結果：非常に類似している
        評価理由：両方のテキストが同じ内容を扱っており、
        　　　　　表現方法のみが異なっている。
        """

        result = score_parser.parse_response(response_text)

        assert result.score == 0.85
        assert "非常に類似" in result.category
        assert "同じ内容" in result.reason

    def test_malformed_score_handling(self, score_parser):
        """不正な形式のスコア処理テスト"""
        # 非数値のスコア
        response_text1 = "スコア: 高い"
        with pytest.raises(ScoreParsingError):
            score_parser.parse_response(response_text1)

        # 空のスコア
        response_text2 = "スコア: "
        with pytest.raises(ScoreParsingError):
            score_parser.parse_response(response_text2)

    def test_response_logging(self, score_parser):
        """レスポンス処理のログ記録テスト"""
        with patch('src.score_parser.logger') as mock_logger:
            response_text = "スコア: 0.8\nカテゴリ: 非常に類似"

            result = score_parser.parse_response(response_text, log_details=True)

            # ログが適切に記録されることを確認
            assert mock_logger.info.called
            assert mock_logger.debug.called

    def test_batch_parsing(self, score_parser):
        """バッチ解析のテスト"""
        responses = [
            "スコア: 0.8\nカテゴリ: 非常に類似",
            "スコア: 0.6\nカテゴリ: 類似",
            "類似度は0.4程度です"
        ]

        results = score_parser.parse_batch_responses(responses)

        assert len(results) == 3
        assert results[0].score == 0.8
        assert results[1].score == 0.6
        assert results[2].score == 0.4

    def test_statistics_collection(self, score_parser):
        """統計情報収集のテスト"""
        # 統計をリセットしてクリーンな状態から開始
        score_parser.reset_statistics()

        responses = [
            "スコア: 0.8\nカテゴリ: 非常に類似",
            "スコア: 0.6\nカテゴリ: 類似",
            "解析不能なレスポンス"
        ]

        # バッチ解析を実行（エラーを許容）
        results = score_parser.parse_batch_responses(responses, skip_errors=True)

        stats = score_parser.get_parsing_statistics()

        assert stats["total_parsed"] == 3
        assert stats["successful_parsed"] == 2
        assert stats["failed_parsed"] == 1
        assert stats["success_rate"] == 2/3