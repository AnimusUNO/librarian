#!/usr/bin/env python3
"""
Test suite for MessageTranslator

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
from src.librarian.message_translator import MessageTranslator


class TestMessageTranslator:
    """Test MessageTranslator class"""
    
    def test_init(self):
        """Test MessageTranslator initialization"""
        translator = MessageTranslator()
        assert translator is not None
    
    def test_translate_messages_basic(self):
        """Test basic message translation"""
        translator = MessageTranslator()
        openai_messages = [
            {"role": "user", "content": "Hello"}
        ]
        messages, system_content = translator.translate_messages(openai_messages)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"][0]["text"] == "Hello"
        assert system_content is None
    
    def test_translate_messages_multiple(self):
        """Test translating multiple messages"""
        translator = MessageTranslator()
        openai_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        messages, system_content = translator.translate_messages(openai_messages)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
    
    def test_translate_messages_with_name(self):
        """Test translating messages with name field"""
        translator = MessageTranslator()
        openai_messages = [
            {"role": "user", "content": "Hello", "name": "Alice"}
        ]
        messages, system_content = translator.translate_messages(openai_messages)
        assert len(messages) == 1
        # Name field is not currently preserved in translation
        assert messages[0]["role"] == "user"
    
    def test_translate_messages_with_tool_calls(self):
        """Test translating messages with tool calls"""
        translator = MessageTranslator()
        openai_messages = [
            {
                "role": "assistant",
                "content": "I'll call a function",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location": "NYC"}'
                        }
                    }
                ]
            }
        ]
        messages, system_content = translator.translate_messages(openai_messages)
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        # Tool calls are not currently preserved in translation
    
    def test_create_mode_selection_instruction_worker(self):
        """Test creating mode selection instruction for worker mode"""
        translator = MessageTranslator()
        instruction = translator.create_mode_selection_instruction("worker")
        assert "worker" in instruction.lower() or "procedural" in instruction.lower()
    
    def test_create_mode_selection_instruction_persona(self):
        """Test creating mode selection instruction for persona mode"""
        translator = MessageTranslator()
        instruction = translator.create_mode_selection_instruction("persona")
        assert "persona" in instruction.lower() or "expressive" in instruction.lower()
    
    def test_create_mode_selection_instruction_auto(self):
        """Test creating mode selection instruction for auto mode"""
        translator = MessageTranslator()
        instruction = translator.create_mode_selection_instruction("auto")
        assert instruction is not None
        assert len(instruction) > 0
    
    def test_translate_messages_empty_list(self):
        """Test translating empty message list"""
        translator = MessageTranslator()
        messages, system_content = translator.translate_messages([])
        assert len(messages) == 0
        assert system_content is None
    
    def test_translate_messages_system_role(self):
        """Test translating system role messages"""
        translator = MessageTranslator()
        openai_messages = [
            {"role": "system", "content": "You are a helpful assistant"}
        ]
        messages, system_content = translator.translate_messages(openai_messages)
        assert len(messages) == 0  # System messages are extracted, not included in messages
        assert system_content == "You are a helpful assistant"
    
    def test_translate_messages_tool_role(self):
        """Test translating tool role messages"""
        translator = MessageTranslator()
        openai_messages = [
            {"role": "tool", "content": "Tool result", "tool_call_id": "call_123"}
        ]
        messages, system_content = translator.translate_messages(openai_messages)
        assert len(messages) == 1
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "call_123"
    
    def test_extract_system_messages(self):
        """Test extracting system messages"""
        translator = MessageTranslator()
        openai_messages = [
            {"role": "system", "content": "System 1"},
            {"role": "user", "content": "Hello"},
            {"role": "system", "content": "System 2"}
        ]
        system_messages = translator.extract_system_messages(openai_messages)
        assert len(system_messages) == 2
        assert "System 1" in system_messages
        assert "System 2" in system_messages
    
    def test_has_system_messages(self):
        """Test checking for system messages"""
        translator = MessageTranslator()
        assert translator.has_system_messages([{"role": "system", "content": "Test"}]) is True
        assert translator.has_system_messages([{"role": "user", "content": "Test"}]) is False
    
    def test_validate_messages(self):
        """Test message validation"""
        translator = MessageTranslator()
        assert translator.validate_messages([{"role": "user", "content": "Hello"}]) is True
        assert translator.validate_messages([]) is False
        assert translator.validate_messages([{"role": "invalid", "content": "Hello"}]) is False
        assert translator.validate_messages([{"role": "user"}]) is False  # Missing content
    
    def test_validate_messages_not_dict(self):
        """Test message validation with non-dict items"""
        translator = MessageTranslator()
        assert translator.validate_messages(["not a dict"]) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

