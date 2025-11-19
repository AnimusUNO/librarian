"""
Token Counter for The Librarian

Provides accurate token counting for OpenAI-compatible usage statistics.
"""

import tiktoken
from typing import Dict, List, Optional


class TokenCounter:
    """Handles token counting for different OpenAI models"""
    
    def __init__(self):
        # Model-specific encodings
        self.encodings = {
            "gpt-3.5-turbo": tiktoken.encoding_for_model("gpt-3.5-turbo"),
            "gpt-4": tiktoken.encoding_for_model("gpt-4"),
            "gpt-4.1": tiktoken.encoding_for_model("gpt-4"),  # gpt-4.1 uses gpt-4 encoding
            "gpt-4-turbo": tiktoken.encoding_for_model("gpt-4"),
            "gpt-4o": tiktoken.encoding_for_model("gpt-4o"),
            "gpt-4o-mini": tiktoken.encoding_for_model("gpt-4o-mini"),
        }
    
    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Count tokens in text for a specific model"""
        encoding = self.encodings.get(model, self.encodings["gpt-4"])
        return len(encoding.encode(text))
    
    def count_messages_tokens(self, messages: List[Dict[str, str]], model: str = "gpt-4") -> int:
        """Count tokens in a list of messages"""
        encoding = self.encodings.get(model, self.encodings["gpt-4"])
        
        total_tokens = 0
        for message in messages:
            # Count tokens for each message
            message_tokens = 4  # Every message follows <|start|>{role/name}\n{content}<|end|>\n
            message_tokens += len(encoding.encode(message.get("role", "")))
            message_tokens += len(encoding.encode(message.get("content", "")))
            
            # Add name tokens if present
            if "name" in message:
                message_tokens += len(encoding.encode(message["name"]))
            
            # Add tool call tokens if present
            if "tool_calls" in message:
                for tool_call in message["tool_calls"]:
                    message_tokens += len(encoding.encode(tool_call.get("function", {}).get("name", "")))
                    message_tokens += len(encoding.encode(tool_call.get("function", {}).get("arguments", "")))
            
            total_tokens += message_tokens
        
        # Add 2 tokens for the assistant's reply
        total_tokens += 2
        
        return total_tokens
    
    def calculate_usage(self, messages: List[Dict[str, str]], response_content: str, model: str = "gpt-4") -> Dict[str, int]:
        """Calculate usage statistics for a request/response pair"""
        prompt_tokens = self.count_messages_tokens(messages, model)
        completion_tokens = self.count_tokens(response_content, model)
        
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }
    
    def estimate_cost(self, usage: Dict[str, int], model: str = "gpt-4") -> float:
        """Estimate cost based on usage (approximate pricing)"""
        # Approximate pricing per 1K tokens (as of 2024)
        pricing = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4.1": {"input": 0.01, "output": 0.03},  # Similar to gpt-4-turbo
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        }
        
        model_pricing = pricing.get(model, pricing["gpt-4"])
        
        input_cost = (usage["prompt_tokens"] / 1000) * model_pricing["input"]
        output_cost = (usage["completion_tokens"] / 1000) * model_pricing["output"]
        
        return input_cost + output_cost
    
    def get_model_info(self, model: str) -> Dict[str, any]:
        """Get information about a model's tokenizer"""
        encoding = self.encodings.get(model, self.encodings["gpt-4"])
        
        return {
            "model": model,
            "encoding_name": encoding.name,
            "vocab_size": encoding.n_vocab,
            "max_tokens": self._get_max_tokens(model)
        }
    
    def _get_max_tokens(self, model: str) -> int:
        """Get maximum tokens for a model"""
        max_tokens = {
            "gpt-3.5-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4.1": 128000,  # gpt-4.1 has large context window
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
        }
        return max_tokens.get(model, 8192)
    
    def truncate_to_max_tokens(self, text: str, model: str, max_tokens: Optional[int] = None) -> str:
        """Truncate text to fit within token limit"""
        if max_tokens is None:
            max_tokens = self._get_max_tokens(model)
        
        encoding = self.encodings.get(model, self.encodings["gpt-4"])
        tokens = encoding.encode(text)
        
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode
        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
