# serena 設定
claude mcp add serena -- uvx --from git+https://github.com/oraios/serena serena start-mcp-server --context ide-assistant --project $(pwd)
/init

# playwright 設定
claude mcp add playwright npx @playwright/mcp@latest

# ワークフロー
## spec-workflow 
claude mcp add spec-workflow npx @pimzino/spec-workflow-mcp@latest $(pwd)


npx -y @pimzino/spec-workflow-mcp@latest $(pwd) --dashboard

## cc-sdd
コマンドインストール
Steering Documents の作成 (/kiro:steering)
Specs テンプレートの作成 (/kiro:spec-init)
requirements.md の作成 (/kiro:spec-requirements)
design.md の作成 (/kiro:spec-design)
tasks.md の作成 (/kiro:spec-tasks)
タスク番号を指定して実行 (/kiro:spec-impl)

# 初期
コミットして https://github.com/kabayan/ccinit にpush sshキーはid_ed25519 emailはkabayan@adlibjapan.jp userはkabayan