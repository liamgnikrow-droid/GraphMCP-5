import os
import shutil
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

def purge_specitems():
    driver = get_driver()
    if not driver: return
    
    print("🗑️ Purging illegal SpecItem nodes and files...")
    
    # 1. Delete from Neo4j
    with driver.session(database="neo4j") as session:
        result = session.run("""
            MATCH (n:SpecItem)
            DETACH DELETE n
            RETURN count(n) as items_deleted
        """)
        count = result.single()['items_deleted']
        print(f"   ✅ Deleted {count} SpecItem nodes from Graph.")
        
    # 2. Delete Files from Disk
    items_dir = os.path.join(WORKSPACE_ROOT, "Graph_Export", "2_Specs", "Items")
    if os.path.exists(items_dir):
        try:
             shutil.rmtree(items_dir)
             print(f"   ✅ Removed directory: {items_dir}")
        except Exception as e:
             print(f"   ❌ Failed to remove directory: {e}")
    else:
        print("   ✅ Directory already clean (not found).")
        
    print("🎉 Cleanup Complete. The law of One File for Spec is restored.")

if __name__ == "__main__":
    purge_specitems()
