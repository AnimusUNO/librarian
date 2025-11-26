"""
Test script to verify Letta API context.retrieve() response structure

Usage:
    Set environment variables:
    - LETTA_BASE_URL (default: http://localhost:8283)
    - LETTA_API_KEY (optional)
    - LETTA_AGENT_ID (default: librarian)
    
    Then run: python test_context_api.py
"""
import asyncio
import os
import sys
import json
from letta_client import AsyncLetta

async def test_context_api():
    """Test the context.retrieve() API to see actual response structure"""
    
    # Get Letta connection details from environment
    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
    api_key = os.getenv("LETTA_API_KEY")
    
    # Initialize client
    if api_key:
        client = AsyncLetta(token=api_key, base_url=base_url)
    else:
        client = AsyncLetta(base_url=base_url)
    
    # Get agent ID from environment or use default
    agent_id = os.getenv("LETTA_AGENT_ID", "librarian")
    
    try:
        print(f"Testing context.retrieve() for agent: {agent_id}")
        print(f"Base URL: {base_url}")
        print("-" * 60)
        
        # Retrieve context
        context = await client.agents.context.retrieve(agent_id=agent_id)
        
        # Get the raw dict
        context_dict = context.model_dump()
        
        print("\n=== Raw Response (model_dump()) ===")
        print(f"Type: {type(context)}")
        print(f"Dict keys: {list(context_dict.keys())}")
        print(f"\nFull dict:")
        print(json.dumps(context_dict, indent=2, default=str))
        
        # Check for the fields we're using
        print("\n=== Field Verification ===")
        current_field = context_dict.get('context_window_size_current', 'NOT FOUND')
        max_field = context_dict.get('context_window_size_max', 'NOT FOUND')
        print(f"context_window_size_current: {current_field} (type: {type(current_field).__name__})")
        print(f"context_window_size_max: {max_field} (type: {type(max_field).__name__})")
        
        # Check all fields that might contain token info
        print("\n=== All Fields (token/window/context related) ===")
        relevant_fields = {}
        for key, value in context_dict.items():
            if 'token' in key.lower() or 'window' in key.lower() or 'context' in key.lower():
                relevant_fields[key] = value
                print(f"  {key}: {value} (type: {type(value).__name__})")
        
        if not relevant_fields:
            print("  No fields found matching 'token', 'window', or 'context'")
        
        # Check if it's a Pydantic model
        if hasattr(context, '__fields__'):
            print("\n=== Pydantic Model Fields ===")
            for field_name, field_info in context.__fields__.items():
                print(f"  {field_name}: {field_info.type_}")
        
        # Summary
        print("\n=== Summary ===")
        if current_field != 'NOT FOUND' and max_field != 'NOT FOUND':
            print("✅ Both expected fields found!")
            available = max_field - current_field if isinstance(max_field, (int, float)) and isinstance(current_field, (int, float)) else None
            if available is not None:
                print(f"   Available tokens: {available:,}")
        else:
            print("⚠️  Expected fields NOT found - check field names above")
            print("   Please update code with correct field names")
        
        return context_dict
        
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = asyncio.run(test_context_api())
    if result:
        print("\n✓ Test completed successfully")
        print("\nNext steps:")
        print("1. Verify field names match what's in main.py")
        print("2. Update token-limit-exploration.md with verified field names")
        print("3. Update code if field names are different")
    else:
        print("\n✗ Test failed")
        sys.exit(1)

