# serena 設定
claude mcp add serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant --project $(pwd)
/init

# playwright 設定
claude mcp add playwright npx @playwright/mcp@latest

# ワークフロー
## spec-workflow(新規) 
### claude code UI
https://github.com/siteboon/claudecodeui

#### インストール

##### nodeが古い場合
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm use 20
nvm alias default 20
nvm install 20
rm -rf node_modules package-lock.json
npm install

##### インストール
git clone https://github.com/siteboon/claudecodeui.git
cd claudecodeui
npm install
cp .env.example .env
npm run dev

#### WebUI
http://localhost:3001

### セットアップ
claude mcp add spec-workflow npx @pimzino/spec-workflow-mcp@latest $(pwd)
#### WebUI
npx -y @pimzino/spec-workflow-mcp@latest $(pwd) --dashboard
### 使い方
1. @docs/sped.md, @docs/rules.md, @docs/envs.mdを基に spec を作成して
    - ここでのspec名を覚えておく
2. webuiでタスク確認
3. spec に 機能：ｘｘを追加して更新
4. webuiでタスク確認。足りなければ３へ
5. task.mdを参考に task 〇〇を実装。モックテスト不可、Dockerコンテナ内実施必須。100%テストpassは必要。 @docs/rules.md を厳守していること。簡易的なテストは不可。テストデータの変更による100%成功は不可

## cc-sdd（既存拡張）

### セットアップ

#### claude-code-viewer
PORT=3400 npx @kimuson/claude-code-viewer@latest

#### インストール
npx cc-sdd@latest --lang ja

### 使い方
- https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/README_ja.md
- https://zenn.dev/kokushing/articles/7468d5f195e54c

1. Steering Documents の作成 (/kiro:steering)
2. Specs テンプレートの作成 
- /kiro:spec-init 追加機能
3. requirements.md の作成 (/kiro:spec-requirements)
    - .kiro/xx/requirement.md を確認
    /kiro:steering llm-similarity-vllm

4. design.md の作成 
/kiro:spec-design llm-similarity-vllm
/kiro:steering llm-similarity-vllm

5. tasks.md の作成 
/kiro:spec-tasks llm-similarity-vllm
/kiro:steering llm-similarity-vllm

6. タスク番号を指定して実行 
/kiro:spec-impl llm-similarity-vllm タスク1から順番に進めて

7. /kiro:spec-status 進捗を確認

# 初期
コミットして https://github.com/kabayan/ccinit にpush sshキーはid_ed25519 emailはkabayan@adlibjapan.jp userはkabayan

# フロー例
## specbase.mdを作成
概要仕様を作成

## specを作成
@docs/specbase.md を基に specを作成。各種ドキュメントは日本語で作成。

## rules.md を反映
@docs/rules.md を specに反映

## steering documentsを作成
steering documents を日本語で作成

## spec を更新後にやること
タスクも spec の更新に対応させて

# github tip
https://github.com/kabayan/ccinit をカレントにpull。サブフォルダは作らない。sshキーはid_ed25519