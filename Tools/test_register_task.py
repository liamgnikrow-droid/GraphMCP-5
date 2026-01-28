#!/usr/bin/env python3
"""
Test script for register_task tool.
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import tool_register_task
import asyncio

async def test_register_task_valid():
    """Test registering a valid Task"""
    print("=" * 70)
    print("TEST 1: Register Valid Task (Russian content)")
    print("=" * 70)
    
    result = await tool_register_task({
        "title": "Реализовать авторизацию пользователя",
        "description": "Добавить OAuth2 и JWT токены для безопасного входа"
    })
    
    print(result[0].text)
    print()

async def test_register_task_english():
    """Test registering a Task with English content (should fail)"""
    print("=" * 70)
    print("TEST 2: Register Task with English (should be blocked)")
    print("=" * 70)
    
    result = await tool_register_task({
        "title": "Implement user authentication",
        "description": "Add OAuth2 and JWT tokens"
    })
    
    print(result[0].text)
    print()

async def test_register_task_wikilinks():
    """Test registering a Task with WikiLinks (should fail)"""
    print("=" * 70)
    print("TEST 3: Register Task with WikiLinks (should be blocked)")
    print("=" * 70)
    
    result = await tool_register_task({
        "title": "Изучить [[GraphQL]] для API",
        "description": "Проверить совместимость с [[Neo4j]]"
    })
    
    print(result[0].text)
    print()

async def test_register_task_no_description():
    """Test registering a Task without description"""
    print("=" * 70)
    print("TEST 4: Register Task without description")
    print("=" * 70)
    
    result = await tool_register_task({
        "title": "Оптимизировать запросы к базе данных"
    })
    
    print(result[0].text)
    print()

async def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "REGISTER_TASK TEST" + " " * 29 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    await test_register_task_valid()
    await test_register_task_english()
    await test_register_task_wikilinks()
    await test_register_task_no_description()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()

if __name__ == "__main__":
    asyncio.run(main())
