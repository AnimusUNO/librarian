#!/usr/bin/env python3
"""
Test suite for TokenCounter

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
from src.librarian.token_counter import TokenCounter


class TestTokenCounter:
    """Test TokenCounter class"""
    
    def test_init(self):
        """Test TokenCounter initialization"""
        counter = TokenCounter()
        assert counter is not None
        assert hasattr(counter, 'encodings')
        assert 'gpt-4' in counter.encodings
    
    def test_count_tokens_basic(self):
        """Test basic token counting"""
        counter = TokenCounter()
        text = "Hello, world!"
        tokens = counter.count_tokens(text, "gpt-4")
        assert tokens > 0
        assert isinstance(tokens, int)
    
    def test_count_tokens_different_models(self):
        """Test token counting for different models"""
        counter = TokenCounter()
        text = "This is a test message"
        
        # Test with different model names
        models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4.1"]
        for model in models:
            tokens = counter.count_tokens(text, model)
            assert tokens > 0
            assert isinstance(tokens, int)
    
    def test_count_tokens_empty_string(self):
        """Test token counting with empty string"""
        counter = TokenCounter()
        tokens = counter.count_tokens("", "gpt-4")
        assert tokens == 0
    
    def test_count_tokens_very_long_string(self):
        """Test token counting with very long string"""
        counter = TokenCounter()
        long_text = "word " * 1000
        tokens = counter.count_tokens(long_text, "gpt-4")
        assert tokens > 0
    
    def test_count_messages_tokens_basic(self):
        """Test counting tokens in messages"""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        tokens = counter.count_messages_tokens(messages, "gpt-4")
        assert tokens > 0
    
    def test_count_messages_tokens_with_system_content(self):
        """Test counting tokens with system content"""
        counter = TokenCounter()
        # Add system message to messages list
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"}
        ]
        tokens = counter.count_messages_tokens(messages, "gpt-4")
        assert tokens > 0
        # Should be more than without system content
        tokens_no_system = counter.count_messages_tokens(
            [{"role": "user", "content": "Hello"}], "gpt-4"
        )
        assert tokens > tokens_no_system
    
    def test_count_messages_tokens_with_name(self):
        """Test counting tokens in messages with name field"""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello", "name": "Alice"}
        ]
        tokens = counter.count_messages_tokens(messages, "gpt-4")
        assert tokens > 0
        # Should be more than without name
        tokens_no_name = counter.count_messages_tokens(
            [{"role": "user", "content": "Hello"}], "gpt-4"
        )
        assert tokens > tokens_no_name
    
    def test_count_messages_tokens_with_tool_calls(self):
        """Test counting tokens in messages with tool calls"""
        counter = TokenCounter()
        messages = [
            {
                "role": "assistant",
                "content": "I'll call a function",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "New York"}'
                        }
                    }
                ]
            }
        ]
        tokens = counter.count_messages_tokens(messages, "gpt-4")
        assert tokens > 0
        # Should be more than without tool calls
        tokens_no_tools = counter.count_messages_tokens(
            [{"role": "assistant", "content": "I'll call a function"}], "gpt-4"
        )
        assert tokens > tokens_no_tools
    
    def test_count_messages_tokens_empty_list(self):
        """Test counting tokens with empty message list"""
        counter = TokenCounter()
        tokens = counter.count_messages_tokens([], "gpt-4")
        # Should return 2 (for assistant's reply overhead)
        assert tokens == 2
    
    def test_count_messages_tokens_multiple_tool_calls(self):
        """Test counting tokens with multiple tool calls"""
        counter = TokenCounter()
        messages = [
            {
                "role": "assistant",
                "content": "I'll call multiple functions",
                "tool_calls": [
                    {
                        "function": {
                            "name": "function1",
                            "arguments": '{"arg": "value1"}'
                        }
                    },
                    {
                        "function": {
                            "name": "function2",
                            "arguments": '{"arg": "value2"}'
                        }
                    }
                ]
            }
        ]
        tokens = counter.count_messages_tokens(messages, "gpt-4")
        assert tokens > 0
    
    def test_calculate_usage_basic(self):
        """Test calculate_usage basic functionality"""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]
        response = "Hi there!"
        usage = counter.calculate_usage(messages, response, "gpt-4")
        
        assert usage is not None
        assert isinstance(usage, dict)
        assert 'prompt_tokens' in usage
        assert 'completion_tokens' in usage
        assert 'total_tokens' in usage
        assert usage['prompt_tokens'] > 0
        assert usage['completion_tokens'] > 0
        assert usage['total_tokens'] == usage['prompt_tokens'] + usage['completion_tokens']
    
    def test_calculate_usage_with_system_content(self):
        """Test calculate_usage with system content"""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]
        response = "Hi there!"
        system_content = "You are a helpful assistant."
        usage = counter.calculate_usage(messages, response, "gpt-4", system_content=system_content)
        
        assert usage['prompt_tokens'] > 0
        assert usage['completion_tokens'] > 0
        # Prompt tokens should include system content
        usage_no_system = counter.calculate_usage(messages, response, "gpt-4")
        assert usage['prompt_tokens'] > usage_no_system['prompt_tokens']
    
    def test_calculate_usage_different_models(self):
        """Test calculate_usage with different models"""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]
        response = "Hi there!"
        
        models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
        for model in models:
            usage = counter.calculate_usage(messages, response, model)
            assert usage['prompt_tokens'] > 0
            assert usage['completion_tokens'] > 0
            assert usage['total_tokens'] > 0
    
    def test_calculate_usage_empty_response(self):
        """Test calculate_usage with empty response"""
        counter = TokenCounter()
        messages = [{"role": "user", "content": "Hello"}]
        response = ""
        usage = counter.calculate_usage(messages, response, "gpt-4")
        
        assert usage['prompt_tokens'] > 0
        assert usage['completion_tokens'] == 0  # Empty response
        assert usage['total_tokens'] == usage['prompt_tokens']
    
    def test_calculate_usage_empty_messages(self):
        """Test calculate_usage with empty messages"""
        counter = TokenCounter()
        messages = []
        response = "Hello"
        usage = counter.calculate_usage(messages, response, "gpt-4")
        
        assert usage['prompt_tokens'] >= 0
        assert usage['completion_tokens'] > 0
        assert usage['total_tokens'] > 0
    
    def test_estimate_cost(self):
        """Test cost estimation"""
        counter = TokenCounter()
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }
        cost = counter.estimate_cost(usage, "gpt-4")
        assert cost > 0
        assert isinstance(cost, float)
    
    def test_estimate_cost_different_models(self):
        """Test cost estimation for different models"""
        counter = TokenCounter()
        usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500
        }
        models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
        for model in models:
            cost = counter.estimate_cost(usage, model)
            assert cost > 0
            assert isinstance(cost, float)
    
    def test_get_model_info(self):
        """Test getting model information"""
        counter = TokenCounter()
        info = counter.get_model_info("gpt-4")
        assert info is not None
        assert isinstance(info, dict)
        assert 'model' in info
        assert 'encoding_name' in info
        assert 'vocab_size' in info
        assert 'max_tokens' in info
        assert info['model'] == "gpt-4"
    
    def test_get_model_info_different_models(self):
        """Test getting model info for different models"""
        counter = TokenCounter()
        models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"]
        for model in models:
            info = counter.get_model_info(model)
            assert info['model'] == model
            assert info['max_tokens'] > 0
    
    def test_get_max_tokens(self):
        """Test getting max tokens for models"""
        counter = TokenCounter()
        max_tokens = counter._get_max_tokens("gpt-4")
        assert max_tokens == 8192
        
        max_tokens = counter._get_max_tokens("gpt-4.1")
        assert max_tokens == 128000
        
        max_tokens = counter._get_max_tokens("unknown-model")
        assert max_tokens == 8192  # Default
    
    def test_truncate_to_max_tokens(self):
        """Test truncating text to max tokens"""
        counter = TokenCounter()
        # Create text that exceeds max tokens
        long_text = "word " * 10000
        truncated = counter.truncate_to_max_tokens(long_text, "gpt-4", max_tokens=100)
        
        # Should be truncated
        tokens = counter.count_tokens(truncated, "gpt-4")
        assert tokens <= 100
    
    def test_truncate_to_max_tokens_short_text(self):
        """Test truncating text that's already short enough"""
        counter = TokenCounter()
        short_text = "Hello world"
        truncated = counter.truncate_to_max_tokens(short_text, "gpt-4", max_tokens=100)
        
        # Should be unchanged
        assert truncated == short_text
    
    def test_truncate_to_max_tokens_default(self):
        """Test truncating with default max_tokens"""
        counter = TokenCounter()
        long_text = "word " * 10000
        truncated = counter.truncate_to_max_tokens(long_text, "gpt-4")
        
        # Should use model's default max_tokens
        tokens = counter.count_tokens(truncated, "gpt-4")
        assert tokens <= counter._get_max_tokens("gpt-4")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

