"""日本語埋め込みベクトル処理モジュール"""

import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np
from scipy.spatial.distance import cosine


class JapaneseEmbedding:
    """日本語埋め込みベクトルを使用した類似度計算クラス"""

    def __init__(self, use_gpu: bool = False):
        """ruri-v3-310mモデルの初期化

        Args:
            use_gpu: GPUを使用するかどうか (default: False)
        """
        # デバイス選択
        if use_gpu and torch.cuda.is_available():
            self.device = torch.device("cuda")
        else:
            self.device = torch.device("cpu")

        # モデルとトークナイザーのロード
        model_name = "cl-nagoya/ruri-v3-310m"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """2つのテキストのコサイン類似度を計算
        
        Args:
            text1: 比較するテキスト1
            text2: 比較するテキスト2
        
        Returns:
            コサイン類似度 (0-1)
        """
        # 空文字列の処理
        if not text1 or not text2:
            return 1.0 if text1 == text2 else 0.0
        
        # 埋め込みベクトルを取得
        with torch.no_grad():
            # テキスト1の埋め込み
            inputs1 = self.tokenizer(text1, return_tensors="pt", 
                                   padding=True, truncation=True, max_length=512)
            inputs1 = {k: v.to(self.device) for k, v in inputs1.items()}
            outputs1 = self.model(**inputs1)
            embedding1 = outputs1.last_hidden_state.mean(dim=1).cpu().numpy()[0]
            
            # テキスト2の埋め込み
            inputs2 = self.tokenizer(text2, return_tensors="pt",
                                   padding=True, truncation=True, max_length=512)
            inputs2 = {k: v.to(self.device) for k, v in inputs2.items()}
            outputs2 = self.model(**inputs2)
            embedding2 = outputs2.last_hidden_state.mean(dim=1).cpu().numpy()[0]
        
        # コサイン類似度計算
        similarity = 1 - cosine(embedding1, embedding2)
        
        # 0-1の範囲に収める
        return max(0.0, min(1.0, similarity))