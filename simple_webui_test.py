#!/usr/bin/env python3
"""
簡単なWebUIテスト - 接続確認
"""

import asyncio
from playwright.async_api import async_playwright

async def test_webui_connection():
    """WebUIへの基本接続テスト"""
    async with async_playwright() as p:
        print("ブラウザを起動中...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("WebUIにアクセス中...")
        await page.goto("http://localhost:18081/ui")

        print("ページタイトルを取得中...")
        title = await page.title()
        print(f"Page title: {title}")

        print("2ファイル比較ボタンを探しています...")
        dual_button = await page.query_selector('button:has-text("📑 2ファイル比較")')
        if dual_button:
            print("✓ 2ファイル比較ボタンが見つかりました")
        else:
            print("✗ 2ファイル比較ボタンが見つかりません")

        await browser.close()
        print("テスト完了")

if __name__ == "__main__":
    asyncio.run(test_webui_connection())