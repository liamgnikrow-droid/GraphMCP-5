from neo4j import GraphDatabase
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-db:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 1. New Node Types
node_types = [
    {"name": "File", "desc": "Source code file"},
    {"name": "Class", "desc": "Class definition"},
    {"name": "Function", "desc": "Function definition"}
]

print("🚀 Starting Migration Phase 5: Code Integration...")

try:
    with driver.session() as session:
        # 1. Add Node Types
        for nt in node_types:
            session.run("""
            MERGE (n:NodeType {name: $name})
            SET n.description = $desc
            """, name=nt["name"], desc=nt["desc"])
            print(f"✅ Added NodeType: {nt['name']}")

        # 2. Add 'map_codebase' Action (Global)
        session.run("""
        MERGE (a:Action {uid: 'ACT-map_codebase', tool_name: 'map_codebase'})
        SET a.scope = 'global',
            a.description = 'Scan active project codebase and create File/Class/Function nodes'
        """)
        print("✅ Added Action: map_codebase")
        
except Exception as e:
    print(f"❌ Migration Failed: {e}")
finally:
    driver.close()
