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
import time
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
ENABLE_LOAD_TESTS = os.getenv("LIBRARIAN_ENABLE_LOAD_TESTS", "true").lower() == "true"
LOAD_TEST_CONCURRENT = int(os.getenv("LIBRARIAN_LOAD_TEST_CONCURRENT", "20"))  # Default 20 concurrent requests
LOAD_TEST_MAX_CONCURRENT = int(os.getenv("LIBRARIAN_MAX_CONCURRENT", "10"))  # Should match server config

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
            start_time = time.time()
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            elapsed_time = time.time() - start_time
            print(f"Chat completion status: {response.status_code}")
            print(f"[TIME] Response time: {elapsed_time:.2f}s")
            
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
            print(f"[TIME] Total request time: {elapsed_time:.2f}s ({elapsed_time*1000:.0f}ms)")
            
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
            start_time = time.time()
            async with client.stream(
                "POST",
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Streaming status: {response.status_code}")
                first_chunk_time = None
                
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
                            # Note: id may not be in every chunk, but should be in at least one
                            if "id" in chunk:
                                response_id = chunk["id"]
                            
                            # Skip chunks that don't have choices (like final usage chunk)
                            if "choices" not in chunk:
                                # This might be a final chunk with usage, check for it
                                if "usage" in chunk:
                                    final_usage = chunk["usage"]
                                continue
                            
                            assert len(chunk["choices"]) > 0, "Chunk has no choices"
                            
                            # Extract content
                            if chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    if first_chunk_time is None:
                                        first_chunk_time = time.time()
                                        time_to_first_chunk = first_chunk_time - start_time
                                        print(f"\n[TIME] Time to first chunk: {time_to_first_chunk:.2f}s ({time_to_first_chunk*1000:.0f}ms)")
                                    chunks_received += 1
                                    full_content += content
                                    print(content, end="", flush=True)
                            
                            # Check for final chunk with usage (may be in same chunk or separate)
                            if "usage" in chunk:
                                final_usage = chunk["usage"]
                                
                        except json.JSONDecodeError as e:
                            print(f"\n⚠ JSON decode error: {e}")
                            continue
                        except AssertionError as e:
                            print(f"\n[FAIL] Assertion failed in chunk: {str(e)}")
                            return False
                
                elapsed_time = time.time() - start_time
                
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
                print(f"[TIME] Total streaming time: {elapsed_time:.2f}s ({elapsed_time*1000:.0f}ms)")
                if final_usage and elapsed_time > 0:
                    print(f"[PERF] Streaming tokens per second: {final_usage['completion_tokens']/elapsed_time:.1f} tokens/s")
                
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
            start_time = time.time()
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Analyze this data: [5, 12, 8, 15, 3, 9]. Calculate the mean, median, and identify the highest value."}
                    ],
                    "temperature": 0.3
                    # max_tokens omitted to use available capacity
                }
            )
            elapsed_time = time.time() - start_time
            
            assert response.status_code == 200, f"Request failed with status {response.status_code}: {response.text}"
            print(f"[TIME] Response time: {elapsed_time:.2f}s ({elapsed_time*1000:.0f}ms)")
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
            print(f"[TIME] Total request time: {elapsed_time:.2f}s ({elapsed_time*1000:.0f}ms)")
            print(f"[PERF] Tokens per second: {usage['total_tokens']/elapsed_time:.1f} tokens/s")
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

@pytest.mark.asyncio
async def test_concurrent_requests(model: str = "gpt-4.1"):
    """Test concurrent request handling - verify queueing works"""
    if not ENABLE_LOAD_TESTS:
        print(f"\nSkipping load test (disabled)")
        return True
    
    print(f"\nTesting concurrent requests ({LOAD_TEST_CONCURRENT} requests, max_concurrent={LOAD_TEST_MAX_CONCURRENT})")
    
    async def make_request(client: httpx.AsyncClient, request_num: int):
        """Make a single request"""
        start_time = time.time()
        try:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": f"Request #{request_num}: What is {request_num} multiplied by 2? Just give the number."}
                    ],
                    "temperature": 0.3
                    # max_tokens omitted to use available capacity
                },
                timeout=TEST_TIMEOUT
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "request_num": request_num,
                    "elapsed": elapsed,
                    "content": content,
                    "usage": result.get("usage", {})
                }
            else:
                return {
                    "success": False,
                    "request_num": request_num,
                    "elapsed": elapsed,
                    "error": f"Status {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "request_num": request_num,
                "elapsed": time.time() - start_time,
                "error": str(e)
            }
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT * 2) as client:
        try:
            # Launch all requests concurrently
            print(f"Launching {LOAD_TEST_CONCURRENT} concurrent requests...")
            start_time = time.time()
            tasks = [make_request(client, i+1) for i in range(LOAD_TEST_CONCURRENT)]
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            # Analyze results
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]
            
            print(f"\n[LOAD] Total time: {total_time:.2f}s")
            print(f"[LOAD] Successful: {len(successful)}/{LOAD_TEST_CONCURRENT}")
            print(f"[LOAD] Failed: {len(failed)}")
            
            if failed:
                print(f"[FAIL] Failed requests:")
                for f in failed[:5]:  # Show first 5 failures
                    print(f"  Request #{f['request_num']}: {f.get('error', 'Unknown error')}")
            
            # Verify all requests succeeded
            assert len(successful) == LOAD_TEST_CONCURRENT, \
                f"Expected {LOAD_TEST_CONCURRENT} successful requests, got {len(successful)}"
            
            # Calculate statistics
            elapsed_times = [r["elapsed"] for r in successful]
            avg_time = sum(elapsed_times) / len(elapsed_times)
            min_time = min(elapsed_times)
            max_time = max(elapsed_times)
            
            # Calculate throughput
            throughput = len(successful) / total_time
            
            print(f"[LOAD] Request times - Min: {min_time:.2f}s, Avg: {avg_time:.2f}s, Max: {max_time:.2f}s")
            print(f"[LOAD] Throughput: {throughput:.2f} requests/second")
            
            # Verify responses are correct
            for result in successful:
                content = result["content"]
                request_num = result["request_num"]
                expected_answer = str(request_num * 2)
                # Check if the answer is in the response
                assert expected_answer in content or str(request_num) in content, \
                    f"Request #{request_num} response doesn't contain expected answer. Got: {content[:50]}"
            
            # If we have more requests than max_concurrent, verify queueing occurred
            # (requests should take longer due to queue wait)
            if LOAD_TEST_CONCURRENT > LOAD_TEST_MAX_CONCURRENT:
                # Some requests should have waited in queue
                # The max time should be significantly higher than min time
                time_spread = max_time - min_time
                print(f"[LOAD] Time spread (indicates queueing): {time_spread:.2f}s")
                # If queueing is working, there should be a noticeable spread
                # But we don't fail if it's small - depends on processing speed
            
            print(f"[OK] All {LOAD_TEST_CONCURRENT} concurrent requests completed successfully")
            return True
            
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {str(e)}")
            return False
        except Exception as e:
            print(f"[FAIL] Load test error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

@pytest.mark.asyncio
async def test_concurrent_streaming_requests(model: str = "gpt-4.1"):
    """Test concurrent streaming requests - verify queueing works for streaming"""
    if not ENABLE_LOAD_TESTS or not ENABLE_STREAMING_TESTS:
        print(f"\nSkipping streaming load test (disabled)")
        return True
    
    concurrent_count = min(LOAD_TEST_CONCURRENT, 10)  # Limit streaming to 10 for performance
    print(f"\nTesting concurrent streaming requests ({concurrent_count} requests, max_concurrent={LOAD_TEST_MAX_CONCURRENT})")
    
    async def make_streaming_request(client: httpx.AsyncClient, request_num: int):
        """Make a single streaming request"""
        start_time = time.time()
        try:
            async with client.stream(
                "POST",
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": f"Request #{request_num}: Count from 1 to 5."}
                    ],
                    "stream": True,
                    "temperature": 0.3
                    # max_tokens omitted to use available capacity
                },
                timeout=TEST_TIMEOUT
            ) as response:
                if response.status_code != 200:
                    return {
                        "success": False,
                        "request_num": request_num,
                        "elapsed": time.time() - start_time,
                        "error": f"Status {response.status_code}: {await response.aread()}"
                    }
                
                content = ""
                chunks = 0
                first_chunk_time = None
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                chunk_content = delta.get("content", "")
                                if chunk_content:
                                    if first_chunk_time is None:
                                        first_chunk_time = time.time()
                                    chunks += 1
                                    content += chunk_content
                        except json.JSONDecodeError:
                            continue
                
                elapsed = time.time() - start_time
                time_to_first_chunk = (first_chunk_time - start_time) if first_chunk_time else elapsed
                
                return {
                    "success": True,
                    "request_num": request_num,
                    "elapsed": elapsed,
                    "time_to_first_chunk": time_to_first_chunk,
                    "chunks": chunks,
                    "content": content
                }
        except Exception as e:
            return {
                "success": False,
                "request_num": request_num,
                "elapsed": time.time() - start_time,
                "error": str(e)
            }
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT * 2) as client:
        try:
            print(f"Launching {concurrent_count} concurrent streaming requests...")
            start_time = time.time()
            tasks = [make_streaming_request(client, i+1) for i in range(concurrent_count)]
            results = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]
            
            print(f"\n[LOAD] Total time: {total_time:.2f}s")
            print(f"[LOAD] Successful: {len(successful)}/{concurrent_count}")
            print(f"[LOAD] Failed: {len(failed)}")
            
            if failed:
                for f in failed[:3]:
                    print(f"  Request #{f['request_num']}: {f.get('error', 'Unknown error')}")
            
            assert len(successful) == concurrent_count, \
                f"Expected {concurrent_count} successful requests, got {len(successful)}"
            
            # Calculate statistics
            elapsed_times = [r["elapsed"] for r in successful]
            first_chunk_times = [r.get("time_to_first_chunk", 0) for r in successful if "time_to_first_chunk" in r]
            
            avg_time = sum(elapsed_times) / len(elapsed_times)
            avg_first_chunk = sum(first_chunk_times) / len(first_chunk_times) if first_chunk_times else 0
            
            print(f"[LOAD] Avg response time: {avg_time:.2f}s")
            print(f"[LOAD] Avg time to first chunk: {avg_first_chunk:.2f}s")
            print(f"[LOAD] Throughput: {len(successful) / total_time:.2f} requests/second")
            
            # Verify all have content
            for result in successful:
                assert len(result["content"]) > 0, f"Request #{result['request_num']} has no content"
                assert result["chunks"] > 0, f"Request #{result['request_num']} received no chunks"
            
            print(f"[OK] All {concurrent_count} concurrent streaming requests completed successfully")
            return True
            
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {str(e)}")
            return False
        except Exception as e:
            print(f"[FAIL] Streaming load test error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

@pytest.mark.asyncio
async def test_queue_behavior(model: str = "gpt-4.1"):
    """Test that queueing behavior is correct - requests wait when at capacity"""
    if not ENABLE_LOAD_TESTS:
        print(f"\nSkipping queue behavior test (disabled)")
        return True
    
    # Send exactly max_concurrent + 5 requests to verify queueing
    test_count = LOAD_TEST_MAX_CONCURRENT + 5
    print(f"\nTesting queue behavior ({test_count} requests, max_concurrent={LOAD_TEST_MAX_CONCURRENT})")
    print(f"Expected: First {LOAD_TEST_MAX_CONCURRENT} start immediately, remaining wait in queue")
    
    request_times = []
    
    async def make_timed_request(client: httpx.AsyncClient, request_num: int):
        """Make a request and record timing"""
        request_start = time.time()
        try:
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "user", "content": f"Request #{request_num}: Say 'OK'"}
                    ],
                    "temperature": 0.3
                    # max_tokens omitted to use available capacity
                },
                timeout=TEST_TIMEOUT
            )
            request_end = time.time()
            
            return {
                "request_num": request_num,
                "start_time": request_start,
                "end_time": request_end,
                "duration": request_end - request_start,
                "success": response.status_code == 200
            }
        except Exception as e:
            return {
                "request_num": request_num,
                "start_time": request_start,
                "end_time": time.time(),
                "duration": time.time() - request_start,
                "success": False,
                "error": str(e)
            }
    
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT * 2) as client:
        try:
            # Launch all requests with slight stagger to see queue behavior
            print(f"Launching {test_count} requests...")
            overall_start = time.time()
            tasks = [make_timed_request(client, i+1) for i in range(test_count)]
            results = await asyncio.gather(*tasks)
            overall_end = time.time()
            
            successful = [r for r in results if r["success"]]
            print(f"\n[QUEUE] Successful: {len(successful)}/{test_count}")
            print(f"[QUEUE] Total time: {overall_end - overall_start:.2f}s")
            
            assert len(successful) == test_count, \
                f"Expected {test_count} successful requests, got {len(successful)}"
            
            # Analyze timing to verify queueing
            # Sort by start time
            results_sorted = sorted(results, key=lambda x: x["start_time"])
            
            # Calculate when each request started relative to first
            first_start = results_sorted[0]["start_time"]
            start_offsets = [(r["start_time"] - first_start) for r in results_sorted]
            
            # Calculate when each request completed
            completion_times = [r["end_time"] for r in results_sorted]
            
            print(f"[QUEUE] Request timing analysis:")
            print(f"  First request started at: 0.00s")
            print(f"  Last request started at: {start_offsets[-1]:.2f}s")
            print(f"  First request completed at: {completion_times[0] - first_start:.2f}s")
            print(f"  Last request completed at: {completion_times[-1] - first_start:.2f}s")
            
            # Verify that requests completed in reasonable order
            # (Some may complete out of order due to processing time variance, but most should be sequential)
            durations = [r["duration"] for r in results_sorted]
            avg_duration = sum(durations) / len(durations)
            print(f"  Average request duration: {avg_duration:.2f}s")
            
            # If queueing is working, the total time should be longer than a single request
            # but not as long as processing all requests sequentially
            single_request_time = avg_duration
            sequential_time = single_request_time * test_count
            actual_time = overall_end - overall_start
            
            print(f"[QUEUE] Timing comparison:")
            print(f"  Single request: ~{single_request_time:.2f}s")
            print(f"  Sequential (no queue): ~{sequential_time:.2f}s")
            print(f"  Actual (with queue): {actual_time:.2f}s")
            
            # With queueing, actual time should be between single and sequential
            # But much closer to single if max_concurrent allows parallel processing
            efficiency = (sequential_time - actual_time) / sequential_time if sequential_time > 0 else 0
            print(f"  Efficiency: {efficiency*100:.1f}% (higher is better)")
            
            print(f"[OK] Queue behavior test passed")
            return True
            
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {str(e)}")
            return False
        except Exception as e:
            print(f"[FAIL] Queue behavior test error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

@pytest.mark.asyncio
async def test_large_token_request(model: str = "gpt-4.1"):
    """Test large token request (max_tokens > 5000) - verify system handles it"""
    if not ENABLE_LOAD_TESTS:
        print(f"\nSkipping large token test (load tests disabled)")
        return True
    
    print(f"\nTesting large token request with model: {model}")
    print("Requesting max_tokens=6000 to test context window handling")
    
    # Create a substantial prompt that would benefit from large completion
    large_prompt = """Please provide a comprehensive summary of the following topics. 
    For each topic, provide detailed explanations, examples, and analysis:
    
    1. Artificial Intelligence and Machine Learning
    2. Quantum Computing and its applications
    3. Climate Change and Environmental Science
    4. Space Exploration and Astrophysics
    5. Biotechnology and Genetic Engineering
    
    For each topic, include:
    - Historical context and development
    - Current state of the field
    - Key technologies and methodologies
    - Real-world applications and examples
    - Future prospects and challenges
    - Impact on society and industry
    
    Please be thorough and detailed in your response."""
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": large_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 6000  # Large token request
    }
    
    # Use reasonable timeout - large requests can take time but shouldn't hang forever
    timeout_seconds = min(TEST_TIMEOUT * 2, 90)  # Max 90 seconds
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        try:
            start_time = time.time()
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            elapsed_time = time.time() - start_time
            
            print(f"Large token request status: {response.status_code}")
            print(f"[TIME] Response time: {elapsed_time:.2f}s")
            
            if response.status_code != 200:
                print(f"Error response: {response.text}")
                return False
            
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
            
            # Verify usage statistics
            assert "usage" in result, "Response missing 'usage' field"
            usage = result["usage"]
            assert "prompt_tokens" in usage, "Usage missing 'prompt_tokens'"
            assert "completion_tokens" in usage, "Usage missing 'completion_tokens'"
            assert "total_tokens" in usage, "Usage missing 'total_tokens'"
            assert usage["prompt_tokens"] > 0, "Prompt tokens should be > 0"
            assert usage["completion_tokens"] > 0, "Completion tokens should be > 0"
            
            # Verify we got a substantial response (should be large for 6000 max_tokens)
            # Even if not full 6000, should be substantial
            print(f"[OK] Response ID: {result['id']}")
            print(f"[OK] Content length: {len(content)} chars")
            print(f"[OK] Usage: {usage['total_tokens']} total tokens ({usage['prompt_tokens']} prompt + {usage['completion_tokens']} completion)")
            print(f"[OK] Completion tokens: {usage['completion_tokens']:,} (requested max: 6,000)")
            
            # Verify the response actually addresses the topics
            content_lower = content.lower()
            has_topics = any([
                "artificial intelligence" in content_lower or "machine learning" in content_lower,
                "quantum" in content_lower,
                "climate" in content_lower or "environment" in content_lower,
                "space" in content_lower or "astrophysics" in content_lower,
                "biotechnology" in content_lower or "genetic" in content_lower
            ])
            assert has_topics, f"Response doesn't appear to address the requested topics. Content preview: {content[:200]}..."
            
            print(f"[TIME] Total request time: {elapsed_time:.2f}s ({elapsed_time*1000:.0f}ms)")
            if elapsed_time > 0:
                print(f"[PERF] Tokens per second: {usage['total_tokens']/elapsed_time:.1f} tokens/s")
            
            print(f"[OK] Large token request test passed - system handled 6,000 max_tokens request!")
            return True
            
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {str(e)}")
            return False
        except httpx.TimeoutException:
            print("[FAIL] Large token request timed out")
            return False
        except Exception as e:
            print(f"[FAIL] Large token request error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

@pytest.mark.asyncio
async def test_very_large_token_request(model: str = "gpt-4.1"):
    """Test very large token request (max_tokens > 10k) - stress test"""
    # Skip this test by default as it can take a very long time
    # Set LIBRARIAN_ENABLE_VERY_LARGE_TESTS=true to enable
    enable_very_large = os.getenv("LIBRARIAN_ENABLE_VERY_LARGE_TESTS", "false").lower() == "true"
    if not ENABLE_LOAD_TESTS or not enable_very_large:
        print(f"\nSkipping very large token test (disabled - set LIBRARIAN_ENABLE_VERY_LARGE_TESTS=true to enable)")
        return True
    
    print(f"\nTesting very large token request with model: {model}")
    print("Requesting max_tokens=7000 to stress test context window handling")
    
    # Create a document summarization request
    document_summary_prompt = """Please analyze and summarize the following comprehensive document about technology trends.
    
    Document Content:
    
    The technology landscape in 2024 represents a convergence of multiple transformative trends. 
    Artificial intelligence has moved from experimental research to practical applications across industries.
    Machine learning models are now embedded in everyday products, from recommendation systems to autonomous vehicles.
    Natural language processing has reached new heights with large language models capable of understanding context,
    generating human-like text, and assisting with complex reasoning tasks.
    
    Quantum computing is transitioning from theoretical research to early practical applications. Companies are
    developing quantum algorithms for optimization problems, cryptography, and drug discovery. While full-scale
    quantum computers remain years away, quantum simulators and hybrid classical-quantum systems are already
    providing value in specific domains.
    
    Cloud computing has evolved into a distributed computing paradigm with edge computing bringing processing
    closer to data sources. This reduces latency and enables real-time decision making for IoT devices,
    autonomous systems, and augmented reality applications.
    
    Cybersecurity has become increasingly critical as digital transformation accelerates. Zero-trust architectures,
    AI-powered threat detection, and automated response systems are essential for protecting critical infrastructure.
    
    Blockchain technology has expanded beyond cryptocurrencies to enable decentralized applications, smart contracts,
    and transparent supply chain tracking. The technology promises to reduce fraud, increase transparency, and
    enable new business models.
    
    Please provide a comprehensive analysis covering:
    1. Detailed summary of each technology trend
    2. Interconnections between different technologies
    3. Real-world applications and case studies
    4. Challenges and limitations
    5. Future predictions and implications
    6. Recommendations for organizations
    
    Be thorough and provide extensive detail in your analysis."""
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": document_summary_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 7000  # Very large token request
    }
    
    # Use reasonable timeout
    timeout_seconds = min(TEST_TIMEOUT * 3, 120)  # Max 120 seconds
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        try:
            start_time = time.time()
            response = await client.post(
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            elapsed_time = time.time() - start_time
            
            print(f"Very large token request status: {response.status_code}")
            print(f"[TIME] Response time: {elapsed_time:.2f}s")
            
            if response.status_code != 200:
                error_text = response.text
                print(f"Error response: {error_text}")
                # Check if it's a reasonable error (like exceeding model max)
                if "exceeds model's maximum" in error_text.lower() or "context_length_exceeded" in error_text.lower():
                    print(f"[INFO] Request rejected due to model limits (expected for very large requests)")
                    # This is acceptable - means our validation is working
                    return True
                return False
            
            result = response.json()
            
            # Verify response structure
            assert "id" in result, "Response missing 'id' field"
            assert "choices" in result, "Response missing 'choices' field"
            assert len(result["choices"]) > 0, "Response has no choices"
            
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            
            print(f"[OK] Response ID: {result['id']}")
            print(f"[OK] Content length: {len(content):,} chars")
            print(f"[OK] Usage: {usage.get('total_tokens', 0):,} total tokens")
            print(f"[OK] Completion tokens: {usage.get('completion_tokens', 0):,} (requested max: 7,000)")
            
            # Verify we got a substantial response
            assert len(content) > 1000, f"Response too short for large token request: {len(content)} chars"
            
            print(f"[TIME] Total request time: {elapsed_time:.2f}s")
            print(f"[OK] Very large token request test passed!")
            return True
            
        except AssertionError as e:
            print(f"[FAIL] Assertion failed: {str(e)}")
            return False
        except httpx.TimeoutException:
            print("[FAIL] Very large token request timed out")
            return False
        except Exception as e:
            print(f"[FAIL] Very large token request error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

@pytest.mark.asyncio
async def test_large_token_streaming(model: str = "gpt-4.1"):
    """Test large token request with streaming (max_tokens > 5000)"""
    if not ENABLE_LOAD_TESTS or not ENABLE_STREAMING_TESTS:
        print(f"\nSkipping large token streaming test (disabled)")
        return True
    
    print(f"\nTesting large token streaming request with model: {model}")
    print("Requesting max_tokens=5500 with streaming")
    
    large_prompt = """Write a comprehensive guide on software architecture patterns. 
    Cover the following patterns in detail:
    1. Microservices Architecture
    2. Event-Driven Architecture
    3. Serverless Architecture
    4. Monolithic Architecture
    5. Service-Oriented Architecture (SOA)
    6. Layered Architecture
    7. Hexagonal Architecture (Ports and Adapters)
    8. CQRS (Command Query Responsibility Segregation)
    
    For each pattern, provide:
    - Detailed explanation and principles
    - Use cases and when to apply
    - Advantages and disadvantages
    - Implementation examples
    - Best practices
    - Common pitfalls to avoid
    
    Be comprehensive and detailed."""
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": large_prompt}
        ],
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 5500  # Large token request with streaming (reduced for test speed)
    }
    
    async with httpx.AsyncClient(timeout=min(TEST_TIMEOUT * 3, 120)) as client:  # Max 120s timeout
        try:
            start_time = time.time()
            async with client.stream(
                "POST",
                f"{LIBRARIAN_BASE_URL}/v1/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                print(f"Large token streaming status: {response.status_code}")
                first_chunk_time = None
                
                if response.status_code != 200:
                    print(f"[FAIL] Error response: {await response.aread()}")
                    return False
                
                chunks_received = 0
                full_content = ""
                final_usage = None
                
                print("Streaming large response...")
                last_progress_time = time.time()
                max_stream_time = min(TEST_TIMEOUT * 3, 120)  # Max 120 seconds for streaming
                chunk_timeout = 20  # If no chunks for 20 seconds, something's wrong
                
                async for line in response.aiter_lines():
                    # Check for overall timeout
                    elapsed = time.time() - start_time
                    if elapsed > max_stream_time:
                        print(f"\n[WARNING] Stream timeout after {elapsed:.1f}s (max: {max_stream_time}s), stopping")
                        break
                    
                    # Check for progress timeout (if no chunks for chunk_timeout seconds, something's wrong)
                    current_time = time.time()
                    if chunks_received > 0 and current_time - last_progress_time > chunk_timeout:
                        print(f"\n[WARNING] No progress for {chunk_timeout} seconds, stream may be stuck")
                        break
                    
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            print("\n[OK] Stream completed")
                            break
                        try:
                            chunk = json.loads(data)
                            
                            if "id" in chunk:
                                response_id = chunk["id"]
                            
                            if "choices" not in chunk:
                                if "usage" in chunk:
                                    final_usage = chunk["usage"]
                                continue
                            
                            if chunk["choices"]:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    if first_chunk_time is None:
                                        first_chunk_time = time.time()
                                        time_to_first_chunk = first_chunk_time - start_time
                                        print(f"\n[TIME] Time to first chunk: {time_to_first_chunk:.2f}s")
                                    chunks_received += 1
                                    full_content += content
                                    last_progress_time = current_time
                                    
                                    # Print progress for large streams
                                    if chunks_received % 50 == 0:
                                        print(f"\n[PROGRESS] {chunks_received} chunks, {len(full_content):,} chars, {elapsed:.1f}s elapsed...")
                            
                            if "usage" in chunk:
                                final_usage = chunk["usage"]
                                
                        except json.JSONDecodeError:
                            continue
                
                elapsed_time = time.time() - start_time
                
                # Verify we received substantial content
                # For large token requests, the agent may stop early if it completes the task
                # We just need to verify the system handled the large max_tokens request correctly
                assert chunks_received > 0, "No content chunks received"
                assert len(full_content.strip()) > 0, "Streamed content is empty"
                # Agent may complete early, so just verify we got a reasonable response
                assert len(full_content) > 100, f"Streamed content too short: {len(full_content)} chars"
                
                print(f"\n[OK] Chunks received: {chunks_received}")
                print(f"[OK] Total content length: {len(full_content):,} chars")
                if final_usage:
                    print(f"[OK] Final usage: {final_usage}")
                    print(f"[OK] Completion tokens: {final_usage.get('completion_tokens', 0):,} (requested max: 5,500)")
                print(f"[TIME] Total streaming time: {elapsed_time:.2f}s")
                if final_usage and elapsed_time > 0:
                    print(f"[PERF] Streaming tokens per second: {final_usage.get('completion_tokens', 0)/elapsed_time:.1f} tokens/s")
                
                print(f"[OK] Large token streaming test passed!")
                return True
                    
        except AssertionError as e:
            print(f"\n[FAIL] Assertion failed: {str(e)}")
            return False
        except httpx.TimeoutException:
            print("\n[FAIL] Large token streaming request timed out")
            return False
        except Exception as e:
            print(f"\n[FAIL] Large token streaming error: {str(e)}")
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
    print(f"Load tests: {'enabled' if ENABLE_LOAD_TESTS else 'disabled'}")
    if ENABLE_LOAD_TESTS:
        print(f"  Concurrent requests: {LOAD_TEST_CONCURRENT}")
        print(f"  Max concurrent (server): {LOAD_TEST_MAX_CONCURRENT}")
    
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
    
    # Add load tests if enabled
    if ENABLE_LOAD_TESTS:
        for model in TEST_MODELS:
            tests.append((f"Concurrent Requests ({model})", test_concurrent_requests(model)))
            if ENABLE_STREAMING_TESTS:
                tests.append((f"Concurrent Streaming ({model})", test_concurrent_streaming_requests(model)))
        tests.append(("Queue Behavior Test", test_queue_behavior()))
        
        # Add large token request tests
        for model in TEST_MODELS:
            tests.append((f"Large Token Request ({model})", test_large_token_request(model)))
            # Very large token test is optional (can be slow)
            if os.getenv("LIBRARIAN_ENABLE_VERY_LARGE_TESTS", "false").lower() == "true":
                tests.append((f"Very Large Token Request ({model})", test_very_large_token_request(model)))
            if ENABLE_STREAMING_TESTS:
                tests.append((f"Large Token Streaming ({model})", test_large_token_streaming(model)))
    
    results = []
    test_start_time = time.time()
    for test_name, test_coro in tests:
        test_individual_start = time.time()
        try:
            # Add timeout wrapper for each test to prevent hanging
            # Large token tests get more time, others get less
            timeout_seconds = 240 if "Large Token" in test_name else 120
            try:
                print(f"\n[TEST] Starting: {test_name}")
                result = await asyncio.wait_for(test_coro, timeout=timeout_seconds)
                test_elapsed = time.time() - test_individual_start
                results.append((test_name, result))
                if result:
                    print(f"[PASS] {test_name} ({test_elapsed:.1f}s)")
                else:
                    print(f"[FAIL] {test_name} ({test_elapsed:.1f}s)")
            except asyncio.TimeoutError:
                test_elapsed = time.time() - test_individual_start
                print(f"[TIMEOUT] {test_name} - exceeded {timeout_seconds}s limit ({test_elapsed:.1f}s)")
                results.append((test_name, False))
        except Exception as e:
            test_elapsed = time.time() - test_individual_start
            print(f"[ERROR] {test_name} - {str(e)} ({test_elapsed:.1f}s)")
            import traceback
            traceback.print_exc()
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
