"""
Security Middleware for The Librarian

Implements IP filtering, API key authentication, and rate limiting.
All features are configurable and opt-in.

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

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, handling proxy headers.
    
    Checks in order:
    1. X-Forwarded-For (first IP if multiple)
    2. X-Real-IP
    3. Direct connection IP
    
    Args:
        request: FastAPI/Starlette request object
        
    Returns:
        Client IP address as string
    """
    # Check X-Forwarded-For header (common in proxy setups)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first one
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip
    
    # Check X-Real-IP header (nginx proxy)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


class IPFilter:
    """IP filtering utility for allow/block lists"""
    
    def __init__(self, allowed_ips: List[str], blocked_ips: List[str]):
        """
        Initialize IP filter.
        
        Args:
            allowed_ips: List of allowed IP addresses (empty = allow all)
            blocked_ips: List of blocked IP addresses
        """
        # Clean and normalize IP lists
        self.allowed_ips: Set[str] = {ip.strip() for ip in allowed_ips if ip.strip()}
        self.blocked_ips: Set[str] = {ip.strip() for ip in blocked_ips if ip.strip()}
        
        logger.info(f"IP Filter initialized: {len(self.allowed_ips)} allowed, {len(self.blocked_ips)} blocked")
    
    def is_allowed(self, ip: str) -> tuple[bool, Optional[str]]:
        """
        Check if IP address is allowed.
        
        Logic:
        - If allowed_ips is non-empty: IP must be in allowed list
        - If blocked_ips is non-empty: IP must not be in blocked list
        - If both are set: allowed list takes precedence
        
        Args:
            ip: IP address to check
            
        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        # Check allow list first (takes precedence)
        if self.allowed_ips:
            if ip not in self.allowed_ips:
                return False, f"IP {ip} not in allowed list"
            # If in allowed list, check block list
            if ip in self.blocked_ips:
                return False, f"IP {ip} is in blocked list"
            return True, None
        
        # No allow list, check block list
        if self.blocked_ips:
            if ip in self.blocked_ips:
                return False, f"IP {ip} is in blocked list"
        
        # No restrictions
        return True, None


class RateLimiter:
    """In-memory rate limiter using sliding window algorithm"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = asyncio.Lock()
        
        # Cleanup interval (clean old entries every 5 minutes)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        logger.info(f"Rate Limiter initialized: {max_requests} requests per {window_seconds} seconds")
    
    async def is_allowed(self, ip: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            ip: IP address making the request
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        async with self.lock:
            current_time = time.time()
            
            # Cleanup old entries periodically
            if current_time - self.last_cleanup > self.cleanup_interval:
                await self._cleanup(current_time)
                self.last_cleanup = current_time
            
            # Get request history for this IP
            ip_requests = self.requests[ip]
            
            # Remove requests outside the window
            window_start = current_time - self.window_seconds
            ip_requests[:] = [req_time for req_time in ip_requests if req_time > window_start]
            
            # Check if limit exceeded
            if len(ip_requests) >= self.max_requests:
                # Calculate retry after (oldest request in window + window - current time)
                if ip_requests:
                    oldest_request = min(ip_requests)
                    retry_after = int(oldest_request + self.window_seconds - current_time) + 1
                    return False, retry_after
                return False, self.window_seconds
            
            # Add current request
            ip_requests.append(current_time)
            
            return True, None
    
    async def _cleanup(self, current_time: float):
        """Remove old entries from request history"""
        window_start = current_time - self.window_seconds
        ips_to_remove = []
        
        for ip, requests in self.requests.items():
            # Remove old requests
            self.requests[ip] = [req_time for req_time in requests if req_time > window_start]
            # Remove IP if no recent requests
            if not self.requests[ip]:
                ips_to_remove.append(ip)
        
        for ip in ips_to_remove:
            del self.requests[ip]
        
        if ips_to_remove:
            logger.debug(f"Rate limiter cleanup: removed {len(ips_to_remove)} inactive IPs")


class APIKeyValidator:
    """API key authentication validator"""
    
    def __init__(self, required: bool, api_key: Optional[str]):
        """
        Initialize API key validator.
        
        Args:
            required: Whether API key is required
            api_key: The expected API key value
        """
        self.required = required
        self.api_key = api_key
        
        if required and not api_key:
            logger.warning("API key authentication is required but no API key is configured")
        
        logger.info(f"API Key Validator initialized: required={required}")
    
    def is_valid(self, auth_header: Optional[str]) -> tuple[bool, Optional[str]]:
        """
        Validate API key from Authorization header.
        
        Args:
            auth_header: Authorization header value (e.g., "Bearer <key>")
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not self.required:
            return True, None
        
        if not self.api_key:
            return False, "API key authentication required but not configured"
        
        if not auth_header:
            return False, "Missing Authorization header"
        
        # Parse "Bearer <key>" format
        parts = auth_header.strip().split(" ", 1)
        if len(parts) != 2:
            return False, "Invalid Authorization header format"
        
        scheme, key = parts
        if scheme.lower() != "bearer":
            return False, "Authorization scheme must be 'Bearer'"
        
        if key != self.api_key:
            return False, "Invalid API key"
        
        return True, None


class SecurityMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for security features"""
    
    def __init__(
        self,
        app,
        enable_ip_filtering: bool = False,
        allowed_ips: List[str] = None,
        blocked_ips: List[str] = None,
        api_key_required: bool = False,
        api_key: Optional[str] = None,
        rate_limit_enabled: bool = False,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 60,
        log_security_events: bool = True
    ):
        """
        Initialize security middleware.
        
        Args:
            app: FastAPI application
            enable_ip_filtering: Enable IP filtering
            allowed_ips: List of allowed IP addresses
            blocked_ips: List of blocked IP addresses
            api_key_required: Require API key authentication
            api_key: Expected API key value
            rate_limit_enabled: Enable rate limiting
            rate_limit_requests: Max requests per window
            rate_limit_window: Time window in seconds
            log_security_events: Log security events
        """
        super().__init__(app)
        
        self.enable_ip_filtering = enable_ip_filtering
        self.log_security_events = log_security_events
        
        # Initialize IP filter if enabled
        if enable_ip_filtering:
            self.ip_filter = IPFilter(
                allowed_ips=allowed_ips or [],
                blocked_ips=blocked_ips or []
            )
        else:
            self.ip_filter = None
        
        # Initialize API key validator
        self.api_key_validator = APIKeyValidator(
            required=api_key_required,
            api_key=api_key
        )
        
        # Initialize rate limiter if enabled
        if rate_limit_enabled:
            self.rate_limiter = RateLimiter(
                max_requests=rate_limit_requests,
                window_seconds=rate_limit_window
            )
        else:
            self.rate_limiter = None
        
        logger.info(f"Security Middleware initialized: "
                   f"IP filtering={enable_ip_filtering}, "
                   f"API key required={api_key_required}, "
                   f"Rate limiting={rate_limit_enabled}")
    
    async def dispatch(self, request: Request, call_next):
        """Process request through security checks"""
        
        # Skip security checks for health and docs endpoints
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        client_ip = get_client_ip(request)
        
        # 1. IP Filtering (first check - fastest rejection)
        if self.enable_ip_filtering and self.ip_filter:
            is_allowed, reason = self.ip_filter.is_allowed(client_ip)
            if not is_allowed:
                if self.log_security_events:
                    logger.warning(f"IP filtering blocked: {client_ip} - {reason}")
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "message": "IP address not allowed",
                            "type": "forbidden_error",
                            "code": "ip_filtered"
                        }
                    }
                )
        
        # 2. API Key Authentication
        if self.api_key_validator.required:
            auth_header = request.headers.get("Authorization")
            is_valid, reason = self.api_key_validator.is_valid(auth_header)
            if not is_valid:
                if self.log_security_events:
                    logger.warning(f"API key authentication failed: {client_ip} - {reason}")
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "message": "Invalid or missing API key",
                            "type": "authentication_error",
                            "code": "invalid_api_key"
                        }
                    }
                )
        
        # 3. Rate Limiting (last check - after auth)
        if self.rate_limiter:
            is_allowed, retry_after = await self.rate_limiter.is_allowed(client_ip)
            if not is_allowed:
                if self.log_security_events:
                    logger.warning(f"Rate limit exceeded: {client_ip} - {retry_after}s retry after")
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "message": "Rate limit exceeded",
                            "type": "rate_limit_error",
                            "code": "rate_limit_exceeded"
                        }
                    }
                )
                if retry_after:
                    response.headers["Retry-After"] = str(retry_after)
                return response
        
        # All checks passed, proceed with request
        return await call_next(request)

