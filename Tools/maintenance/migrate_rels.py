import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from Tools.db_config import get_driver, close_driver

def migrate_part_of_to_decomposes():
    driver = get_driver()
    if not driver: return

    with driver.session(database="neo4j") as session:
        print("🔄 Migrating PART_OF -> DECOMPOSES...")
        
        # 1. Copy relationships
        session.run("""
            MATCH (si:SpecItem)-[r:PART_OF]->(p:Spec)
            MERGE (p)-[:DECOMPOSES]->(si)
        """)
        
        # 2. Delete old relationships
        session.run("""
            MATCH (si:SpecItem)-[r:PART_OF]->(p:Spec)
            DELETE r
        """)
        
        # 3. Rename "SpecItem" to "Requirement"? 
        # The user said "Там только REQ". 
        # SpecItems are effectively micro-requirements. 
        # But we kept them as SpecItem nodes. 
        # If we want them to show up in frontmatter, they must be linked via a supported type.
        # Supported types: decomposes, implements, depends_on, relates_to, restricts, can_perform.
        # So DECOMPOSES is perfect.
        
        print("✅ Migration complete.")
        
        # Check results
        res = session.run("MATCH (p:Spec)-[r:DECOMPOSES]->(si:SpecItem) RETURN count(r) as c")
        print(f"New DECOMPOSES links: {res.single()['c']}")

    close_driver()

if __name__ == "__main__":
    migrate_part_of_to_decomposes()
