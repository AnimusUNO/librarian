"""
Configuration Management for The Librarian

Centralized configuration loading and validation using Pydantic.

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

import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


def _getenv_bool(key: str, default: bool = False) -> bool:
    """Get boolean from environment variable"""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _getenv_int(key: str, default: int) -> int:
    """Get integer from environment variable"""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid integer value for {key}: {value}, using default {default}")
        return default


def _getenv_list(key: str, default: List[str] = None) -> List[str]:
    """Get list from comma-separated environment variable"""
    if default is None:
        default = []
    value = os.getenv(key)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


class Config(BaseModel):
    """Centralized configuration for The Librarian"""
    
    # Server Configuration
    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    enable_docs: bool = Field(default=False, description="Enable API documentation")
    title: str = Field(default="The Librarian", description="Application title")
    description: str = Field(default="OpenAI-Compatible Letta Proxy", description="Application description")
    version: str = Field(default="0.1.0", description="Application version")
    
    # Letta Configuration
    letta_base_url: str = Field(default="http://localhost:8283", description="Letta server base URL")
    letta_api_key: Optional[str] = Field(default=None, description="Letta API key")
    letta_timeout: int = Field(default=30, description="Letta client timeout (seconds)")
    
    # Security Configuration
    enable_ip_filtering: bool = Field(default=False, description="Enable IP filtering")
    allowed_ips: List[str] = Field(default_factory=list, description="Allowed IP addresses")
    blocked_ips: List[str] = Field(default_factory=list, description="Blocked IP addresses")
    api_key_required: bool = Field(default=False, description="Require API key authentication")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=False, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Max requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window (seconds)")
    
    # Performance Configuration
    max_request_size: int = Field(default=10485760, description="Max request size (bytes)")
    request_timeout: int = Field(default=300, description="Request timeout (seconds)")
    keep_alive_timeout: int = Field(default=5, description="Keep-alive timeout (seconds)")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    log_security_events: bool = Field(default=True, description="Log security events")
    
    # Load Management Configuration (used by LoadManager)
    max_concurrent: int = Field(default=10, description="Max concurrent requests")
    duplication_threshold: int = Field(default=8, description="Queue threshold for auto-duplication")
    queue_timeout: int = Field(default=300, description="Queue timeout (seconds)")
    cleanup_interval: int = Field(default=60, description="Cleanup interval (seconds)")
    enable_auto_duplication: bool = Field(default=True, description="Enable auto-duplication")
    max_clones_per_agent: int = Field(default=3, description="Max clones per agent")
    
    # Agent Configuration (used by ModelRegistry)
    librarian_agent: str = Field(default="librarian", description="Default Librarian agent ID")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        """Validate port is in valid range"""
        if not (1 <= v <= 65535):
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v
    
    @field_validator('letta_timeout', 'request_timeout', 'queue_timeout', 'keep_alive_timeout')
    @classmethod
    def validate_timeout(cls, v):
        """Validate timeout is positive"""
        if v < 1:
            raise ValueError(f"Timeout must be positive, got {v}")
        return v
    
    @field_validator('rate_limit_requests', 'max_concurrent', 'max_clones_per_agent')
    @classmethod
    def validate_positive_int(cls, v):
        """Validate positive integer"""
        if v < 1:
            raise ValueError(f"Value must be positive, got {v}")
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @classmethod
    def load(cls) -> "Config":
        """
        Load configuration from environment variables.
        
        Loads from:
        1. Environment variables (highest priority)
        2. .env file (via dotenv)
        
        Returns:
            Config instance with loaded values
        """
        from dotenv import load_dotenv
        load_dotenv()
        
        return cls(
            # Server Configuration
            host=os.getenv("LIBRARIAN_HOST", "127.0.0.1"),
            port=_getenv_int("LIBRARIAN_PORT", 8000),
            debug=_getenv_bool("LIBRARIAN_DEBUG", False),
            enable_docs=_getenv_bool("LIBRARIAN_ENABLE_DOCS", False),
            title=os.getenv("LIBRARIAN_TITLE", "The Librarian"),
            description=os.getenv("LIBRARIAN_DESCRIPTION", "OpenAI-Compatible Letta Proxy"),
            version=os.getenv("LIBRARIAN_VERSION", "0.1.0"),
            
            # Letta Configuration
            letta_base_url=os.getenv("LETTA_BASE_URL", "http://localhost:8283"),
            letta_api_key=os.getenv("LETTA_API_KEY"),
            letta_timeout=_getenv_int("LETTA_TIMEOUT", 30),
            
            # Security Configuration
            enable_ip_filtering=_getenv_bool("LIBRARIAN_ENABLE_IP_FILTERING", False),
            allowed_ips=_getenv_list("LIBRARIAN_ALLOWED_IPS", []),
            blocked_ips=_getenv_list("LIBRARIAN_BLOCKED_IPS", []),
            api_key_required=_getenv_bool("LIBRARIAN_API_KEY_REQUIRED", False),
            api_key=os.getenv("LIBRARIAN_API_KEY"),
            
            # Rate Limiting Configuration
            rate_limit_enabled=_getenv_bool("LIBRARIAN_RATE_LIMIT_ENABLED", False),
            rate_limit_requests=_getenv_int("LIBRARIAN_RATE_LIMIT_REQUESTS", 100),
            rate_limit_window=_getenv_int("LIBRARIAN_RATE_LIMIT_WINDOW", 60),
            
            # Performance Configuration
            max_request_size=_getenv_int("LIBRARIAN_MAX_REQUEST_SIZE", 10485760),
            request_timeout=_getenv_int("LIBRARIAN_REQUEST_TIMEOUT", 300),
            keep_alive_timeout=_getenv_int("LIBRARIAN_KEEP_ALIVE_TIMEOUT", 5),
            
            # Logging Configuration
            log_level=os.getenv("LIBRARIAN_LOG_LEVEL", "INFO").upper(),
            log_format=os.getenv(
                "LIBRARIAN_LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            log_security_events=_getenv_bool("LIBRARIAN_LOG_SECURITY_EVENTS", True),
            
            # Load Management Configuration
            max_concurrent=_getenv_int("LIBRARIAN_MAX_CONCURRENT", 10),
            duplication_threshold=_getenv_int("LIBRARIAN_DUPLICATION_THRESHOLD", 8),
            queue_timeout=_getenv_int("LIBRARIAN_QUEUE_TIMEOUT", 300),
            cleanup_interval=_getenv_int("LIBRARIAN_CLEANUP_INTERVAL", 60),
            enable_auto_duplication=_getenv_bool("LIBRARIAN_ENABLE_AUTO_DUPLICATION", True),
            max_clones_per_agent=_getenv_int("LIBRARIAN_MAX_CLONES_PER_AGENT", 3),
            
            # Agent Configuration
            librarian_agent=os.getenv("LIBRARIAN_AGENT", "librarian"),
        )
    
    def validate_config(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Additional validation beyond Pydantic validators
        if self.api_key_required and not self.api_key:
            logger.warning("API key authentication is required but no API key is configured")
        
        if self.enable_ip_filtering and not self.allowed_ips and not self.blocked_ips:
            logger.warning("IP filtering is enabled but no allowed or blocked IPs configured")
        
        if self.rate_limit_enabled and self.rate_limit_requests < 1:
            raise ValueError(f"Rate limit requests must be positive, got {self.rate_limit_requests}")
        
        logger.info(f"Configuration validated successfully")
    
    def log_summary(self) -> None:
        """Log configuration summary (without sensitive values)"""
        logger.info(f"Configuration loaded: host={self.host}, port={self.port}, debug={self.debug}")
        logger.info(f"Letta config: base_url={self.letta_base_url}, timeout={self.letta_timeout}")
        logger.info(f"Security: ip_filtering={self.enable_ip_filtering}, api_key_required={self.api_key_required}")
        logger.info(f"Rate limiting: enabled={self.rate_limit_enabled}, requests={self.rate_limit_requests}/window={self.rate_limit_window}")

