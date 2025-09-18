#!/usr/bin/env python3
"""Playwright tests for file upload functionality"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest
from playwright.async_api import async_playwright, APIRequestContext, expect


class TestFileUploadAPI:
    """API tests for file upload functionality using Playwright"""

    @pytest.fixture(scope="session")
    async def api_server(self):
        """Start the API server for testing"""
        # Note: In production, you would start the server programmatically
        # For now, assume server is running on localhost:18081
        base_url = "http://localhost:18081"
        return base_url

    @pytest.fixture
    async def api_context(self, api_server):
        """Create Playwright API request context"""
        async with async_playwright() as p:
            context = await p.request.new_context(base_url=api_server)
            yield context
            await context.dispose()

    @pytest.fixture
    def sample_jsonl_file(self):
        """Create a sample JSONL file for testing"""
        content = [
            {"inference1": "これはテスト文章です", "inference2": "これは試験文書です"},
            {"inference1": "機械学習は便利です", "inference2": "機械学習は有用です"}
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for item in content:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    @pytest.fixture
    def large_jsonl_file(self):
        """Create a large JSONL file for testing size limits"""
        # Create a file just under 100MB
        content = {"inference1": "テスト文章", "inference2": "試験文書"}
        line = json.dumps(content, ensure_ascii=False) + '\n'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Write enough lines to approach 100MB
            size = 0
            max_size = 99 * 1024 * 1024  # 99MB
            while size < max_size:
                f.write(line)
                size += len(line.encode('utf-8'))
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    @pytest.fixture
    def invalid_json_file(self):
        """Create an invalid JSON file for testing validation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("This is not valid JSON\n")
            f.write('{"broken": json}\n')
            temp_path = f.name

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_health_check(self, api_context: APIRequestContext):
        """Test the health check endpoint"""
        response = await api_context.get("/health")
        assert response.ok
        data = await response.json()
        assert data["status"] == "healthy"
        assert data["cli_available"] is True

    @pytest.mark.asyncio
    async def test_upload_valid_jsonl(self, api_context: APIRequestContext, sample_jsonl_file):
        """Test uploading a valid JSONL file"""
        with open(sample_jsonl_file, 'rb') as f:
            file_content = f.read()

        response = await api_context.post("/api/compare/single",
            multipart={
                "file": {
                    "name": "test.jsonl",
                    "mimeType": "application/x-jsonl",
                    "buffer": file_content
                },
                "type": "score",
                "gpu": "false"
            }
        )

        assert response.ok
        data = await response.json()

        # Check for successful processing
        assert "score" in data or "_metadata" in data
        if "_metadata" in data:
            assert "processing_time" in data["_metadata"]
            assert "original_filename" in data["_metadata"]

    @pytest.mark.asyncio
    async def test_upload_file_type_validation(self, api_context: APIRequestContext):
        """Test file type validation"""
        # Create a non-JSONL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a text file")
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                file_content = f.read()

            response = await api_context.post("/api/compare/single",
                multipart={
                    "file": {
                        "name": "test.txt",
                        "mimeType": "text/plain",
                        "buffer": file_content
                    },
                    "type": "score",
                    "gpu": "false"
                }
            )

            assert response.status == 400
            data = await response.json()
            assert "detail" in data
            assert "JSONLファイル(.jsonl拡張子)のみ" in data["detail"]["detail"]

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_upload_invalid_type_parameter(self, api_context: APIRequestContext, sample_jsonl_file):
        """Test invalid type parameter"""
        with open(sample_jsonl_file, 'rb') as f:
            file_content = f.read()

        response = await api_context.post("/api/compare/single",
            multipart={
                "file": {
                    "name": "test.jsonl",
                    "mimeType": "application/x-jsonl",
                    "buffer": file_content
                },
                "type": "invalid",
                "gpu": "false"
            }
        )

        assert response.status == 400
        data = await response.json()
        assert "type must be 'score' or 'file'" in data["detail"]["detail"]

    @pytest.mark.asyncio
    async def test_upload_with_gpu_option(self, api_context: APIRequestContext, sample_jsonl_file):
        """Test upload with GPU option enabled"""
        with open(sample_jsonl_file, 'rb') as f:
            file_content = f.read()

        response = await api_context.post("/api/compare/single",
            multipart={
                "file": {
                    "name": "test.jsonl",
                    "mimeType": "application/x-jsonl",
                    "buffer": file_content
                },
                "type": "file",
                "gpu": "true"
            }
        )

        assert response.ok
        data = await response.json()

        # For file type, expect a list of results
        if isinstance(data, list):
            assert len(data) > 0
            # Check structure of results
            for item in data:
                assert "similarity_score" in item or "input" in item

    @pytest.mark.asyncio
    async def test_upload_invalid_json_structure(self, api_context: APIRequestContext, invalid_json_file):
        """Test upload with invalid JSON structure"""
        with open(invalid_json_file, 'rb') as f:
            file_content = f.read()

        response = await api_context.post("/api/compare/single",
            multipart={
                "file": {
                    "name": "invalid.jsonl",
                    "mimeType": "application/x-jsonl",
                    "buffer": file_content
                },
                "type": "score",
                "gpu": "false"
            }
        )

        assert response.status == 400
        data = await response.json()
        assert "JSONパースエラー" in str(data)

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, api_context: APIRequestContext):
        """Test upload with empty file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Create empty file
            temp_path = f.name

        try:
            with open(temp_path, 'rb') as f:
                file_content = f.read()

            response = await api_context.post("/api/compare/single",
                multipart={
                    "file": {
                        "name": "empty.jsonl",
                        "mimeType": "application/x-jsonl",
                        "buffer": file_content
                    },
                    "type": "score",
                    "gpu": "false"
                }
            )

            assert response.status == 400
            data = await response.json()
            assert "ファイルが空です" in data["detail"]["detail"]

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @pytest.mark.asyncio
    async def test_concurrent_uploads(self, api_context: APIRequestContext, sample_jsonl_file):
        """Test concurrent file uploads"""
        with open(sample_jsonl_file, 'rb') as f:
            file_content = f.read()

        # Send multiple requests concurrently
        tasks = []
        for i in range(3):
            task = api_context.post("/api/compare/single",
                multipart={
                    "file": {
                        "name": f"test_{i}.jsonl",
                        "mimeType": "application/x-jsonl",
                        "buffer": file_content
                    },
                    "type": "score",
                    "gpu": "false"
                }
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.ok
            data = await response.json()
            assert "score" in data or "_metadata" in data


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])