# Proposed Solution for Issue #18

## Verification Status

The issue description is comprehensive and well-documented. The exploration document (`docs/token-limit-exploration.md`) provides detailed analysis.

**Field Names**: Based on existing code in `main.py:853-854`, we're using:
- `context_window_size_current` 
- `context_window_size_max`

These field names are already in use and working in production, so we can proceed with implementation.

## Implementation Approach

### Phase 1: Create TokenLimitService
1. Create `src/librarian/token_limit_service.py` with:
   - `get_agent_token_limits(agent_id)` - fetches from Letta API
   - `calculate_optimal_max_tokens(agent_id, request_tokens, safety_margin=100)` - calculates optimal max
   - Simple in-memory cache for `max_context_window` (TTL: 5 minutes)
   - Always fetch `current_tokens` fresh (changes frequently)

### Phase 2: Update TokenCounter
1. Remove `_get_max_tokens()` method entirely
2. Update `get_model_info()` to remove `max_tokens` field (or make it optional/None)
3. Update `truncate_to_max_tokens()` to require explicit `max_tokens` parameter (no default)
4. Update all callers in codebase

### Phase 3: Update Request Processing
1. Integrate `TokenLimitService` into `RequestProcessor`
2. In `process_request()`: when `request.max_tokens is None`, calculate optimal using `TokenLimitService`
3. Update `check_token_capacity()` to always receive a value (never None)
4. Add logging for calculated vs requested max_tokens

### Phase 4: Testing
1. Update existing tests to work with new structure
2. Add tests for `TokenLimitService`
3. Add tests for optimal max_tokens calculation
4. Test edge cases (nearly full context, API unavailable, etc.)

### Phase 5: Documentation
1. Update docstrings
2. Update exploration document with verified information

## Design Decisions

Based on the exploration document:
- **Safety Margin**: Fixed 100 tokens (can be made configurable later)
- **Minimum Threshold**: 50 tokens minimum for calculated max_tokens
- **Caching**: Cache `max_context_window` per agent (5 min TTL), always fetch `current_tokens` fresh
- **Error Handling**: Fail open (allow request) if Letta API unavailable (matches current behavior)

## Breaking Changes

- `TokenCounter._get_max_tokens()` will be removed
- `TokenCounter.get_model_info()` will no longer return `max_tokens` (or it will be None)
- `TokenCounter.truncate_to_max_tokens()` will require explicit `max_tokens` parameter

All callers will need to be updated, but this is intentional - we want to eliminate static limits.

## Testing Strategy

1. **Unit Tests**: Test `TokenLimitService` methods with mocked Letta API responses
2. **Integration Tests**: Test full request flow with `max_tokens=None` and `max_tokens` specified
3. **Edge Case Tests**: Test with nearly full context, API unavailable, etc.
4. **Regression Tests**: Ensure existing functionality still works

## Implementation Order

1. Create `TokenLimitService` with tests
2. Update `TokenCounter` and all callers
3. Update `RequestProcessor` to use `TokenLimitService`
4. Update `check_token_capacity()` signature
5. Run full test suite
6. Update documentation


