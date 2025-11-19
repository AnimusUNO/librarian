#!/usr/bin/env python3
"""
Test script for The Librarian integration
Tests the complete OpenAI-compatible API with Letta backend
Fully configurable via environment variables
"""

import asyncio
import json
import httpx
import os
import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment
LIBRARIAN_BASE_URL = f"http://{os.getenv('LIBRARIAN_HOST', '127.0.0.1')}:{os.getenv('LIBRARIAN_PORT', '8000')}"
TEST_TIMEOUT = int(os.getenv("LIBRARIAN_TEST_TIMEOUT", "30"))
TEST_MODELS = os.getenv("LIBRARIAN_TEST_MODELS", "gpt-3.5-turbo,gpt-4").split(",")
ENABLE_STREAMING_TESTS = os.getenv("LIBRARIAN_ENABLE_STREAMING_TESTS", "true").lower() == "true"
ENABLE_TOOL_TESTS = os.getenv("LIBRARIAN_ENABLE_TOOL_TESTS", "false").lower() == "true"
VERBOSE_OUTPUT = os.getenv("LIBRARIAN_TEST_VERBOSE", "false").lower() == "true"

@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    print("Testing health check...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{LIBRARIAN_BASE_URL}/health")
        print(f"Health check status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200

@pytest.mark.asyncio
async def test_models_endpoint():
    """Test models listing endpoint"""
    print("\nTesting models endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{LIBRARIAN_BASE_URL}/v1/models")
        print(f"Models endpoint status: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(f"Available models: {[model['id'] for model in models['data']]}")
        return response.status_code == 200

@pytest.mark.asyncio
async def test_chat_completion(model: str = "gpt-3.5-turbo"):
    """Test chat completion endpoint"""
    print(f"\nTesting chat completion with model: {model}")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hello! Can you tell me what you are?"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Chat completion status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response ID: {result['id']}")
                print(f"Model: {result['model']}")
                print(f"Content: {result['choices'][0]['message']['content']}")
                print(f"Usage: {result['usage']}")
                return True
            else:
                print(f"Error response: {response.text}")
                return False
                
        except httpx.TimeoutException:
            print("Request timed out - Letta server may not be running")
            return False
        except Exception as e:
            print(f"Error: {str(e)}")
            return False

@pytest.mark.asyncio
async def test_streaming_completion(model: str = "gpt-3.5-turbo"):
    """Test streaming chat completion"""
    if not ENABLE_STREAMING_TESTS:
        print(f"\nSkipping streaming test (disabled)")
        return True
        
    print(f"\nTesting streaming completion with model: {model}")
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Tell me a short story about a robot."}
        ],
        "stream": True,
        "temperature": 0.7
    }
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        try:
            async with client.stream(
                "POST",
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Streaming status: {response.status_code}")
                
                if response.status_code == 200:
                    print("Streaming response:")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if data.strip() == "[DONE]":
                                print("\nStream completed")
                                break
                            try:
                                chunk = json.loads(data)
                                if "choices" in chunk and chunk["choices"]:
                                    delta = chunk["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        print(content, end="", flush=True)
                            except json.JSONDecodeError:
                                pass
                    return True
                else:
                    print(f"Error response: {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            print("Streaming request timed out")
            return False
        except Exception as e:
            print(f"Streaming error: {str(e)}")
            return False

async def main():
    """Run all tests"""
    print("Starting Librarian Integration Tests")
    print(f"Testing against: {LIBRARIAN_BASE_URL}")
    print(f"Test timeout: {TEST_TIMEOUT}s")
    print(f"Test models: {TEST_MODELS}")
    print(f"Streaming tests: {'enabled' if ENABLE_STREAMING_TESTS else 'disabled'}")
    print(f"Tool tests: {'enabled' if ENABLE_TOOL_TESTS else 'disabled'}")
    
    tests = [
        ("Health Check", test_health_check()),
        ("Models Endpoint", test_models_endpoint()),
    ]
    
    # Add model-specific tests
    for model in TEST_MODELS:
        tests.append((f"Chat Completion ({model})", test_chat_completion(model)))
        if ENABLE_STREAMING_TESTS:
            tests.append((f"Streaming Completion ({model})", test_streaming_completion(model)))
    
    results = []
    for test_name, test_coro in tests:
        try:
            result = await test_coro
            results.append((test_name, result))
            if result:
                print(f"PASS: {test_name}")
            else:
                print(f"FAIL: {test_name}")
        except Exception as e:
            print(f"ERROR: {test_name} - {str(e)}")
            results.append((test_name, False))
    
    print(f"\nTest Results:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! The Librarian is fully functional.")
    else:
        print("Some tests failed. Check the Letta server connection and configuration.")

if __name__ == "__main__":
    asyncio.run(main())
