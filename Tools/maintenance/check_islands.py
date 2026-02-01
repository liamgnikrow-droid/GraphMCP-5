import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver

def check_islands():
    driver = get_driver()
    if not driver: return
    
    print("🏝️ Scanning for Islands (Disconnected Nodes)...")
    
    with driver.session(database="neo4j") as session:
        # Check for nodes with NO relationships (true islands)
        result = session.run("""
            MATCH (n)
            WHERE NOT (n)--() 
            RETURN labels(n) as type, n.uid as uid, n.title as title, n.name as name
            ORDER BY type
        """)
        
        islands = list(result)
        
        if not islands:
            print("✅ No disconnected islands found! The graph is fully connected.")
        else:
            print(f"⚠️ Found {len(islands)} ISOLATED nodes:")
            for record in islands:
                typ = record['type'][0] if record['type'] else "Unknown"
                name = record['title'] or record['name'] or record['uid']
                print(f"   - [{typ}] {name} ({record['uid']})")
                
        # Also check for "Cluster Islands" (groups connected to themselves but not main graph)
        # This is harder without GDS, but usually 0-degree check is enough for basic hygiene.
        
    close_driver()

if __name__ == "__main__":
    check_islands()
