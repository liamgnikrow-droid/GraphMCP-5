#!/usr/bin/env python3
"""
Test script for Meta-Graph powered middleware.
Tests:
1. get_allowed_tool_names() for different NodeTypes
2. Comparison with expected results from Meta-Graph
"""

import sys
sys.path.insert(0, '/opt/tools')

from server import get_allowed_tool_names
from db_config import get_driver

def test_global_tools():
    """Test that global tools are returned for any NodeType"""
    print("=" * 70)
    print("TEST 1: Global Tools (should be same for all)")
    print("=" * 70)
    
    expected_global = {"look_around", "move_to", "look_for_similar", "explain_physics", "register_task"}
    
    for node_type in ["Idea", "Spec", "Requirement", "Task", "Domain", "NonExistent"]:
        tools = set(get_allowed_tool_names(node_type))
        global_tools = tools & expected_global
        
        status = "✅" if global_tools == expected_global else "❌"
        print(f"{status} {node_type:15} → Global tools: {sorted(global_tools)}")
    
    print()

def test_contextual_tools():
    """Test contextual tools for each NodeType"""
    print("=" * 70)
    print("TEST 2: Contextual Tools (specific to NodeType)")
    print("=" * 70)
    
    test_cases = [
        ("Idea", {"create_concept", "link_nodes", "delete_node", "delete_link", "sync_graph", "propose_change"}),
        ("Spec", {"create_concept", "link_nodes", "delete_node", "delete_link", "sync_graph", "propose_change"}),
        ("Requirement", {"create_concept", "link_nodes", "delete_node", "delete_link", "sync_graph", "propose_change"}),
        ("Task", {"link_nodes", "delete_node", "delete_link", "sync_graph", "propose_change"}),  # Task cannot create_concept
        ("Domain", set()),  # Domain has no contextual tools
    ]
    
    for node_type, expected_contextual in test_cases:
        all_tools = set(get_allowed_tool_names(node_type))
        # Remove global tools to get only contextual
        contextual = all_tools - {"look_around", "move_to", "look_for_similar", "explain_physics", "register_task"}
        
        status = "✅" if contextual == expected_contextual else "❌"
        print(f"{status} {node_type:15} → Contextual: {sorted(contextual)}")
        
        if contextual != expected_contextual:
            missing = expected_contextual - contextual
            extra = contextual - expected_contextual
            if missing:
                print(f"   ⚠️  Missing: {sorted(missing)}")
            if extra:
                print(f"   ⚠️  Extra: {sorted(extra)}")
    
    print()

def test_spec_create_actions():
    """Test that Spec can create both Requirement and Domain"""
    print("=" * 70)
    print("TEST 3: Spec Create Actions (should allow Requirement + Domain)")
    print("=" * 70)
    
    driver = get_driver()
    query = """
    MATCH (nt:NodeType {name: 'Spec'})-[:CAN_PERFORM]->(a:Action)
    WHERE a.tool_name = 'create_concept'
    RETURN a.target_type as target_type
    ORDER BY target_type
    """
    
    records, _, _ = driver.execute_query(query, database_="neo4j")
    targets = [r["target_type"] for r in records]
    
    expected = ["Domain", "Requirement"]
    status = "✅" if targets == expected else "❌"
    
    print(f"{status} Spec can create: {targets}")
    print(f"   Expected: {expected}")
    print()

def main():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "META-GRAPH MIDDLEWARE TEST" + " " * 26 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    test_global_tools()
    test_contextual_tools()
    test_spec_create_actions()
    
    print("=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70)
    print()

if __name__ == "__main__":
    main()
