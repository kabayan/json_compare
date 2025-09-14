"""ユーティリティ関数モジュール"""

from typing import Any


def is_numeric(value: Any) -> bool:
    """値が数値に変換可能かを判定
    
    Args:
        value: 判定する値
    
    Returns:
        数値に変換可能ならTrue
    """
    if isinstance(value, (int, float)):
        return True
    
    if isinstance(value, str):
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    return False


def to_numeric(value: Any) -> float | None:
    """値を数値に変換
    
    Args:
        value: 変換する値
    
    Returns:
        変換された数値、変換できない場合はNone
    """
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    
    return None


def is_same_type(val1: Any, val2: Any) -> bool:
    """2つの値が同じ型かを判定
    
    Args:
        val1: 値1
        val2: 値2
    
    Returns:
        同じ型ならTrue
    """
    # NoneはNoneと同じ型
    if val1 is None and val2 is None:
        return True
    
    # 片方だけNoneの場合
    if val1 is None or val2 is None:
        return False
    
    # 基本型の判定
    return type(val1) == type(val2)