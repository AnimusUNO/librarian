#!/usr/bin/env python3
"""
Test script to verify token counting accuracy

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

from src.librarian import TokenCounter

def test_token_counting():
    """Test token counting accuracy"""
    
    token_counter = TokenCounter()
    
    print("Testing Token Counting Accuracy")
    print("=" * 40)
    
    # Test 1: Simple text counting
    text = "Hello, world!"
    tokens = token_counter.count_tokens(text, "gpt-4")
    print(f"Text: '{text}'")
    print(f"Tokens: {tokens}")
    print()
    
    # Test 2: Message counting
    messages = [
        {"role": "user", "content": "What is 2+2?"},
        {"role": "assistant", "content": "2+2 equals 4."},
        {"role": "user", "content": "Thank you!"}
    ]
    
    message_tokens = token_counter.count_messages_tokens(messages, "gpt-4")
    print(f"Messages tokens: {message_tokens}")
    print()
    
    # Test 3: Usage calculation
    response_content = "2+2 equals 4."
    usage = token_counter.calculate_usage(messages, response_content, "gpt-4")
    print(f"Usage calculation:")
    print(f"  Prompt tokens: {usage['prompt_tokens']}")
    print(f"  Completion tokens: {usage['completion_tokens']}")
    print(f"  Total tokens: {usage['total_tokens']}")
    print()
    
    # Test 4: Cost estimation
    cost = token_counter.estimate_cost(usage, "gpt-4")
    print(f"Estimated cost: ${cost:.6f}")
    print()
    
    # Test 5: Model info
    model_info = token_counter.get_model_info("gpt-4")
    print(f"Model info for gpt-4:")
    print(f"  Encoding: {model_info['encoding_name']}")
    print(f"  Vocab size: {model_info['vocab_size']}")
    print(f"  Max tokens: {model_info['max_tokens']}")
    print()
    
    print("Token counting tests completed!")

if __name__ == "__main__":
    test_token_counting()
