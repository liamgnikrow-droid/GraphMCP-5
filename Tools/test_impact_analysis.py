#!/usr/bin/env python3
"""
Test script for Impact Analysis in create_concept.
Tests that creating a node shows impact report.
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import tool_create_concept, get_driver
import asyncio

# Helper to set agent location
def set_agent_location(uid):
    driver = get_driver()
    driver.execute_query("MATCH (a:Agent {id: 'yuri_agent'})-[r:LOCATED_AT]->() DELETE r", database_="neo4j")
    query = """
    MERGE (a:Agent {id: 'yuri_agent'})
    WITH a
    MATCH (n {uid: $uid})
    MERGE (a)-[:LOCATED_AT]->(n)
    """
    driver.execute_query(query, {"uid": uid}, database_="neo4j")

async def test_create_with_impact():
    """Test creating Task and seeing impact analysis"""
    print("=" * 70)
    print("TEST 1: Create Task and see Impact Analysis")
    print("=" * 70)
    
    # Move to Idea
    driver = get_driver()
    idea_rec, _, _ = driver.execute_query("MATCH (n:Idea) RETURN n.uid as uid LIMIT 1", database_="neo4j")
    
    if idea_rec:
        idea_uid = idea_rec[0]["uid"]
        set_agent_location(idea_uid)
        
        result = await tool_create_concept({
            "type": "Task",
            "title": "Добавить двухфакторную аутентификацию",
            "description": "Реализовать 2FA через SMS и Email для повышения безопасности"
        })
        
        print(result[0].text)
    else:
        print("⚠️  No Idea node found")
    
    print()

async def test_create_duplicate():
    """Test creating similar Task (should warn about duplicates)"""
    print("=" * 70)
    print("TEST 2: Create similar Task (duplicate detection)")
    print("=" * 70)
    
    # Move to Idea
    driver = get_driver()
    idea_rec, _, _ = driver.execute_query("MATCH (n:Idea) RETURN n.uid as uid LIMIT 1", database_="neo4j")
    
    if idea_rec:
        idea_uid = idea_rec[0]["uid"]
        set_agent_location(idea_uid)
        
        result = await tool_create_concept({
            "type": "Task",
            "title": "Реализовать двухфакторную авторизацию",
            "description": "2FA через SMS и токены для безопасного входа"
        })
        
        print(result[0].text)
    else:
        print("⚠️  No Idea node found")
    
    print()

async def test_create_requirement():
    """Test creating Requirement from Spec"""
    print("=" * 70)
    print("TEST 3: Create Requirement from Spec (should show related Specs)")
    print("=" * 70)
    
    # Move to Spec
    driver = get_driver()
    spec_rec, _, _ = driver.execute_query("MATCH (n:Spec) RETURN n.uid as uid LIMIT 1", database_="neo4j")
    
    if spec_rec:
        spec_uid = spec_rec[0]["uid"]
        set_agent_location(spec_uid)
        
        result = await tool_create_concept({
            "type": "Requirement",
            "title": "Требование безопасности API",
            "description": "API должен использовать HTTPS и валидировать токены"
        })
        
        print(result[0].text)
    else:
        print("⚠️  No Spec node found")
    
    print()

async def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "IMPACT ANALYSIS TEST (create_concept)" + " " * 14 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    await test_create_with_impact()
    await test_create_duplicate()
    await test_create_requirement()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()
    print("💡 Impact Analysis shows:")
    print("   • Semantically similar nodes (duplicate detection)")
    print("   • Applied Constraints")
    print("   • Automatic links (parent)")
    print("   • Affected graph areas (related Specs/Requirements)")
    print()

if __name__ == "__main__":
    asyncio.run(main())
