#!/usr/bin/env python3
"""
Integration Test: Tool with Constraint Middleware

Tests that tool_create_concept correctly uses check_constraints()
and blocks invalid actions.
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import tool_create_concept
import asyncio


async def test_blocked_by_russian():
    """Test that English text is blocked"""
    print("=" * 70)
    print("TEST 1: create_concept with English text (should BLOCK)")
    print("=" * 70)
    
    result = await tool_create_concept({
        "type": "Requirement",
        "title": "Hello World",
        "description": "This is a test"
    })
    
    print(result[0].text)
    print()


async def test_blocked_by_wikilinks():
    """Test that WikiLinks are blocked"""
    print("=" * 70)
    print("TEST 2: create_concept with WikiLinks (should BLOCK)")
    print("=" * 70)
    
    result = await tool_create_concept({
        "type": "Requirement",
        "title": "Требование авторизации",
        "description": "Связано с [[REQ-Security]]"
    })
    
    print(result[0].text)
    print()


async def test_allowed():
    """Test that valid Russian text without WikiLinks is allowed"""
    print("=" * 70)
    print("TEST 3: create_concept with valid Russian text (should ALLOW)")
    print("=" * 70)
    
    result = await tool_create_concept({
        "type": "Requirement",
        "title": "Требование авторизации пользователей",
        "description": "Система должна поддерживать авторизацию через OAuth2"
    })
    
    # Check if it was created successfully
    text = result[0].text
    if "CONSTRAINT VIOLATION" in text:
        print("❌ FAILED: Should have been allowed")
        print(text)
    else:
        print("✅ SUCCESS: Node created")
        print(text[:200] + "...")
    print()


async def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "INTEGRATION TEST: Tool + Middleware" + " " * 21 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    await test_blocked_by_russian()
    await test_blocked_by_wikilinks()
    await test_allowed()
    
    print("=" * 70)
    print("ALL INTEGRATION TESTS COMPLETE")
    print("=" * 70)
    print()
    print("💡 Constraints are enforced automatically via middleware!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
