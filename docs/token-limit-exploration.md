# Token Limit Exploration & Design

**License**: [CC-BY-SA-4.0](../LICENSE-DOCS)

## Overview

This document explores the current token limit logic and designs a system that:
1. **Eliminates static hardcoded token limits** - uses Letta API as source of truth
2. **Always provides users the option to maximize tokens** - calculates optimal max_tokens when not specified
3. **Respects model capabilities** - uses Letta's context window information dynamically

## Fact-Checking Summary

### ✅ Verified Against Codebase
- API endpoint exists: `GET /agents/{id}/context` (docs/letta-api-reference.md:78)
- SDK method exists: `letta_client.agents.context.retrieve()` (main.py:849)
- Response is Pydantic model with `.model_dump()` method
- Code uses field names: `context_window_size_current` and `context_window_size_max` (main.py:853-854)
- Default values: `.get('field', 0)` with default 0
- AgentConfigManager sets max_tokens via `LlmConfig` (agent_config_manager.py:93-103)
- Formula logic: `available_tokens = max_context_window - current_tokens` (main.py:859)

### ⚠️ Needs Live API Verification
- **Field Names**: Assumed `context_window_size_current` and `context_window_size_max` - verify actual names
- **Field Types**: Assumed integers - verify actual types
- **Response Structure**: Assumed flat dict - verify full structure
- **Error Cases**: Verify behavior when API unavailable or fields missing

### 🔧 Verification Tool
Run `test_context_api.py` against a live Letta server to verify:
```bash
python test_context_api.py
```

---

## Current State Analysis

### 1. Static Token Limits (TO BE REMOVED)

**Location**: `src/librarian/token_counter.py`

```python
def _get_max_tokens(self, model: str) -> int:
    """Get maximum tokens for a model"""
    max_tokens = {
        "gpt-3.5-turbo": 4096,
        "gpt-4": 8192,
        "gpt-4.1": 128000,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
    }
    return max_tokens.get(model, 8192)
```

**Used in**:
- `get_model_info()` - returns max_tokens in model info
- `truncate_to_max_tokens()` - uses as default when max_tokens not provided

**Problem**: These are hardcoded and may not match actual Letta agent configuration or model capabilities.

---

### 2. Dynamic Token Limits from Letta API (CURRENT SOURCE OF TRUTH)

**Location**: `main.py` - `check_token_capacity()`

```python
# Get current context from Letta
context = await letta_client.agents.context.retrieve(agent_id=agent_id)
context_dict = context.model_dump()

# Get current usage and max window size (model's absolute maximum)
current_tokens = context_dict.get('context_window_size_current', 0)
max_context_window = context_dict.get('context_window_size_max', 0)  # Model's absolute max

capacity_info = {
    'max_tokens': max_context_window,
    'current_tokens': current_tokens,
    'available_tokens': max_context_window - current_tokens,
    'request_tokens': request_tokens
}
```

**Key Data Points from Letta API**:
- `context_window_size_current` - Current token usage in agent's context (⚠️ **VERIFY FIELD NAME**)
- `context_window_size_max` - Maximum context window size for the model/agent (⚠️ **VERIFY FIELD NAME**)

**This is the authoritative source** - it reflects the actual agent configuration and model capabilities.

**⚠️ VERIFICATION NEEDED**: Field names `context_window_size_current` and `context_window_size_max` are assumed based on code usage. Actual field names should be verified by running `test_context_api.py` against a live Letta server.

---

### 3. Token Limit Flow Through System

#### Request Flow:
1. **User Request** → `ChatCompletionRequest.max_tokens` (optional)
2. **RequestProcessor** → Validates capacity via `check_token_capacity()`
3. **AgentConfigManager** → Sets `max_tokens` on agent's `LlmConfig` via `temporary_config()`
4. **Letta API** → Uses the configured `max_tokens` for generation

#### Current Validation Logic:
```python
# Only error if requested_max_tokens exceeds the model's absolute maximum capability
if requested_max_tokens is not None:
    if requested_max_tokens > max_context_window:
        error_msg = f"Requested max_tokens ({requested_max_tokens:,}) exceeds model's maximum capability ({max_context_window:,} tokens)."
        return False, error_msg, capacity_info
```

**Current Behavior**:
- If `max_tokens` is provided and exceeds `max_context_window` → **ERROR**
- If `max_tokens` is provided and is valid → **USE IT**
- If `max_tokens` is `None` → **PASSED TO LETTA AS-IS** (Letta uses its own default)

---

### 4. Where Static Limits Are Currently Used

#### A. TokenCounter.get_model_info()
```python
def get_model_info(self, model: str) -> Dict[str, any]:
    return {
        "model": model,
        "encoding_name": encoding.name,
        "vocab_size": encoding.n_vocab,
        "max_tokens": self._get_max_tokens(model)  # ← STATIC
    }
```

#### B. TokenCounter.truncate_to_max_tokens()
```python
def truncate_to_max_tokens(self, text: str, model: str, max_tokens: Optional[int] = None) -> str:
    if max_tokens is None:
        max_tokens = self._get_max_tokens(model)  # ← STATIC DEFAULT
    # ... truncation logic
```

**Note**: `truncate_to_max_tokens()` may not be used in production flow - needs verification.

---

## Design Goals

### Goal 1: Eliminate Static Limits
- Remove `_get_max_tokens()` hardcoded values
- Always query Letta API for actual limits
- Cache results appropriately to avoid excessive API calls

### Goal 2: Always Provide Maximum Token Option
When `max_tokens` is `None` in user request:
- Calculate optimal `max_tokens` based on available capacity
- Formula: `optimal_max_tokens = available_tokens - safety_margin`
- Safety margin accounts for prompt tokens and overhead

### Goal 3: Respect User Intent
- If user provides `max_tokens` → use it (if valid)
- If user provides `max_tokens=None` → calculate optimal maximum
- Always validate against Letta's actual limits

---

## Proposed Architecture

### 1. Token Limit Service

Create a new service or extend existing functionality to:

```python
class TokenLimitService:
    """Manages token limits using Letta API as source of truth"""
    
    async def get_agent_token_limits(self, agent_id: str) -> Dict[str, int]:
        """
        Get token limits for an agent from Letta API.
        
        Returns:
            {
                'max_context_window': int,  # Model's absolute maximum
                'current_tokens': int,       # Current usage
                'available_tokens': int,     # Available capacity
            }
        """
        context = await letta_client.agents.context.retrieve(agent_id=agent_id)
        context_dict = context.model_dump()
        
        max_context_window = context_dict.get('context_window_size_max', 0)
        current_tokens = context_dict.get('context_window_size_current', 0)
        available_tokens = max_context_window - current_tokens
        
        return {
            'max_context_window': max_context_window,
            'current_tokens': current_tokens,
            'available_tokens': available_tokens
        }
    
    async def calculate_optimal_max_tokens(
        self,
        agent_id: str,
        request_tokens: int,
        safety_margin: int = 100
    ) -> int:
        """
        Calculate optimal max_tokens when user doesn't specify.
        
        Formula:
            available = max_context_window - current_tokens
            optimal = available - request_tokens - safety_margin
        
        ⚠️ **FORMULA VERIFICATION**: This formula assumes:
        - `request_tokens` is the prompt size (already counted in current_tokens after request)
        - We want to reserve space for the completion
        - Safety margin accounts for overhead
        
        **Alternative Formula Consideration**:
        - If `request_tokens` is NOT yet in `current_tokens`, then:
          `optimal = available - request_tokens - safety_margin` ✅ (current formula)
        - If `request_tokens` IS already in `current_tokens`, then:
          `optimal = available - safety_margin` (request already counted)
        
        **Current Implementation**: `request_tokens` is estimated BEFORE the request is sent,
        so it's NOT yet in `current_tokens`. Therefore current formula is correct.
        
        Args:
            agent_id: Letta agent ID
            request_tokens: Estimated tokens for the prompt (NOT yet in current_tokens)
            safety_margin: Safety buffer (default: 100 tokens)
        
        Returns:
            Optimal max_tokens value (never exceeds max_context_window)
        """
        limits = await self.get_agent_token_limits(agent_id)
        available = limits['available_tokens']
        
        # Calculate optimal: available - request - safety margin
        # Note: request_tokens is NOT yet in current_tokens, so we subtract it
        optimal = max(0, available - request_tokens - safety_margin)
        
        # Never exceed model's absolute maximum
        optimal = min(optimal, limits['max_context_window'])
        
        return optimal
```

### 2. Updated TokenCounter

**Remove**:
- `_get_max_tokens()` method
- Static max_tokens dictionary

**Update**:
- `get_model_info()` - should accept agent_id and query Letta API, or return None for max_tokens
- `truncate_to_max_tokens()` - require explicit max_tokens parameter (no default)

### 3. Updated Request Processing Flow

```python
async def process_request(self, request: ChatCompletionRequest) -> ProcessedRequest:
    # ... existing code ...
    
    # Prepare messages and estimate tokens
    letta_messages, system_content, estimated_tokens = await self.prepare_messages(...)
    
    # Determine max_tokens to use
    if request.max_tokens is None:
        # User didn't specify - calculate optimal maximum
        optimal_max = await token_limit_service.calculate_optimal_max_tokens(
            agent_id=agent_id,
            request_tokens=estimated_tokens,
            safety_margin=100
        )
        max_tokens_to_use = optimal_max
        logger.info(f"Calculated optimal max_tokens: {optimal_max:,} (available: {available_tokens:,}, request: {estimated_tokens:,})")
    else:
        # User specified max_tokens - validate and use
        max_tokens_to_use = request.max_tokens
    
    # Validate token capacity
    is_valid, error_message = await self.validate_token_capacity(
        agent_id,
        estimated_tokens,
        requested_max_tokens=max_tokens_to_use
    )
    
    # ... rest of processing ...
    
    return ProcessedRequest(
        # ...
        max_tokens=max_tokens_to_use,  # Always set (never None)
        # ...
    )
```

### 4. Updated check_token_capacity()

```python
async def check_token_capacity(
    agent_id: str, 
    request_tokens: int, 
    requested_max_tokens: Optional[int] = None  # Now always provided (never None)
) -> tuple[bool, Optional[str], Optional[Dict[str, int]]]:
    """
    Check if request is valid based on current token usage and model limits.
    
    Args:
        agent_id: Letta agent ID
        request_tokens: Estimated tokens for the prompt
        requested_max_tokens: max_tokens value (always provided, calculated if user didn't specify)
    
    Returns:
        (is_valid, error_message, capacity_info)
    """
    # Get limits from Letta API
    limits = await token_limit_service.get_agent_token_limits(agent_id)
    max_context_window = limits['max_context_window']
    current_tokens = limits['current_tokens']
    available_tokens = limits['available_tokens']
    
    capacity_info = {
        'max_tokens': max_context_window,
        'current_tokens': current_tokens,
        'available_tokens': available_tokens,
        'request_tokens': request_tokens,
        'requested_max_tokens': requested_max_tokens
    }
    
    # Validate requested_max_tokens against model's absolute maximum
    if requested_max_tokens > max_context_window:
        error_msg = (
            f"Requested max_tokens ({requested_max_tokens:,}) exceeds model's maximum capability "
            f"({max_context_window:,} tokens)."
        )
        return False, error_msg, capacity_info
    
    # Calculate total needed
    total_needed = current_tokens + request_tokens + requested_max_tokens
    
    # Log if we're over capacity (summarization will handle it)
    if total_needed > max_context_window:
        logger.info(
            f"Request will exceed current capacity (needed: {total_needed:,}, max: {max_context_window:,}, "
            f"current: {current_tokens:,}). Will attempt summarization if context window full error occurs."
        )
    
    return True, None, capacity_info
```

---

## Key Design Decisions

### Decision 1: Safety Margin
**Question**: How much safety margin should we use when calculating optimal max_tokens?

**Options**:
- **Fixed**: Always use 100 tokens
- **Percentage**: Use X% of available tokens
- **Dynamic**: Based on request size (larger requests = larger margin)

**Recommendation**: Start with fixed 100 tokens, make configurable later.

### Decision 2: Caching Strategy
**Question**: Should we cache token limit queries?

**Considerations**:
- Token limits change as context grows
- Current usage changes with every request
- Max context window is relatively stable (per agent)

**Recommendation**: 
- Cache `max_context_window` per agent (TTL: 5 minutes)
- Always fetch `current_tokens` fresh (changes frequently)
- Cache key: `f"token_limits:{agent_id}"`

### Decision 3: Minimum max_tokens
**Question**: What if calculated optimal max_tokens is very small (e.g., < 10)?

**Options**:
- Allow it (let Letta handle)
- Set minimum threshold (e.g., 50 tokens)
- Return error to user

**Recommendation**: Set minimum of 50 tokens. If below threshold, log warning but proceed.

### Decision 4: Backward Compatibility
**Question**: How to handle existing code that calls `TokenCounter._get_max_tokens()`?

**Options**:
- Remove method entirely (breaking change)
- Deprecate and redirect to Letta API
- Keep as fallback with warning

**Recommendation**: Remove entirely. Update all callers to use Letta API.

---

## Implementation Plan

### Phase 1: Create TokenLimitService
- [ ] Create `src/librarian/token_limit_service.py`
- [ ] Implement `get_agent_token_limits()`
- [ ] Implement `calculate_optimal_max_tokens()`
- [ ] Add caching for `max_context_window`
- [ ] Add unit tests

### Phase 2: Update TokenCounter
- [ ] Remove `_get_max_tokens()` method
- [ ] Update `get_model_info()` to accept agent_id (or remove max_tokens)
- [ ] Update `truncate_to_max_tokens()` to require explicit max_tokens
- [ ] Update all callers
- [ ] Update tests

### Phase 3: Update Request Processing
- [ ] Integrate TokenLimitService into RequestProcessor
- [ ] Update `process_request()` to calculate optimal max_tokens when None
- [ ] Update `check_token_capacity()` to always receive max_tokens
- [ ] Update logging to show calculated vs requested max_tokens
- [ ] Update tests

### Phase 4: Testing & Validation
- [ ] Test with `max_tokens=None` (should calculate optimal)
- [ ] Test with `max_tokens` specified (should use user value)
- [ ] Test with `max_tokens` exceeding limits (should error)
- [ ] Test with very small available capacity
- [ ] Test caching behavior
- [ ] Integration tests

### Phase 5: Documentation
- [ ] Update API documentation
- [ ] Update usage guide
- [ ] Update architecture docs
- [ ] Add examples of optimal max_tokens calculation

---

## Edge Cases & Considerations

### Edge Case 1: Agent Has No Context
**Scenario**: New agent, `current_tokens = 0`

**Behavior**: 
- `available_tokens = max_context_window`
- Optimal max_tokens = `max_context_window - request_tokens - safety_margin`
- Should work correctly

### Edge Case 2: Context Nearly Full
**Scenario**: `current_tokens = 127,900`, `max_context_window = 128,000`, `request_tokens = 50`

**Behavior**:
- `available_tokens = 100`
- Optimal max_tokens = `100 - 50 - 100 = -50` → `max(0, -50) = 0`
- With minimum threshold: `max(0, 50) = 50`
- May trigger summarization on next request

### Edge Case 3: Request Exceeds Available
**Scenario**: `available_tokens = 100`, `request_tokens = 200`

**Behavior**:
- Optimal max_tokens = `100 - 200 - 100 = -200` → `0` (or minimum 50)
- Total needed = `current + 200 + 50 = exceeds max`
- Log warning, proceed (summarization will handle)

### Edge Case 4: Letta API Unavailable
**Scenario**: Cannot retrieve context from Letta

**Current Behavior**: Fail open (allow request)

**Proposed Behavior**: 
- Log error
- Use conservative default (e.g., 1000 tokens) if available
- Or fail closed (reject request) - needs decision

### Edge Case 5: Model Change
**Scenario**: Agent's model changed, `max_context_window` changed

**Behavior**:
- Cached value may be stale
- Cache TTL (5 min) will refresh
- Or invalidate cache on agent modification

---

## Questions for Discussion

1. **Safety Margin**: What's the right value? Should it be configurable?
2. **Caching**: What TTL for `max_context_window`? Should we invalidate on agent changes?
3. **Minimum Threshold**: Should we enforce minimum max_tokens? What value?
4. **Error Handling**: Fail open or closed when Letta API unavailable?
5. **Backward Compatibility**: How to handle existing integrations that rely on static limits?
6. **Performance**: How often should we query Letta API? Every request? Cached?
7. **User Experience**: Should we log/return the calculated optimal max_tokens to user?
8. **API Response**: Should we include `calculated_max_tokens` in response metadata?

---

## Fact-Checking & Verification

### Verified Against Implementation

✅ **API Endpoint**: `GET /agents/{id}/context` exists (confirmed in `docs/letta-api-reference.md:78`)
✅ **SDK Method**: `letta_client.agents.context.retrieve(agent_id=agent_id)` is used in `main.py:849`
✅ **Response Type**: Returns Pydantic model with `.model_dump()` method (confirmed in code)
✅ **Field Names**: Code uses `context_window_size_current` and `context_window_size_max` (confirmed in `main.py:853-854`)
✅ **Default Values**: Code uses `.get('field', 0)` with default 0 (confirmed in `main.py:853-854`)
✅ **AgentConfigManager**: Sets `max_tokens` on `LlmConfig` via `agents.modify()` (confirmed in `src/librarian/agent_config_manager.py:93-103`)

### Needs Verification (Cannot Test Without Live Server)

⚠️ **Field Names**: Assumed `context_window_size_current` and `context_window_size_max` - should verify actual field names from Letta API response
⚠️ **Field Types**: Assumed integers - should verify actual types
⚠️ **Response Structure**: Assumed flat dict with these fields - should verify full structure
⚠️ **Error Handling**: Current code fails open (allows request) if API unavailable - verify this is correct behavior

### Verification Test Script

A test script `test_context_api.py` was created to verify the actual API response structure. Run it when Letta server is available:

```bash
python test_context_api.py
```

This will print:
- All fields in the response
- Actual field names (to verify `context_window_size_current` and `context_window_size_max`)
- Field types
- Full response structure

### Code References

- `src/librarian/token_counter.py:135-145` - Static `_get_max_tokens()` method
- `main.py:826-890` - `check_token_capacity()` function (uses Letta API)
- `main.py:849-850` - Actual API call: `context = await letta_client.agents.context.retrieve(agent_id=agent_id)`
- `main.py:853-854` - Field extraction: `context_dict.get('context_window_size_current', 0)` and `context_dict.get('context_window_size_max', 0)`
- `src/librarian/request_processor.py:187-209` - Token capacity validation
- `src/librarian/agent_config_manager.py:93-103` - Setting max_tokens on LlmConfig
- `docs/letta-api-reference.md:78` - API endpoint documentation: `GET /agents/{id}/context`

### Assertions to Verify

1. **Field Names**: Verify `context_window_size_current` and `context_window_size_max` are correct (not `current_tokens`, `max_tokens`, etc.)
2. **Field Availability**: Verify these fields always exist (or if they can be None/missing)
3. **Field Types**: Verify they are integers (not strings, floats, etc.)
4. **Response Structure**: Verify if there are other relevant fields we should use
5. **API Behavior**: Verify if `context.retrieve()` can fail and how errors are structured

---

## References

- `src/librarian/token_counter.py` - Current static limits
- `main.py:826` - `check_token_capacity()` function
- `src/librarian/request_processor.py` - Request processing flow
- `src/librarian/agent_config_manager.py` - Agent configuration management
- `docs/letta-api-reference.md:78` - Letta API endpoint: `GET /agents/{id}/context`
- Letta API: `agents.context.retrieve()` - Source of truth for limits

---

## Status

- [ ] Design approved
- [ ] API response structure verified (run `test_context_api.py`)
- [ ] Field names confirmed
- [ ] Implementation started
- [ ] Tests written
- [ ] Documentation updated
- [ ] Deployed

**Last Updated**: 2025-01-XX

