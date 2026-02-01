import sys
import os

# Add proper path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import get_driver

def register_tool():
    print("--- REGISTERING TOOL: find_orphans ---")
    driver = get_driver()
    
    # 1. Register Action as GLOBAL
    query = """
    MERGE (a:Action {tool_name: 'find_orphans'})
    SET a.uid = 'ACT-find_orphans',
        a.scope = 'global',
        a.description = 'Finds isolated nodes (orphans) that have NO relationships.'
    RETURN a
    """
    
    try:
        driver.execute_query(query, database_="neo4j")
        print("✅ Success: Registered global action 'find_orphans'")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    register_tool()
