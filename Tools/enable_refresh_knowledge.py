import sys
import os

# Add current directory to path so we can import db_config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from db_config import get_driver, close_driver
except ImportError:
    # Fallback if running from root
    sys.path.append(os.path.join(os.getcwd(), 'Tools'))
    from db_config import get_driver, close_driver

def enable_tool():
    driver = get_driver()
    if not driver:
        print("❌ No connection to Neo4j. Make sure the database is running.")
        return

    print("🔌 Connected to Neo4j. Enabling 'refresh_knowledge' as a GLOBAL tool...")

    # We define it as scope='global'. 
    # The server.py logic automatically allows any tool with scope='global' 
    # regardless of the agent's location.
    cypher = """
    MERGE (a:Action {uid: 'ACT-refresh_knowledge'})
    SET a.tool_name = 'refresh_knowledge',
        a.scope = 'global',
        a.description = 'Recalculates semantic embeddings for ALL nodes. Useful after manual edits or imports.'
    RETURN a.uid, a.tool_name, a.scope
    """
    
    try:
        with driver.session(database="neo4j") as session:
            result = session.run(cypher)
            record = result.single()
            print(f"✅ Success! Node: {record['a.uid']}")
            print(f"   Tool Name: {record['a.tool_name']}")
            print(f"   Scope: {record['a.scope']}")
            
    except Exception as e:
        print(f"❌ Error executing Cypher: {e}")
    finally:
        close_driver()

if __name__ == "__main__":
    enable_tool()
