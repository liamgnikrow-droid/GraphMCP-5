#!/usr/bin/env python3
"""
Test script for explain_physics tool.
Tests introspection of Meta-Graph rules.
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import tool_explain_physics, get_driver
import asyncio

# Helper to set agent location for testing
def set_agent_location(uid):
    """Temporarily set agent location for testing"""
    driver = get_driver()
    # Delete old location
    driver.execute_query("MATCH (a:Agent {id: 'yuri_agent'})-[r:LOCATED_AT]->() DELETE r", database_="neo4j")
    # Set new location
    query = """
    MERGE (a:Agent {id: 'yuri_agent'})
    WITH a
    MATCH (n {uid: $uid})
    MERGE (a)-[:LOCATED_AT]->(n)
    """
    driver.execute_query(query, {"uid": uid}, database_="neo4j")

async def test_global_tool():
    """Test explaining a global tool (should always be available)"""
    print("=" * 70)
    print("TEST 1: Explain global tool 'look_around'")
    print("=" * 70)
    
    result = await tool_explain_physics({"tool_name": "look_around"})
    print(result[0].text)
    print()

async def test_contextual_allowed():
    """Test explaining a contextual tool that IS allowed at current location"""
    print("=" * 70)
    print("TEST 2: Explain 'create_concept' from Spec (ALLOWED)")
    print("=" * 70)
    
    # Move agent to a Spec node first
    driver = get_driver()
    # Find or create a Spec node
    records, _, _ = driver.execute_query(
        "MATCH (n:Spec) RETURN n.uid as uid LIMIT 1", 
        database_="neo4j"
    )
    
    if records:
        spec_uid = records[0]["uid"]
        set_agent_location(spec_uid)
        
        result = await tool_explain_physics({"tool_name": "create_concept"})
        print(result[0].text)
    else:
        print("⚠️  No Spec node found in database. Skipping test.")
    
    print()

async def test_contextual_blocked():
    """Test explaining a tool that is BLOCKED at current location"""
    print("=" * 70)
    print("TEST 3: Explain non-existent action from Task (BLOCKED)")
    print("=" * 70)
    
    # Move agent to a Task node (Task cannot create_concept)
    driver = get_driver()
    records, _, _ = driver.execute_query(
        "MATCH (n:Task) RETURN n.uid as uid LIMIT 1", 
        database_="neo4j"
    )
    
    if records:
        task_uid = records[0]["uid"]
        set_agent_location(task_uid)
        
        result = await tool_explain_physics({"tool_name": "create_concept"})
        print(result[0].text)
    else:
        print("⚠️  No Task node found in database. Skipping test.")
    
    print()

async def test_nonexistent_tool():
    """Test explaining a tool that doesn't exist"""
    print("=" * 70)
    print("TEST 4: Explain non-existent tool 'fly_to_moon'")
    print("=" * 70)
    
    result = await tool_explain_physics({"tool_name": "fly_to_moon"})
    print(result[0].text)
    print()

async def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 18 + "EXPLAIN_PHYSICS TEST" + " " * 29 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    await test_global_tool()
    await test_contextual_allowed()
    await test_contextual_blocked()
    await test_nonexistent_tool()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()

if __name__ == "__main__":
    asyncio.run(main())
