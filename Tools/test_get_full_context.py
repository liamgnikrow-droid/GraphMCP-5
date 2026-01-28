#!/usr/bin/env python3
"""
Test script for get_full_context tool.
Tests complete context retrieval for agent decision-making.
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import tool_get_full_context
import asyncio

async def test_auth_context():
    """Test getting context for 'authorization' task"""
    print("=" * 70)
    print("TEST 1: Get full context for 'авторизация пользователей'")
    print("=" * 70)
    
    result = await tool_get_full_context({
        "query": "авторизация пользователей OAuth JWT токены"
    })
    
    print(result[0].text)
    print()

async def test_graph_context():
    """Test getting context for 'graph physics' task"""
    print("=" * 70)
    print("TEST 2: Get full context for 'Graph Physics'")
    print("=" * 70)
    
    result = await tool_get_full_context({
        "query": "правила графа мета-граф физика"
    })
    
    print(result[0].text)
    print()

async def test_english_query():
    """Test that English queries work (embeddings are multilingual)"""
    print("=" * 70)
    print("TEST 3: Get full context with English query")
    print("=" * 70)
    
    result = await tool_get_full_context({
        "query": "implement user authentication security"
    })
    
    print(result[0].text)
    print()

async def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 17 + "GET_FULL_CONTEXT TEST" + " " * 29 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    await test_auth_context()
    await test_graph_context()
    await test_english_query()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()
    print("💡 This tool gives agent FULL PICTURE for any task!")
    print()

if __name__ == "__main__":
    asyncio.run(main())
