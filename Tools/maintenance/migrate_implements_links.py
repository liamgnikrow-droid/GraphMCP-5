import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver

def migrate_hierarchical_links():
    driver = get_driver()
    if not driver: return
    
    print("🚀 Starting Migration: Roll-up IMPLEMENTS links to File level...")
    
    with driver.session(database="neo4j") as session:
        # 1. Roll-up FUNCTION -> REQUIREMENT
        print("   Processing Functions...")
        result = session.run("""
            MATCH (func:Function)-[r:IMPLEMENTS]->(req:Requirement)
            MATCH (file:File)-[:DECOMPOSES*]->(func) // Find parent file (recursively if needed)
            
            // Create link from File
            MERGE (file)-[ new_r:IMPLEMENTS ]->(req)
            
            // Delete old link
            DELETE r
            RETURN count(r) as migrated
        """)
        print(f"   ✅ Migrated {result.single()['migrated']} Function links.")

        # 2. Roll-up CLASS -> REQUIREMENT
        print("   Processing Classes...")
        result = session.run("""
            MATCH (cls:Class)-[r:IMPLEMENTS]->(req:Requirement)
            MATCH (file:File)-[:DECOMPOSES*]->(cls)
            
            MERGE (file)-[ new_r:IMPLEMENTS ]->(req)
            
            DELETE r
            RETURN count(r) as migrated
        """)
        print(f"   ✅ Migrated {result.single()['migrated']} Class links.")

        # 3. Clean up any other Illegal Links (Function -> Spec, etc) if they exist
        print("   Cleaning residual illegal links (to Spec/SpecItem)...")
        session.run("""
            MATCH (code)-[r:IMPLEMENTS]->(target)
            WHERE (labels(code)[0] IN ['Function', 'Class']) 
            OR (labels(target)[0] IN ['Spec', 'SpecItem'])
            DELETE r
        """)
        
    print("✅ Migration Complete. Graph is now strictly File->Requirement compliant.")

if __name__ == "__main__":
    migrate_hierarchical_links()
