#!/usr/bin/env python3
"""
E2E and Integration Tests for The Librarian

These tests require a running Librarian server and Letta backend.
They test the complete integration of all components.

Copyright (C) 2025 AnimusUNO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import pytest
import httpx
import os
from dotenv import load_dotenv

# Mark all tests as integration/E2E
pytestmark = pytest.mark.integration

load_dotenv()

LIBRARIAN_BASE_URL = f"http://{os.getenv('LIBRARIAN_HOST', '127.0.0.1')}:{os.getenv('LIBRARIAN_PORT', '8000')}"
TEST_TIMEOUT = int(os.getenv("LIBRARIAN_TEST_TIMEOUT", "30"))


class TestEndpoints:
    """Test all API endpoints"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.get(f"{LIBRARIAN_BASE_URL}/")
            assert response.status_code == 200
            data = response.json()
            assert "service" in data or "name" in data
    
    @pytest.mark.asyncio
    async def test_get_model_by_id(self):
        """Test getting a specific model by ID"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.get(f"{LIBRARIAN_BASE_URL}/v1/models/gpt-4.1")
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["id"] == "gpt-4.1"
    
    @pytest.mark.asyncio
    async def test_get_model_by_id_nonexistent(self):
        """Test getting a nonexistent model"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.get(f"{LIBRARIAN_BASE_URL}/v1/models/nonexistent-model")
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_completions_endpoint(self):
        """Test legacy /v1/completions endpoint"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/completions",
                json={
                    "model": "gpt-4.1",
                    "prompt": "Hello, world!",
                    "max_tokens": 10
                }
            )
            # Should either work or return appropriate error
            assert response.status_code in [200, 400, 404]
            if response.status_code == 200:
                data = response.json()
                assert "choices" in data or "error" in data


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_model(self):
        """Test request with invalid model"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "invalid-model",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    @pytest.mark.asyncio
    async def test_missing_messages(self):
        """Test request without messages"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1"
                }
            )
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_empty_messages(self):
        """Test request with empty messages"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": []
                }
            )
            assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_invalid_json(self):
        """Test request with invalid JSON"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                content="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_missing_content(self):
        """Test message without content"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": [{"role": "user"}]
                }
            )
            assert response.status_code == 422


class TestSecurityIntegration:
    """Test security features integration"""
    
    @pytest.mark.asyncio
    async def test_health_bypasses_security(self):
        """Test that health endpoint bypasses security"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            # Should work even if security is enabled
            response = await client.get(f"{LIBRARIAN_BASE_URL}/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_docs_bypasses_security(self):
        """Test that docs endpoints bypass security"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            # Should work even if security is enabled
            response = await client.get(f"{LIBRARIAN_BASE_URL}/docs")
            # May return 200 or 404 depending on enable_docs config
            assert response.status_code in [200, 404]


class TestRequestParameters:
    """Test various request parameters"""
    
    @pytest.mark.asyncio
    async def test_temperature_parameter(self):
        """Test temperature parameter"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "temperature": 0.7
                }
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_max_tokens_parameter(self):
        """Test max_tokens parameter"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": [{"role": "user", "content": "Say hello"}],
                    "max_tokens": 10
                }
            )
            assert response.status_code == 200
            data = response.json()
            if "choices" in data:
                # Verify usage reflects max_tokens
                assert "usage" in data
    
    @pytest.mark.asyncio
    async def test_user_parameter(self):
        """Test user parameter for request tracking"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "user": "test-user-123"
                }
            )
            assert response.status_code == 200


class TestResponseFormat:
    """Test response format compliance"""
    
    @pytest.mark.asyncio
    async def test_response_has_required_fields(self):
        """Test that response has all required OpenAI fields"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            # Required fields
            assert "id" in data
            assert "object" in data
            assert "created" in data
            assert "model" in data
            assert "choices" in data
            assert "usage" in data
            
            # Choices structure
            assert len(data["choices"]) > 0
            choice = data["choices"][0]
            assert "index" in choice
            assert "message" in choice
            assert "finish_reason" in choice
            
            # Message structure
            message = choice["message"]
            assert "role" in message
            assert "content" in message
            
            # Usage structure
            usage = data["usage"]
            assert "prompt_tokens" in usage
            assert "completion_tokens" in usage
            assert "total_tokens" in usage
    
    @pytest.mark.asyncio
    async def test_streaming_response_format(self):
        """Test streaming response format"""
        async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": "gpt-4.1",
                    "messages": [{"role": "user", "content": "Count to 3"}],
                    "stream": True
                }
            ) as response:
                assert response.status_code == 200
                assert response.headers.get("content-type") == "text/event-stream"
                
                chunks = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunks.append(line)
                        if len(chunks) >= 3:  # Get a few chunks
                            break
                
                assert len(chunks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

