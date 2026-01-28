#!/usr/bin/env python3
"""
Test script for format_cypher tool (renamed from propose_change).
Tests that agent can format Cypher scripts WITHOUT executing them.
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import tool_format_cypher
import asyncio

async def test_format_node_type():
    """Test formatting Cypher for new NodeType"""
    print("=" * 70)
    print("TEST 1: Format Cypher for new NodeType 'File'")
    print("=" * 70)
    
    result = await tool_format_cypher({
        "change_type": "add_node_type",
        "details": {
            "name": "File",
            "description": "Represents a source code file",
            "max_count": None
        }
    })
    
    print(result[0].text)
    print()

async def test_format_action():
    """Test formatting Cypher for new Action"""
    print("=" * 70)
    print("TEST 2: Format Cypher for new Action")
    print("=" * 70)
    
    result = await tool_format_cypher({
        "change_type": "add_action",
        "details": {
            "uid": "ACT-create_file",
            "tool_name": "create_concept",
            "target_type": "File",
            "scope": "contextual",
            "allowed_from": ["Requirement", "Task"]
        }
    })
    
    print(result[0].text)
    print()

async def test_custom_cypher():
    """Test formatting custom Cypher"""
    print("=" * 70)
    print("TEST 3: Format custom Cypher script")
    print("=" * 70)
    
    custom_script = """
MATCH (c:Constraint {uid: 'CON-Russian_Language'})
SET c.cyrillic_threshold = 0.5
RETURN c
"""
    
    result = await tool_format_cypher({
        "change_type": "modify_rule",
        "details": {
            "cypher": custom_script
        }
    })
    
    print(result[0].text)
    print()

async def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "FORMAT_CYPHER TEST" + " " * 30 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    await test_format_node_type()
    await test_format_action()
    await test_custom_cypher()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()
    print("💡 format_cypher = Agent helps format, Human executes!")
    print("   No :Proposal nodes created")
    print("   No automatic execution")
    print("   Pure secretary mode")
    print()

if __name__ == "__main__":
    asyncio.run(main())
