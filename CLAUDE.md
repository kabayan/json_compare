# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JSON比較ツール - 2つのJSONファイルの類似度を計算するPythonモジュール。日本語埋め込みベクトルモデル（cl-nagoya/ruri-v3-310m）を使用してフィールド値の意味的類似度を計算。

## Key Architecture

### Core Components
- `src/similarity.py`: メインの類似度計算ロジック
  - JSONの修復・パース（json_repair使用）
  - フィールド名一致率（A）× フィールド値類似度（B）で最終スコア算出
  - 再帰的な辞書・リスト比較

- `src/embedding.py`: 日本語埋め込みベクトル処理
  - ruri-v3-310mモデルをGPU上で実行
  - テキストのコサイン類似度計算
  - シングルトンパターンで初期化コスト削減

- `src/utils.py`: 数値判定・変換用ユーティリティ

## Development Constraints

1. **uvxで実行可能にする** - ローカル環境への各種インストールは原則不可
2. **APIは0.0.0.0:18081で待ち受け**
3. **パフォーマンス、認証、排他制御は実装しない** - シンプル実装を維持
4. **文ベクトルモデルはcl-nagoya/ruri-v3-310m固定** - 変更不可
5. **GPU必須** - embedding.pyはGPUがないと動作しない

## External Services

ファイル保存・変換API（192.168.1.24:28080）が利用可能：
- ファイルアップロード: `POST /file_upload/`
- フォーマット変換: `GET /download/?format={形式}`
- 対応形式: csv, json, jsonl, xlsx, yaml, huggingface(parquet)

## API Specification

入力:
- ファイル名またはファイルアクセスURL
- 結果形式:
  - "score": 全体指標を返す `{"file": ..., "score": ..., "meaning": ..., "json": ...}`
  - "file": 各行の比較結果を追加したファイルURLを返す
- コミットする場合、余計な中間ファイルやアーティファクトはコミットしない