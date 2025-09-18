#!/bin/bash

# スクリプトのディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# コピーしたいファイルリスト（スクリプトのディレクトリからの相対パス）
FILES=("init.sh" "docs/envs.md" "docs/rules.md" "docs/setup.md")

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CURDIR=$(pwd)

for FILE in "${FILES[@]}"; do
  TARGET="$CURDIR/$FILE"
  TARGET_DIR=$(dirname "$TARGET")

  # ディレクトリが存在しなければ作成
  if [ ! -d "$TARGET_DIR" ]; then
    mkdir -p "$TARGET_DIR"
    echo "ディレクトリ作成: $TARGET_DIR"
  fi

  if [ -e "$TARGET" ]; then
    read -p "$FILE が既に存在します。バックアップしますか？ [Y/n]（デフォルト:Y）: " yn
    yn=${yn:-Y}
    if [[ "$yn" =~ ^[Yy]$ ]]; then
      mv "$TARGET" "$TARGET.$TIMESTAMP"
      echo "バックアップ: $TARGET → $TARGET.$TIMESTAMP"
    else
      echo "バックアップせずに上書きします: $TARGET"
    fi
  fi
  cp "$SCRIPT_DIR/$FILE" "$TARGET"
  echo "コピー: $FILE → $TARGET"
done


# .claude 以下のファイル・ディレクトリを個別にバックアップ・コピー
CLAUDE_DIR=".claude"
if [ -d "$SCRIPT_DIR/$CLAUDE_DIR" ]; then
  find "$SCRIPT_DIR/$CLAUDE_DIR" -type f | while read ITEM; do
    REL_PATH="${ITEM#$SCRIPT_DIR/$CLAUDE_DIR/}"
    TARGET="$CURDIR/$CLAUDE_DIR/$REL_PATH"
    SRC="$ITEM"
    if [ -e "$TARGET" ]; then
      read -p "$CLAUDE_DIR/$REL_PATH が既に存在します。バックアップしますか？ [Y/n]（デフォルト:Y）: " yn
      yn=${yn:-Y}
      if [[ "$yn" =~ ^[Yy]$ ]]; then
        mv "$TARGET" "$TARGET.$TIMESTAMP"
        echo "バックアップ: $TARGET → $TARGET.$TIMESTAMP"
      else
        echo "バックアップせずに上書きします: $TARGET"
      fi
    fi
    mkdir -p "$(dirname "$CURDIR/$CLAUDE_DIR/$REL_PATH")"
    cp "$SRC" "$CURDIR/$CLAUDE_DIR/$REL_PATH"
    echo "コピー: $SRC → $CURDIR/$CLAUDE_DIR/$REL_PATH"
  done
fi