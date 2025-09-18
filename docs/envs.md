# 環境ルール

## 禁止事項

- [ ] 実行中コンテナへのpipインストール禁止（Dockerfile修正で対応）

## 必須実施事項

### 実行環境
- [ ] LLMはAPI経由で利用（直接利用禁止）
- [ ] LLMサーバーは既存のサーバーを利用
- [ ] LLMサーバーへのアクセスはopenai api互換エンドポイントを使う
- [ ] serena mcp、playwright mcpの使用

## LLM設定

### 利用可能LLM
1. **qwen3:14b-awq**
   ```bash
   curl -s http://192.168.1.18:8000/v1/chat/completions \
     -H "Authorization: Bearer EMPTY" \
     -H "Content-Type: application/json" \
     -d '{ 
       "model": "qwen3-14b-awq", 
       "messages": [{"role": "user", "content": "日本の首都は？"}],
       "max_tokens": 64, 
       "temperature": 0.2,
       "chat_template_kwargs": {"enable_thinking": false}
     }'
   ```

2. **qwen3:1.7b**
   ```bash
   curl -s http://192.168.1.3:8000/v1/chat/completions \
     -H "Authorization: Bearer EMPTY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "Orion-zhen/Qwen3-1.7B-AWQ",
       "messages": [{"role": "user", "content": "日本の首都は？"}],
       "max_tokens": 64,
       "temperature": 0.2,
       "chat_template_kwargs": {"enable_thinking": false}
     }'
   ```
