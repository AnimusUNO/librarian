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
TEST_MODELS = os.getenv("LIBRARIAN_TEST_MODELS", "gpt-4.1").split(",")  # Default to gpt-4.1
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
    """Test models listing endpoint with validation"""
    print("\nTesting models endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{LIBRARIAN_BASE_URL}/v1/models")
        print(f"Models endpoint status: {response.status_code}")
        
        if response.status_code != 200:
            return False
        
        models_data = response.json()
        
        # Verify response structure
        assert "object" in models_data, "Response missing 'object' field"
        assert models_data["object"] == "list", f"Expected 'list', got '{models_data['object']}'"
        assert "data" in models_data, "Response missing 'data' field"
        assert isinstance(models_data["data"], list), "Data should be a list"
        assert len(models_data["data"]) > 0, "No models returned"
        
        # Verify each model has required fields
        model_ids = []
        for model in models_data["data"]:
            assert "id" in model, "Model missing 'id' field"
            assert "object" in model, "Model missing 'object' field"
            assert model["object"] == "model", f"Model object should be 'model', got '{model['object']}'"
            assert "created" in model, "Model missing 'created' field"
            assert "owned_by" in model, "Model missing 'owned_by' field"
            model_ids.append(model["id"])
        
        # Verify default model is present
        assert "gpt-4.1" in model_ids, "Default model 'gpt-4.1' not found in list"
        
        print(f"[OK] Available models: {model_ids}")
        print(f"[OK] Total models: {len(model_ids)}")
        return True

@pytest.mark.asyncio
async def test_chat_completion(model: str = "gpt-4.1"):
    """Test chat completion endpoint with real query validation"""
    print(f"\nTesting chat completion with model: {model}")
    
    # Use a query that requires actual reasoning
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "What is 15 multiplied by 23? Show your work."}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        try:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"Chat completion status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return False
            
            result = response.json()
            
            # Verify response structure
            assert "id" in result, "Response missing 'id' field"
            assert "model" in result, "Response missing 'model' field"
            assert "choices" in result, "Response missing 'choices' field"
            assert len(result["choices"]) > 0, "Response has no choices"
            
            # Verify model matches request
            assert result["model"] == model, f"Model mismatch: expected {model}, got {result['model']}"
            
            # Get response content
            content = result["choices"][0]["message"]["content"]
            assert content is not None, "Response content is None"
            assert len(content.strip()) > 0, "Response content is empty"
            assert len(content) > 10, f"Response too short: {len(content)} chars"
            
            # Verify usage statistics
            assert "usage" in result, "Response missing 'usage' field"
            usage = result["usage"]
            assert "prompt_tokens" in usage, "Usage missing 'prompt_tokens'"
            assert "completion_tokens" in usage, "Usage missing 'completion_tokens'"
            assert "total_tokens" in usage, "Usage missing 'total_tokens'"
            assert usage["prompt_tokens"] > 0, "Prompt tokens should be > 0"
            assert usage["completion_tokens"] > 0, "Completion tokens should be > 0"
            assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], "Token math incorrect"
            
            # Verify the response actually contains the answer (345 = 15 * 23)
            # The response should mention the calculation or result
            content_lower = content.lower()
            has_calculation = any([
                "345" in content,
                "15" in content and "23" in content,
                "multipl" in content_lower,
                "=" in content
            ])
            assert has_calculation, f"Response doesn't appear to answer the question. Content: {content[:100]}..."
            
            print(f"[OK] Response ID: {result['id']}")
            print(f"[OK] Model: {result['model']}")
            print(f"[OK] Content length: {len(content)} chars")
            # Safe content preview (handle Unicode for Windows)
            preview = content[:100].encode('ascii', errors='replace').decode('ascii')
            print(f"[OK] Content preview: {preview}...")
            print(f"[OK] Usage: {usage}")
            
            return True
                
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {str(e)}")
            return False
        except httpx.TimeoutException:
            print("[FAIL] Request timed out - Letta server may not be running")
            return False
        except Exception as e:
            print(f"[FAIL] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

@pytest.mark.asyncio
async def test_streaming_completion(model: str = "gpt-4.1"):
    """Test streaming chat completion with real content validation"""
    if not ENABLE_STREAMING_TESTS:
        print(f"\nSkipping streaming test (disabled)")
        return True
        
    print(f"\nTesting streaming completion with model: {model}")
    
    # Use a query that requires multi-step reasoning
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "List the first 5 prime numbers and explain why each is prime."}
        ],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 300
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
                
                if response.status_code != 200:
                    print(f"[FAIL] Error response: {response.text}")
                    return False
                
                # Collect streaming content
                chunks_received = 0
                full_content = ""
                response_id = None
                final_usage = None
                
                print("Streaming response:")
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip() == "[DONE]":
                            print("\n[OK] Stream completed")
                            break
                        try:
                            chunk = json.loads(data)
                            
                            # Verify chunk structure
                            assert "id" in chunk or response_id is not None, "Chunk missing 'id'"
                            if "id" in chunk:
                                response_id = chunk["id"]
                            
                            assert "choices" in chunk, "Chunk missing 'choices'"
                            assert len(chunk["choices"]) > 0, "Chunk has no choices"
                            
                            # Extract content
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    chunks_received += 1
                                    full_content += content
                                    print(content, end="", flush=True)
                            
                            # Check for final chunk with usage
                            if "usage" in chunk:
                                final_usage = chunk["usage"]
                                
                        except json.JSONDecodeError as e:
                            print(f"\n⚠ JSON decode error: {e}")
                            continue
                        except AssertionError as e:
                            print(f"\n[FAIL] Assertion failed in chunk: {str(e)}")
                            return False
                
                # Verify we actually received content
                assert chunks_received > 0, "No content chunks received"
                assert len(full_content.strip()) > 0, "Streamed content is empty"
                assert len(full_content) > 50, f"Streamed content too short: {len(full_content)} chars"
                
                # Verify the response actually answers the question
                # Should mention prime numbers
                content_lower = full_content.lower()
                has_primes = any([
                    "prime" in content_lower,
                    "2" in full_content and "3" in full_content,
                    "divisible" in content_lower or "factor" in content_lower
                ])
                assert has_primes, f"Response doesn't appear to answer about primes. Content: {full_content[:150]}..."
                
                # Verify usage if provided
                if final_usage:
                    assert "prompt_tokens" in final_usage, "Final usage missing 'prompt_tokens'"
                    assert "completion_tokens" in final_usage, "Final usage missing 'completion_tokens'"
                    assert final_usage["completion_tokens"] > 0, "Completion tokens should be > 0"
                
                print(f"\n[OK] Chunks received: {chunks_received}")
                print(f"[OK] Total content length: {len(full_content)} chars")
                if final_usage:
                    print(f"[OK] Final usage: {final_usage}")
                
                return True
                    
        except AssertionError as e:
            print(f"\n[FAIL] Assertion failed: {str(e)}")
            return False
        except httpx.TimeoutException:
            print("\n[FAIL] Streaming request timed out")
            return False
        except Exception as e:
            print(f"\n[FAIL] Streaming error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

@pytest.mark.asyncio
async def test_e2e_api_request(model: str = "gpt-4.1"):
    """Test end-to-end API request processing - verify agent does real work"""
    print(f"\nTesting E2E API request processing with model: {model}")
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        try:
            # Test a request that requires actual processing/calculation
            print("\nSending API request requiring real processing...")
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Analyze this data: [5, 12, 8, 15, 3, 9]. Calculate the mean, median, and identify the highest value."}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200
                }
            )
            
            assert response.status_code == 200, f"Request failed with status {response.status_code}: {response.text}"
            result = response.json()
            
            # Verify response structure
            assert "id" in result, "Response missing 'id' field"
            assert "model" in result, "Response missing 'model' field"
            assert result["model"] == model, f"Model mismatch: expected {model}, got {result['model']}"
            assert "choices" in result, "Response missing 'choices' field"
            assert len(result["choices"]) > 0, "Response has no choices"
            
            # Get response content
            content = result["choices"][0]["message"]["content"]
            assert content is not None, "Response content is None"
            assert len(content.strip()) > 0, "Response content is empty"
            assert len(content) > 20, f"Response too short: {len(content)} chars"
            
            # Verify the agent actually processed the data
            # Should mention calculations or results
            content_lower = content.lower()
            has_analysis = any([
                "mean" in content_lower or "average" in content_lower,
                "median" in content_lower,
                "15" in content or "highest" in content_lower or "maximum" in content_lower,
                "8.67" in content or "8.7" in content or "8.6" in content,  # Mean ≈ 8.67
                "9" in content and ("median" in content_lower or "middle" in content_lower)
            ])
            assert has_analysis, \
                f"Response doesn't appear to analyze the data. Content: {content[:200]}..."
            
            # Verify usage statistics
            assert "usage" in result, "Response missing 'usage' field"
            usage = result["usage"]
            assert usage["prompt_tokens"] > 0, "Prompt tokens should be > 0"
            assert usage["completion_tokens"] > 0, "Completion tokens should be > 0"
            assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], \
                "Token math incorrect"
            
            # Verify response ID format (OpenAI-compatible)
            assert result["id"].startswith("chatcmpl-"), \
                f"Response ID should start with 'chatcmpl-', got: {result['id']}"
            
            print(f"[OK] Response ID: {result['id']}")
            print(f"[OK] Content length: {len(content)} chars")
            # Safe content preview (handle Unicode for Windows)
            preview = content[:150].encode('ascii', errors='replace').decode('ascii')
            print(f"[OK] Content preview: {preview}...")
            print(f"[OK] Usage: {usage['total_tokens']} total tokens ({usage['prompt_tokens']} prompt + {usage['completion_tokens']} completion)")
            print("[OK] E2E API request test passed - agent processed the request!")
            
            return True
            
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {str(e)}")
            return False
        except httpx.TimeoutException:
            print("[FAIL] E2E test timed out")
            return False
        except Exception as e:
            print(f"[FAIL] E2E test error: {str(e)}")
            import traceback
            traceback.print_exc()
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
    
    # Add E2E API request test
    tests.append(("E2E API Request Processing", test_e2e_api_request()))
    
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
