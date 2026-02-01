import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver

def check_orphaned_files():
    driver = get_driver()
    if not driver: return
    
    print("🔍 Scanning for Orphaned Files (Files without IMPLEMENTS links)...")
    
    with driver.session(database="neo4j") as session:
        # Find Files that do NOT have an OUTGOING implementation link to a Requirement or Spec
        result = session.run("""
            MATCH (f:File)
            WHERE NOT (f)-[:IMPLEMENTS]->(:Requirement)
            AND NOT (f)-[:IMPLEMENTS]->(:Spec)
            RETURN f.uid as uid, f.name as name, f.path as path
            ORDER BY f.path
        """)
        
        orphans = list(result)
        
        if not orphans:
            print("✅ All files are linked! Zero orphans.")
        else:
            print(f"⚠️ Found {len(orphans)} ORPHANED Files (Need linking):")
            for record in orphans:
                print(f"   [{record['uid']}] {record['name']}")
                
    close_driver()

if __name__ == "__main__":
    check_orphaned_files()
