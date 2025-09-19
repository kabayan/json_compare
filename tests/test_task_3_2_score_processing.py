"""Task 3.2: スコア変換と結果処理システムの統合テスト

Task 3.2専用のテストスイート。
Requirements 4.1, 4.2, 4.3, 4.4, 8.5の統合的検証。
"""

import pytest
import logging
from unittest.mock import patch, MagicMock
from io import StringIO

from src.score_parser import (
    ScoreParser,
    ScoreParsingError,
    ParsedScore,
    CategoryScoreMapping
)


class TestTask32ScoreProcessing:
    """Task 3.2: スコア変換と結果処理システムの統合テストクラス"""

    @pytest.fixture
    def task_3_2_score_parser(self):
        """Task 3.2専用のScoreParserインスタンス"""
        return ScoreParser()

    def test_requirement_4_1_numerical_score_extraction(self, task_3_2_score_parser):
        """
        Requirement 4.1: LLMの回答から0-1の数値スコアを抽出する

        Task 3.2: LLM応答から数値スコアを抽出する機能を実装
        """
        # 様々な形式の数値スコア抽出をテスト
        test_cases = [
            ("スコア: 0.85", 0.85),
            ("類似度スコア：0.92", 0.92),
            ("評価: 0.73", 0.73),
            ("score: 0.46", 0.46),
            ("0.67という値です", 0.67),
            ("75%の類似度", 0.75),
            ("95％の一致", 0.95)
        ]

        for response_text, expected_score in test_cases:
            result = task_3_2_score_parser.parse_response(response_text)
            assert result.score == expected_score, f"Failed for: {response_text}"
            assert 0.0 <= result.score <= 1.0, "Score must be in valid range"

    def test_requirement_4_2_automatic_score_estimation(self, task_3_2_score_parser):
        """
        Requirement 4.2: 数値スコアがない場合は回答内容に基づいて自動的にスコアを推定

        Task 3.2: カテゴリベースのスコア推定ロジックを構築
        """
        # 数値スコアがないが、類似性キーワードがある場合のテスト
        test_cases = [
            ("これらのテキストは似ています", 0.5, "やや類似"),
            ("同じような内容です", 0.5, "やや類似"),
            ("近い意味を持っています", 0.5, "やや類似"),
            ("類似した表現が見られます", 0.6, "類似")  # "類似"キーワードが検出される
        ]

        for response_text, expected_score, expected_category in test_cases:
            result = task_3_2_score_parser.parse_response(response_text)
            assert result.score == expected_score, f"Failed for: {response_text}"
            assert result.category == expected_category, f"Category mismatch for: {response_text}"

    def test_requirement_4_3_category_based_score_conversion(self, task_3_2_score_parser):
        """
        Requirement 4.3: カテゴリベースの数値スコア変換
        (完全一致=1.0, 非常に類似=0.8, 類似=0.6, やや類似=0.4, 低い類似度=0.2)

        Task 3.2: カテゴリベースのスコア推定ロジックを構築
        """
        # Requirement 4.3で指定された正確なマッピング
        test_cases = [
            ("カテゴリ: 完全一致", 1.0, "完全一致"),
            ("カテゴリ: 非常に類似", 0.8, "非常に類似"),
            ("カテゴリ: 類似", 0.6, "類似"),
            ("カテゴリ: やや類似", 0.4, "やや類似"),
            ("カテゴリ: 低い類似度", 0.2, "低い類似度"),
            ("これらのテキストは完全一致しています", 1.0, "完全一致"),
            ("非常に類似した内容です", 0.8, "非常に類似"),
            ("類似している部分があります", 0.6, "類似"),
            ("やや類似している感じです", 0.4, "やや類似"),
            ("低い類似度を示しています", 0.2, "低い類似度")
        ]

        for response_text, expected_score, expected_category in test_cases:
            result = task_3_2_score_parser.parse_response(response_text)
            assert result.score == expected_score, f"Score mismatch for: {response_text}"
            assert result.category == expected_category, f"Category mismatch for: {response_text}"

    def test_requirement_4_4_unparseable_response_handling(self, task_3_2_score_parser):
        """
        Requirement 4.4: 解析不能な応答をエラーとして処理し、該当行をスキップ

        Task 3.2: 解析不能な応答への対処メカニズムを実装
        """
        # 解析不能なレスポンスのテストケース
        unparseable_responses = [
            "申し訳ありませんが、比較できませんでした。",
            "エラーが発生しました。",
            "不明な結果です。",
            "",  # 空文字列
            "   ",  # 空白のみ
            "無関係なテキストです。"
        ]

        for response_text in unparseable_responses:
            with pytest.raises(ScoreParsingError, match="数値スコアを抽出できません"):
                task_3_2_score_parser.parse_response(response_text)

        # バッチ処理でのスキップ動作をテスト
        mixed_responses = [
            "スコア: 0.8",  # 正常
            "解析不能なレスポンス",  # エラー
            "カテゴリ: 類似",  # 正常
            "また別のエラー"  # エラー
        ]

        results = task_3_2_score_parser.parse_batch_responses(mixed_responses, skip_errors=True)

        # 正常な2つのレスポンスのみが処理される
        assert len(results) == 2
        assert results[0].score == 0.8
        assert results[1].score == 0.6  # "類似"のマッピング

    def test_requirement_8_5_score_range_validation_and_clamping(self, task_3_2_score_parser):
        """
        Requirement 8.5: スコア範囲検証と自動クランプ機能（警告メッセージ付き）

        Task 3.2: スコア範囲の検証と自動クランプ機能を追加
        """
        # 範囲外スコアのテストケース
        test_cases = [
            ("スコア: 1.5", 1.0, True),   # 上限超過
            ("スコア: -0.3", 0.0, True),  # 下限未満
            ("スコア: 2.0", 1.0, True),   # 大幅上限超過
            ("スコア: -1.0", 0.0, True),  # 大幅下限未満
            ("スコア: 0.5", 0.5, False),  # 正常範囲
            ("スコア: 0.0", 0.0, False),  # 境界値（下限）
            ("スコア: 1.0", 1.0, False)   # 境界値（上限）
        ]

        for response_text, expected_score, should_warn in test_cases:
            with patch('src.score_parser.logger') as mock_logger:
                result = task_3_2_score_parser.parse_response(response_text)

                # スコアが適切にクランプされることを確認
                assert result.score == expected_score, f"Score clamping failed for: {response_text}"
                assert 0.0 <= result.score <= 1.0, "Score must be within valid range"

                # 警告メッセージの出力確認
                if should_warn:
                    # 警告ログが出力されることを確認
                    mock_logger.warning.assert_called()
                    warning_message = mock_logger.warning.call_args[0][0]
                    assert "範囲外" in warning_message or "クランプ" in warning_message, \
                        "Warning message should mention out-of-range or clamping"

    def test_task_3_2_batch_processing_with_logging(self, task_3_2_score_parser):
        """
        Task 3.2: バッチ処理でのLLM判定結果とスコア変換のログ記録

        Requirement 4.5 (implied): バッチ処理中のLLM判定結果とスコアログ記録
        """
        responses = [
            "スコア: 0.85\nカテゴリ: 非常に類似\n理由: 詳細な説明",
            "カテゴリ: 類似",
            "スコア: 1.5",  # 範囲外
            "解析不能なレスポンス"
        ]

        with patch('src.score_parser.logger') as mock_logger:
            # 行番号付きでバッチ処理
            results = []
            for i, response in enumerate(responses):
                try:
                    result = task_3_2_score_parser.parse_with_line_info(
                        response, line_number=i+1, log_details=True
                    )
                    results.append(result)
                except ScoreParsingError:
                    pass  # エラーはスキップ

            # 正常処理された結果の確認
            assert len(results) == 3  # 解析不能な1つ以外は処理される

            # ログ記録の確認
            assert mock_logger.info.called, "処理結果のログが記録される"
            assert mock_logger.warning.called, "範囲外スコアの警告が記録される"
            assert mock_logger.error.called, "解析エラーが記録される"

    def test_task_3_2_confidence_and_quality_metrics(self, task_3_2_score_parser):
        """
        Task 3.2: 信頼度と品質メトリクスの統合テスト

        スコア解析結果の品質評価機能
        """
        # 品質レベルの異なるレスポンス
        test_cases = [
            ("スコア: 0.85\nカテゴリ: 非常に類似\n理由: 詳細な説明", 0.85, "高品質"),
            ("類似度は0.7程度です", 0.7, "中品質"),
            ("似ているようです", 0.5, "低品質")
        ]

        for response_text, expected_score, quality_level in test_cases:
            result = task_3_2_score_parser.parse_response(response_text)

            assert result.score == expected_score

            # 信頼度の妥当性確認
            if quality_level == "高品質":
                assert result.confidence > 0.7, "高品質レスポンスは高い信頼度"
            elif quality_level == "中品質":
                assert 0.3 < result.confidence <= 0.7, "中品質レスポンスは中程度の信頼度"
            else:  # 低品質
                assert result.confidence <= 0.5, "低品質レスポンスは低い信頼度"

    def test_task_3_2_integration_with_llm_similarity(self, task_3_2_score_parser):
        """
        Task 3.2: LLMSimilarityとの統合テスト

        ScoreParserがLLMSimilarityから使用される場合の動作確認
        """
        # LLMSimilarityから受け取るような構造化されたレスポンス
        structured_responses = [
            "スコア: 0.92\nカテゴリ: 非常に類似\n理由: 両テキストは同じ概念を扱っています。",
            "スコア: 0.78\nカテゴリ: 類似\n理由: 表現は異なりますが、内容は関連しています。",
            "スコア: 0.45\nカテゴリ: やや類似\n理由: 一部に共通点が見られます。"
        ]

        results = task_3_2_score_parser.parse_batch_responses(structured_responses)

        # 全ての結果が正しく解析されることを確認
        assert len(results) == 3

        for i, result in enumerate(results):
            assert isinstance(result, ParsedScore)
            assert 0.0 <= result.score <= 1.0
            assert result.category != ""
            assert result.reason != ""
            assert result.confidence > 0.5  # 構造化されたレスポンスは高信頼度

        # 統計情報の妥当性確認
        stats = task_3_2_score_parser.get_parsing_statistics()
        assert stats["success_rate"] == 1.0, "構造化レスポンスは100%成功率"

    def test_task_3_2_error_recovery_and_fallback(self, task_3_2_score_parser):
        """
        Task 3.2: エラー回復とフォールバック機能

        解析エラー時の回復機能とフォールバック戦略
        """
        # 部分的に破損したレスポンス
        partially_broken_responses = [
            "スコア: 0.8\nカテゴリ: [破損データ]",  # 一部破損
            "数値なし\nカテゴリ: 類似",  # 数値なしだがカテゴリあり
            "0.6という結果\n理由なし"  # スコアありだが構造なし
        ]

        results = []
        for response in partially_broken_responses:
            try:
                result = task_3_2_score_parser.parse_response(response)
                results.append(result)
            except ScoreParsingError:
                # エラーの場合はスキップ
                pass

        # 全ての部分的破損レスポンスが何らかの形で処理されることを確認
        assert len(results) == 3, "部分的破損レスポンスも回復可能"

        for result in results:
            assert 0.0 <= result.score <= 1.0, "スコアは有効範囲内"
            # カテゴリまたは理由のいずれかは存在する
            assert result.category != "" or result.reason != "", "何らかの情報は抽出される"