#!/usr/bin/env python3
"""
Test script for The Librarian OpenAI compatibility

This script demonstrates that The Librarian works with standard OpenAI client libraries.

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

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
import json
import time
import pytest

@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai module not available")
def test_openai_compatibility():
    """Test OpenAI client compatibility with The Librarian"""
    
    # Configure OpenAI client to use The Librarian
    client = openai.OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="any-value"  # Not validated by proxy
    )
    
    print("Testing The Librarian OpenAI Compatibility")
    print("=" * 50)
    
    # Test 1: List models
    print("\n1. Testing /v1/models endpoint...")
    try:
        models = client.models.list()
        print(f"Found {len(models.data)} models:")
        for model in models.data:
            print(f"   - {model.id} ({model.owned_by})")
    except Exception as e:
        print(f"Error listing models: {e}")
        return False
    
    # Test 2: Chat completion with gpt-3.5-turbo (Worker mode)
    print("\n2. Testing chat completion with gpt-3.5-turbo (Worker mode)...")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "What is 2+2?"}
            ],
            temperature=0.7
        )
        print(f"Worker mode response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error with worker mode: {e}")
        return False
    
    # Test 3: Chat completion with gpt-4 (Persona mode)
    print("\n3. Testing chat completion with gpt-4 (Persona mode)...")
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": "Tell me about yourself, Librarian."}
            ],
            temperature=0.8
        )
        print(f"Persona mode response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"Error with persona mode: {e}")
        return False
    
    # Test 4: Streaming response
    print("\n4. Testing streaming response...")
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "user", "content": "Count from 1 to 5"}
            ],
            stream=True
        )
        
        print("Streaming response:")
        for chunk in response:
            if chunk.choices[0].delta.content:
                print(f"   {chunk.choices[0].delta.content}", end="", flush=True)
        print()  # New line after streaming
    except Exception as e:
        print(f"Error with streaming: {e}")
        return False
    
    # Test 5: Error handling
    print("\n5. Testing error handling...")
    try:
        response = client.chat.completions.create(
            model="invalid-model",
            messages=[
                {"role": "user", "content": "This should fail"}
            ]
        )
        print("Expected error but got response")
        return False
    except Exception as e:
        print(f"Correctly handled invalid model: {e}")
    
    print("\n" + "=" * 50)
    print("All tests passed! The Librarian is OpenAI-compatible!")
    return True

if __name__ == "__main__":
    print("Starting The Librarian compatibility test...")
    print("Make sure The Librarian server is running on http://localhost:8000")
    print()
    
    success = test_openai_compatibility()
    
    if success:
        print("\nThe Librarian is ready for OpenAI client integration!")
        print("\nNext steps:")
        print("1. Create the Librarian agent in Letta")
        print("2. Implement actual Letta integration")
        print("3. Add system overlay management")
        print("4. Implement tool synchronization")
    else:
        print("\nSome tests failed. Check the server logs.")
