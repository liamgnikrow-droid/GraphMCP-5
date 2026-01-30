#!/usr/bin/env python3
"""
Diagnostic script to debug MCP parameter passing issues.
This script intercepts and logs all tool calls to see exactly what parameters are being passed.
"""

import sys
import os
import asyncio
import json

# Add proper path
sys.path.append("/opt/tools")

from server import mcp, list_tools, call_tool
import mcp.types as types


async def test_direct_call():
    """Test calling tools directly to verify server-side logic"""
    print("=" * 60)
    print("DIRECT TOOL CALL TEST (Server-Side)")
    print("=" * 60)
    
    # 1. Test list_tools
    print("\n1. Testing list_tools()...")
    tools = await list_tools()
    print(f"✅ Found {len(tools)} tools")
    
    # Find create_concept tool
    create_concept_tool = None
    for tool in tools:
        if tool.name == "create_concept":
            create_concept_tool = tool
            break
    
    if create_concept_tool:
        print(f"\n2. Found create_concept tool:")
        print(f"   Name: {create_concept_tool.name}")
        print(f"   Description: {create_concept_tool.description}")
        print(f"   Input Schema: {json.dumps(create_concept_tool.inputSchema, indent=2)}")
    
    # 2. Test calling create_concept with correct parameters
    print("\n3. Testing call_tool with CORRECT parameters...")
    test_args = {
        "type": "Task",
        "title": "Тестовая задача",
        "description": "Описание тестовой задачи"
    }
    print(f"   Arguments: {json.dumps(test_args, ensure_ascii=False, indent=2)}")
    
    try:
        result = await call_tool("create_concept", test_args)
        print(f"   ✅ Result: {result[0].text[:200]}...")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Test with MISSING required parameter
    print("\n4. Testing call_tool with MISSING required parameter...")
    bad_args = {
        "type": "Task",
        # Missing "title"
        "description": "Описание без заголовка"
    }
    print(f"   Arguments: {json.dumps(bad_args, ensure_ascii=False, indent=2)}")
    
    try:
        result = await call_tool("create_concept", bad_args)
        print(f"   Result: {result[0].text[:200]}...")
    except Exception as e:
        print(f"   ❌ Caught error: {type(e).__name__}: {e}")
    
    # 4. Test with WRONG types
    print("\n5. Testing call_tool with WRONG parameter types...")
    wrong_type_args = {
        "type": 123,  # Should be string
        "title": "Тест",
        "description": False  # Should be string
    }
    print(f"   Arguments: {json.dumps(wrong_type_args, ensure_ascii=False, indent=2)}")
    
    try:
        result = await call_tool("create_concept", wrong_type_args)
        print(f"   Result: {result[0].text[:200]}...")
    except Exception as e:
        print(f"   ❌ Caught error: {type(e).__name__}: {e}")


async def test_mcp_protocol():
    """Test simulating actual MCP protocol messages"""
    print("\n" + "=" * 60)
    print("MCP PROTOCOL SIMULATION TEST")
    print("=" * 60)
    
    # Simulate what the MCP client would send
    # According to MCP spec, tool calls come as JSON-RPC messages
    
    print("\n1. Simulating tools/list request...")
    # This would normally go through JSON-RPC, but we test directly
    tools = await list_tools()
    print(f"   ✅ Response contains {len(tools)} tools")
    
    print("\n2. Simulating tools/call request with parameters...")
    # Format: {"name": "tool_name", "arguments": {...}}
    call_request = {
        "name": "look_around",
        "arguments": {}
    }
    print(f"   Request: {json.dumps(call_request, indent=2)}")
    
    try:
        result = await call_tool(call_request["name"], call_request["arguments"])
        print(f"   ✅ Got result (length: {len(result[0].text)} chars)")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {e}")
    
    print("\n3. Testing with create_concept...")
    call_request2 = {
        "name": "create_concept",
        "arguments": {
            "type": "Idea",
            "title": "Диагностическая идея",
            "description": "Проверка передачи параметров через MCP"
        }
    }
    print(f"   Request: {json.dumps(call_request2, ensure_ascii=False, indent=2)}")
    
    try:
        result = await call_tool(call_request2["name"], call_request2["arguments"])
        print(f"   ✅ Result preview: {result[0].text[:150]}...")
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def inspect_mcp_server():
    """Inspect MCP server handlers and their signatures"""
    print("\n" + "=" * 60)
    print("MCP SERVER INTROSPECTION")
    print("=" * 60)
    
    print(f"\n1. MCP Server Name: {mcp.name}")
    print(f"   Server type: {type(mcp)}")
    
    # Check registered handlers
    print("\n2. Registered Request Handlers:")
    if hasattr(mcp, '_request_handlers'):
        for method, handler in mcp._request_handlers.items():
            print(f"   - {method}: {handler}")
    
    print("\n3. Inspect call_tool handler signature:")
    import inspect
    sig = inspect.signature(call_tool)
    print(f"   Signature: {sig}")
    print(f"   Parameters:")
    for param_name, param in sig.parameters.items():
        print(f"      - {param_name}: {param.annotation}")


async def main():
    print("\n🔍 MCP PARAMETER DEBUGGING TOOL")
    print("=" * 60)
    
    # Part 1: Introspection
    inspect_mcp_server()
    
    # Part 2: Direct calls
    await test_direct_call()
    
    # Part 3: Protocol simulation
    await test_mcp_protocol()
    
    print("\n" + "=" * 60)
    print("✅ DIAGNOSTIC COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
