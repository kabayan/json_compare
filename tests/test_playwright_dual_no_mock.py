#!/usr/bin/env python3
"""
Playwright\u30c6\u30b9\u30c8 - \u5b9f\u30b5\u30fc\u30d0\u30fc\u3067\u306e2\u30d5\u30a1\u30a4\u30eb\u6bd4\u8f03UI\u30c6\u30b9\u30c8
"""

import asyncio
from playwright.async_api import async_playwright
import tempfile
import json
import os


async def test_dual_file_upload():
    """\u30102\u30d5\u30a1\u30a4\u30eb\u6bd4\u8f03\u6a5f\u80fd\u306e\u30c6\u30b9\u30c8"""
    print("=" * 60)
    print("2\u30d5\u30a1\u30a4\u30eb\u6bd4\u8f03UI\u30c6\u30b9\u30c8 (\u5b9f\u30b5\u30fc\u30d0\u30fc)")
    print("=" * 60)

    # \u30c6\u30b9\u30c8\u30d5\u30a1\u30a4\u30eb1\u3092\u4f5c\u6210
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data1 = [
            {"id": 1, "inference": '{"name": "Alice", "age": 25}', "other": "data1"},
            {"id": 2, "inference": '{"city": "Tokyo", "country": "Japan"}', "other": "data2"},
            {"id": 3, "inference": '{"status": "active", "level": 5}', "other": "data3"}
        ]
        for item in test_data1:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        test_file1 = f.name

    # \u30c6\u30b9\u30c8\u30d5\u30a1\u30a4\u30eb2\u3092\u4f5c\u6210
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data2 = [
            {"id": 1, "inference": '{"name": "Alice", "age": 30}', "other": "data4"},
            {"id": 2, "inference": '{"city": "Osaka", "country": "Japan"}', "other": "data5"},
            {"id": 3, "inference": '{"status": "inactive", "level": 3}', "other": "data6"}
        ]
        for item in test_data2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        test_file2 = f.name

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # UI\u3092\u958b\u304f
            print("\n1. UI\u30da\u30fc\u30b8\u306b\u30a2\u30af\u30bb\u30b9...")
            await page.goto("http://localhost:18081/ui", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("\u2705 \u30da\u30fc\u30b8\u304c\u8aad\u307f\u8fbc\u307e\u308c\u307e\u3057\u305f")

            # 2\u30d5\u30a1\u30a4\u30eb\u30e2\u30fc\u30c9\u306b\u5207\u308a\u66ff\u3048
            print("\n2. 2\u30d5\u30a1\u30a4\u30eb\u30e2\u30fc\u30c9\u306b\u5207\u308a\u66ff\u3048...")
            dual_tab = page.locator('button.tab-button[data-mode="dual"]')
            await dual_tab.click()
            await page.wait_for_timeout(500)  # \u30a2\u30cb\u30e1\u30fc\u30b7\u30e7\u30f3\u5f85\u6a5f

            # dual\u30d5\u30a9\u30fc\u30e0\u304c\u8868\u793a\u3055\u308c\u3066\u3044\u308b\u304b\u78ba\u8a8d
            dual_form = page.locator("#dualForm")
            is_visible = await dual_form.is_visible()
            if is_visible:
                print("\u2705 2\u30d5\u30a1\u30a4\u30eb\u30e2\u30fc\u30c9\u306e\u30d5\u30a9\u30fc\u30e0\u304c\u8868\u793a\u3055\u308c\u307e\u3057\u305f")
            else:
                print("\u2757 2\u30d5\u30a1\u30a4\u30eb\u30e2\u30fc\u30c9\u306e\u30d5\u30a9\u30fc\u30e0\u304c\u8868\u793a\u3055\u308c\u3066\u3044\u307e\u305b\u3093")

            # \u30d5\u30a1\u30a4\u30eb\u3092\u9078\u629e
            print("\n3. \u30d5\u30a1\u30a4\u30eb\u3092\u9078\u629e...")
            file1_input = page.locator('#dualForm input[name="file1"]')
            file2_input = page.locator('#dualForm input[name="file2"]')

            await file1_input.set_input_files(test_file1)
            print(f"   \u30d5\u30a1\u30a4\u30eb1: {test_file1}")

            await file2_input.set_input_files(test_file2)
            print(f"   \u30d5\u30a1\u30a4\u30eb2: {test_file2}")

            # \u30ab\u30e9\u30e0\u540d\u3092\u78ba\u8a8d
            column_input = page.locator('#dualForm input[name="column"]')
            column_value = await column_input.input_value()
            print(f"   \u6bd4\u8f03\u5217: {column_value}")

            # \u30d5\u30a9\u30fc\u30e0\u3092\u9001\u4fe1
            print("\n4. \u30d5\u30a9\u30fc\u30e0\u3092\u9001\u4fe1...")
            submit_button = page.locator('#dualForm button[type="submit"]')
            await submit_button.click()

            # \u51e6\u7406\u5b8c\u4e86\u3092\u5f85\u3064\uff0860\u79d2\u30bf\u30a4\u30e0\u30a2\u30a6\u30c8\uff09
            print("   \u51e6\u7406\u4e2d... (\u6700\u592760\u79d2\u5f85\u6a5f)")
            result_container = page.locator("#result")

            # \u7d50\u679c\u304c\u8868\u793a\u3055\u308c\u308b\u306e\u3092\u5f85\u3064
            await result_container.wait_for(state="visible", timeout=60000)

            # \u7d50\u679c\u3092\u53d6\u5f97
            result_text = await result_container.text_content()

            if result_text:
                print("\n\u2705 \u7d50\u679c\u304c\u8868\u793a\u3055\u308c\u307e\u3057\u305f\uff01")

                # JSON\u7d50\u679c\u306e\u4e00\u90e8\u3092\u8868\u793a
                if len(result_text) > 200:
                    print(f"\u7d50\u679c\u306e\u4e00\u90e8: {result_text[:200]}...")
                else:
                    print(f"\u7d50\u679c: {result_text}")

                # \u7d50\u679c\u306b\u5fc5\u8981\u306a\u30ad\u30fc\u304c\u542b\u307e\u308c\u3066\u3044\u308b\u304b\u78ba\u8a8d
                if "total_lines" in result_text:
                    print("   \u2713 total_lines \u304c\u542b\u307e\u308c\u3066\u3044\u307e\u3059")
                if "score" in result_text:
                    print("   \u2713 score \u304c\u542b\u307e\u308c\u3066\u3044\u307e\u3059")
                if "_metadata" in result_text:
                    print("   \u2713 _metadata \u304c\u542b\u307e\u308c\u3066\u3044\u307e\u3059")

                # JSON\u3068\u3057\u3066\u30d1\u30fc\u30b9\u3067\u304d\u308b\u304b\u78ba\u8a8d
                try:
                    result_json = json.loads(result_text)
                    print("\n   \u7d50\u679c\u306e\u8a73\u7d30:")
                    print(f"   - \u7dcf\u884c\u6570: {result_json.get('total_lines', 'N/A')}")
                    print(f"   - \u30b9\u30b3\u30a2: {result_json.get('score', 'N/A')}")
                    print(f"   - \u610f\u5473: {result_json.get('meaning', 'N/A')}")
                    if '_metadata' in result_json:
                        print(f"   - \u6bd4\u8f03\u5217: {result_json['_metadata'].get('column_compared', 'N/A')}")
                        print(f"   - \u6bd4\u8f03\u884c\u6570: {result_json['_metadata'].get('rows_compared', 'N/A')}")
                except json.JSONDecodeError:
                    print("   \u26a0\ufe0f JSON\u30d1\u30fc\u30b9\u306b\u5931\u6557\u3057\u307e\u3057\u305f\u304c\u3001\u7d50\u679c\u306f\u8868\u793a\u3055\u308c\u3066\u3044\u307e\u3059")
            else:
                print("\u2757 \u7d50\u679c\u304c\u7a7a\u3067\u3059")

            print("\n" + "=" * 60)
            print("\u2728 2\u30d5\u30a1\u30a4\u30eb\u6bd4\u8f03\u30c6\u30b9\u30c8\u304c\u5b8c\u4e86\u3057\u307e\u3057\u305f\uff01")
            print("=" * 60)

        except Exception as e:
            print(f"\n\u274c \u30a8\u30e9\u30fc\u767a\u751f: {e}")
            await page.screenshot(path="dual_test_error.png")
            print("\u30a8\u30e9\u30fc\u6642\u306e\u30b9\u30af\u30ea\u30fc\u30f3\u30b7\u30e7\u30c3\u30c8\u3092 dual_test_error.png \u306b\u4fdd\u5b58\u3057\u307e\u3057\u305f")

        finally:
            await browser.close()
            os.unlink(test_file1)
            os.unlink(test_file2)
            print("\n\u4e00\u6642\u30d5\u30a1\u30a4\u30eb\u3092\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u3057\u307e\u3057\u305f")


async def test_custom_column():
    """\u30ab\u30b9\u30bf\u30e0\u5217\u540d\u3067\u306e\u6bd4\u8f03\u30c6\u30b9\u30c8"""
    print("\n" + "=" * 60)
    print("\u30ab\u30b9\u30bf\u30e0\u5217\u540d\u3067\u306e2\u30d5\u30a1\u30a4\u30eb\u6bd4\u8f03\u30c6\u30b9\u30c8")
    print("=" * 60)

    # \u30c6\u30b9\u30c8\u30d5\u30a1\u30a4\u30eb\u3092\u4f5c\u6210\uff08\u30ab\u30b9\u30bf\u30e0\u5217\u540d\u4f7f\u7528\uff09
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data1 = [
            {"id": 1, "output": '{"result": "success", "code": 200}'},
            {"id": 2, "output": '{"result": "pending", "code": 202}'}
        ]
        for item in test_data1:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        test_file1 = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        test_data2 = [
            {"id": 1, "output": '{"result": "failure", "code": 500}'},
            {"id": 2, "output": '{"result": "success", "code": 200}'}
        ]
        for item in test_data2:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
        test_file2 = f.name

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # UI\u3092\u958b\u304f
            print("\n1. UI\u30da\u30fc\u30b8\u306b\u30a2\u30af\u30bb\u30b9...")
            await page.goto("http://localhost:18081/ui", timeout=10000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            print("\u2705 \u30da\u30fc\u30b8\u304c\u8aad\u307f\u8fbc\u307e\u308c\u307e\u3057\u305f")

            # 2\u30d5\u30a1\u30a4\u30eb\u30e2\u30fc\u30c9\u306b\u5207\u308a\u66ff\u3048
            print("\n2. 2\u30d5\u30a1\u30a4\u30eb\u30e2\u30fc\u30c9\u306b\u5207\u308a\u66ff\u3048...")
            dual_tab = page.locator('button.tab-button[data-mode="dual"]')
            await dual_tab.click()
            await page.wait_for_timeout(500)

            # \u30d5\u30a1\u30a4\u30eb\u3092\u9078\u629e
            print("\n3. \u30d5\u30a1\u30a4\u30eb\u3092\u9078\u629e...")
            file1_input = page.locator('#dualForm input[name="file1"]')
            file2_input = page.locator('#dualForm input[name="file2"]')

            await file1_input.set_input_files(test_file1)
            await file2_input.set_input_files(test_file2)

            # \u30ab\u30b9\u30bf\u30e0\u5217\u540d\u3092\u8a2d\u5b9a
            print("\n4. \u30ab\u30b9\u30bf\u30e0\u5217\u540d 'output' \u3092\u8a2d\u5b9a...")
            column_input = page.locator('#dualForm input[name="column"]')
            await column_input.fill("output")

            # \u30d5\u30a9\u30fc\u30e0\u3092\u9001\u4fe1
            print("\n5. \u30d5\u30a9\u30fc\u30e0\u3092\u9001\u4fe1...")
            submit_button = page.locator('#dualForm button[type="submit"]')
            await submit_button.click()

            # \u7d50\u679c\u3092\u5f85\u3064
            print("   \u51e6\u7406\u4e2d...")
            result_container = page.locator("#result")
            await result_container.wait_for(state="visible", timeout=60000)

            result_text = await result_container.text_content()

            if result_text:
                print("\n\u2705 \u30ab\u30b9\u30bf\u30e0\u5217\u540d\u3067\u306e\u6bd4\u8f03\u7d50\u679c\u304c\u8868\u793a\u3055\u308c\u307e\u3057\u305f\uff01")

                try:
                    result_json = json.loads(result_text)
                    if '_metadata' in result_json:
                        column_compared = result_json['_metadata'].get('column_compared', '')
                        if column_compared == 'output':
                            print("   \u2713 \u6b63\u3057\u304f 'output' \u5217\u304c\u6bd4\u8f03\u3055\u308c\u307e\u3057\u305f")
                        else:
                            print(f"   \u26a0\ufe0f \u4e88\u671f\u3057\u306a\u3044\u5217\u540d: {column_compared}")
                except:
                    pass

            print("\n" + "=" * 60)
            print("\u2728 \u30ab\u30b9\u30bf\u30e0\u5217\u540d\u30c6\u30b9\u30c8\u304c\u5b8c\u4e86\u3057\u307e\u3057\u305f\uff01")
            print("=" * 60)

        except Exception as e:
            print(f"\n\u274c \u30a8\u30e9\u30fc\u767a\u751f: {e}")

        finally:
            await browser.close()
            os.unlink(test_file1)
            os.unlink(test_file2)
            print("\n\u4e00\u6642\u30d5\u30a1\u30a4\u30eb\u3092\u30af\u30ea\u30fc\u30f3\u30a2\u30c3\u30d7\u3057\u307e\u3057\u305f")


async def main():
    """\u30e1\u30a4\u30f3\u30c6\u30b9\u30c8\u5b9f\u884c"""
    print("\n" + "=" * 60)
    print("Playwright\u306b\u3088\u308b2\u30d5\u30a1\u30a4\u30eb\u6bd4\u8f03UI\u30c6\u30b9\u30c8")
    print("\uff08\u30e2\u30c3\u30af\u306a\u3057\u30fb\u5b9f\u30b5\u30fc\u30d0\u30fc\u4f7f\u7528\uff09")
    print("=" * 60 + "\n")

    # 2\u30d5\u30a1\u30a4\u30eb\u6bd4\u8f03\u30c6\u30b9\u30c8
    await test_dual_file_upload()

    # \u30ab\u30b9\u30bf\u30e0\u5217\u540d\u30c6\u30b9\u30c8
    await test_custom_column()

    print("\n" + "=" * 60)
    print("\u3059\u3079\u3066\u306e\u30c6\u30b9\u30c8\u304c\u5b8c\u4e86\u3057\u307e\u3057\u305f\uff01")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())