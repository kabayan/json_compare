"""JSON類似度計算のメインモジュール"""

import json
from typing import Any
from json_repair import repair_json

from .embedding import JapaneseEmbedding
from .utils import is_numeric, to_numeric


# グローバルで埋め込みモデルを保持（初期化コストを削減）
_embedding_model = None


def get_embedding_model():
    """埋め込みモデルのシングルトンインスタンスを取得"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = JapaneseEmbedding()
    return _embedding_model


def calculate_json_similarity(json1: str, json2: str) -> float:
    """2つのJSON文字列の類似度を計算
    
    Args:
        json1: 比較するJSON文字列1
        json2: 比較するJSON文字列2
    
    Returns:
        類似度 (0-1)
    """
    # JSON修復とパース
    dict1 = repair_and_parse_json(json1)
    dict2 = repair_and_parse_json(json2)
    
    # いずれかが修復できなければ0を返す
    if dict1 is None or dict2 is None:
        return 0.0
    
    # フィールド名一致率（A）
    field_match_ratio = calculate_field_match_ratio(dict1, dict2)
    
    # フィールド値類似度（B）
    field_similarity = calculate_field_similarity(dict1, dict2)
    
    # A × B を類似度とする
    return field_match_ratio * field_similarity


def repair_and_parse_json(json_str: str) -> dict | None:
    """JSON文字列を修復してパース
    
    Args:
        json_str: JSON文字列
    
    Returns:
        パースされた辞書、失敗時はNone
    """
    try:
        # まず通常のパースを試みる
        return json.loads(json_str)
    except:
        try:
            # 失敗したらjson_repairで修復
            repaired = repair_json(json_str)
            return json.loads(repaired)
        except:
            # 修復も失敗したらNone
            return None


def calculate_field_match_ratio(dict1: dict, dict2: dict) -> float:
    """フィールド名の一致率を計算（A）
    
    Args:
        dict1: 辞書1
        dict2: 辞書2
    
    Returns:
        フィールド名一致率 (0-1)
    """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return 0.0
    
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())
    
    # 両方が空の場合
    if len(keys1) == 0 and len(keys2) == 0:
        return 0.0
    
    # 共通フィールド数
    common_keys = keys1 & keys2
    
    # 全体のフィールド数の最大値
    max_keys = max(len(keys1), len(keys2))
    
    return len(common_keys) / max_keys if max_keys > 0 else 0.0


def calculate_field_similarity(dict1: dict, dict2: dict) -> float:
    """共通フィールドの値の類似度を計算（B）
    
    Args:
        dict1: 辞書1
        dict2: 辞書2
    
    Returns:
        フィールド値類似度 (0-1)
    """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return 0.0
    
    # 共通フィールド
    common_keys = set(dict1.keys()) & set(dict2.keys())
    
    if len(common_keys) == 0:
        return 0.0
    
    # 各フィールドの類似度を計算
    total_similarity = 0.0
    for key in common_keys:
        similarity = compare_values(dict1[key], dict2[key])
        total_similarity += similarity
    
    # 共通フィールド数で正規化
    return total_similarity / len(common_keys)


def compare_values(val1: Any, val2: Any) -> float:
    """2つの値の類似度を比較
    
    Args:
        val1: 値1
        val2: 値2
    
    Returns:
        類似度 (0-1)
    """
    # 完全一致
    if val1 == val2:
        return 1.0
    
    # 両方null/None
    if val1 is None and val2 is None:
        return 1.0
    
    # 片方だけnull
    if val1 is None or val2 is None:
        return 0.0
    
    # リストの場合
    if isinstance(val1, list) and isinstance(val2, list):
        return compare_lists(val1, val2)
    
    # 辞書（オブジェクト）の場合は再帰的に処理
    if isinstance(val1, dict) and isinstance(val2, dict):
        # 再帰的に類似度計算
        field_match = calculate_field_match_ratio(val1, val2)
        field_sim = calculate_field_similarity(val1, val2)
        return field_match * field_sim
    
    # 数値の比較
    if is_numeric(val1) and is_numeric(val2):
        num1 = to_numeric(val1)
        num2 = to_numeric(val2)
        if num1 == num2:
            return 1.0
        else:
            # 数値が異なる場合は一律0.1
            return 0.1
    
    # その他の場合は埋め込みベクトルで類似度計算
    embedding = get_embedding_model()
    return embedding.calculate_similarity(str(val1), str(val2))


def compare_lists(list1: list, list2: list) -> float:
    """リストの類似度を比較
    
    Args:
        list1: リスト1
        list2: リスト2
    
    Returns:
        類似度 (0-1)
    """
    # 両方空リストの場合
    if len(list1) == 0 and len(list2) == 0:
        return 1.0
    
    # 片方だけ空リストの場合
    if len(list1) == 0 or len(list2) == 0:
        return 0.0
    
    # リストのコピーを作成（破壊的変更を避ける）
    remaining1 = list1.copy()
    remaining2 = list2.copy()
    
    similarity_sum = 0.0
    matched_count = 0
    
    # Step 1: 完全一致を除外
    i = 0
    while i < len(remaining1):
        found = False
        for j in range(len(remaining2)):
            if remaining1[i] == remaining2[j]:
                similarity_sum += 1.0
                matched_count += 1
                remaining1.pop(i)
                remaining2.pop(j)
                found = True
                break
        if not found:
            i += 1
    
    # Step 2: 残った要素で類似度計算
    while remaining1 and remaining2:
        best_similarity = 0.0
        best_i = 0
        best_j = 0
        
        # 最も類似度の高いペアを探す
        for i in range(len(remaining1)):
            for j in range(len(remaining2)):
                sim = compare_values(remaining1[i], remaining2[j])
                if sim > best_similarity:
                    best_similarity = sim
                    best_i = i
                    best_j = j
        
        # 最も類似度の高いペアを除外
        similarity_sum += best_similarity
        matched_count += 1
        remaining1.pop(best_i)
        remaining2.pop(best_j)
    
    # 長い方のリスト長
    max_length = max(len(list1), len(list2))
    
    # マッチしなかった要素がある場合
    unmatched_count = len(remaining1) + len(remaining2)
    if unmatched_count > 0:
        # 残った要素数+1で割る
        return similarity_sum / (unmatched_count + 1)
    else:
        # 全てマッチした場合
        return similarity_sum / max_length