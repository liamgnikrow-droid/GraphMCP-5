import os
import sys

# Standard boilerplate for Tools
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # Tools/
sys.path.append(parent_dir)

try:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    # Docker fallback
    sys.path.append(os.path.dirname(parent_dir))
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

def link_system_nodes():
    driver = get_driver()
    
    print("🔌 Connecting Implementation (Code) to Interface (System Nodes)...")
    
    # 1. Update Schema to allow relationships
    print("   1. Updating Schema (Meta-Graph)...")
    schema_queries = [
        """
        MATCH (f:NodeType {name: 'Function'}), (a:Action)
        MERGE (f)-[:ALLOWS_CONNECTION {type: 'IMPLEMENTS'}]->(a)
        """,
        """
        MATCH (f:NodeType {name: 'Function'}), (c:Constraint)
        MERGE (f)-[:ALLOWS_CONNECTION {type: 'IMPLEMENTS'}]->(c)
        """
    ]
    for q in schema_queries:
        driver.execute_query(q, database_="neo4j")
    
    # 2. Link Actions to Functions
    print("   2. Linking Actions to Functions...")
    
    # Logic: ACT-tool_name <-> tool_tool_name (Function)
    # The 'tool_name' in Action is like 'move_to'.
    # The function name in server.py is 'tool_move_to'.
    
    query_link_actions = """
    MATCH (a:Action)
    WHERE a.tool_name IS NOT NULL
    WITH a
    MATCH (f:Function)
    WHERE f.name = 'tool_' + a.tool_name
    MERGE (f)-[:IMPLEMENTS]->(a)
    RETURN f.name, a.uid
    """
    
    records, _, _ = driver.execute_query(query_link_actions, database_="neo4j")
    print(f"      Linked {len(records)} Actions:")
    for r in records:
        print(f"      - {r['f.name']} -> {r['a.uid']}")
        
    # 3. Link Constraints (Heuristic)
    print("   3. Linking Constraints (Heuristic)...")
    # CON-Russian_Language (function: cyrillic_ratio) -> Function 'cyrillic_ratio' ?
    # Typically constraints are logic snippets, but if they have a 'function' property, 
    # we can try to find a function with that name.
    
    query_link_constraints = """
    MATCH (c:Constraint)
    WHERE c.function IS NOT NULL
    WITH c
    MATCH (f:Function)
    WHERE f.name = c.function OR f.name ENDS WITH '.' + c.function
    MERGE (f)-[:IMPLEMENTS]->(c)
    RETURN f.name, c.uid
    """
    
    records_con, _, _ = driver.execute_query(query_link_constraints, database_="neo4j")
    if records_con:
         print(f"      Linked {len(records_con)} Constraints:")
         for r in records_con:
             print(f"      - {r['f.name']} -> {r['c.uid']}")
    else:
         print("      No direct function matches found for Constraints.")
         
    close_driver()
    print("✅ System Integration Complete.")

if __name__ == "__main__":
    link_system_nodes()
