#!/usr/bin/env python3
"""
Test script for propose_change tool (Architecture Mode).
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import tool_propose_change
import asyncio

async def test_add_node_type():
    """Test proposing a new NodeType"""
    print("=" * 70)
    print("TEST 1: Propose adding new NodeType 'Epic'")
    print("=" * 70)
    
    result = await tool_propose_change({
        "change_type": "add_node_type",
        "rationale": "Нужен узел Epic для группировки больших фич проекта",
        "details": {
            "name": "Epic",
            "description": "Крупная функциональная единица, объединяющая несколько Requirement",
            "max_count": None
        }
    })
    
    print(result[0].text)
    print()

async def test_add_action():
    """Test proposing a new Action"""
    print("=" * 70)
    print("TEST 2: Propose adding new Action for Epic")
    print("=" * 70)
    
    result = await tool_propose_change({
        "change_type": "add_action",
        "rationale": "Нужна возможность создавать Epic из Spec",
        "details": {
            "uid": "ACT-create_epic",
            "tool_name": "create_concept",
            "target_type": "Epic",
            "scope": "contextual",
            "allowed_from": ["Spec"]
        }
    })
    
    print(result[0].text)
    print()

async def test_add_constraint():
    """Test proposing a new Constraint"""
    print("=" * 70)
    print("TEST 3: Propose adding new Constraint")
    print("=" * 70)
    
    result = await tool_propose_change({
        "change_type": "add_constraint",
        "rationale": "Нужно ограничить длину заголовков до 100 символов",
        "details": {
            "uid": "CON-Title_Length",
            "rule_name": "Закон Длины Заголовка",
            "function": "string_length",
            "error_message": "Заголовок не должен превышать 100 символов",
            "restricts": ["ACT-create_spec", "ACT-create_req"]
        }
    })
    
    print(result[0].text)
    print()

async def test_english_rationale():
    """Test that English rationale is blocked"""
    print("=" * 70)
    print("TEST 4: Propose with English rationale (should fail)")
    print("=" * 70)
    
    result = await tool_propose_change({
        "change_type": "add_node_type",
        "rationale": "We need a new node type for tracking bugs",
        "details": {
            "name": "Bug",
            "description": "Bug tracking node"
        }
    })
    
    print(result[0].text)
    print()

async def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 16 + "PROPOSE_CHANGE TEST (Architecture Mode)" + " " * 12 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    await test_add_node_type()
    await test_add_action()
    await test_add_constraint()
    await test_english_rationale()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()
    print("💡 Check Graph_Export for created Proposal nodes")
    print()

if __name__ == "__main__":
    asyncio.run(main())
