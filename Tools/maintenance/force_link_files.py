import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver

def force_link_files():
    driver = get_driver()
    if not driver: return
    
    print("🚀 Forcing FILE -> REQUIREMENT links (Surgical Operation)...")
    
    # Direct mapping: Partial Filename -> Requirement UID
    # We use partial names (e.g. "server.py") to find the file node regardless of its full path prefix
    
    MAPPINGS = [
        ("server.py", "REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION"),
        ("server.py", "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION"),
        ("server.py", "REQUIREMENT-TOOL__GET_FULL_CONTEXT__AGGREGATOR"),
        ("server.py", "REQUIREMENT-TOOL__LOOK_AROUND__DASHBOARD"),
        ("server.py", "REQUIREMENT-TOOL__LOOK_FOR_SIMILAR__SEMANTIC_SEARCH"),
        ("server.py", "REQUIREMENT-TOOL__MAP_CODEBASE__CODE_INTEGRATION"),
        ("server.py", "REQUIREMENT-TOOL__MOVE_TO__NAVIGATION"),
        ("server.py", "REQUIREMENT-TOOL__READ_NODE__CONTENT_ACCESS"),
        ("server.py", "REQUIREMENT-TOOL__REGISTER_TASK__ENTRY_POINT"),
        ("server.py", "REQUIREMENT-AUTH_REQUIREMENT"),
        
        ("graph_sync.py", "REQUIREMENT-PRINCIPLE__PURE_LINKS__NO_WIKI"),
        ("graph_sync.py", "REQUIREMENT-SYSTEM__EVOLUTION_PROTOCOL__META_GRAPH_C"),
        
        ("bootstrap_metagraph.py", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
        ("bootstrap_schema.py", "REQUIREMENT-PRINCIPLE__METAGRAPH_LAW"),
        ("bootstrap_schema.py", "REQUIREMENT-PRINTSIP__KANONICHESKAYA_ONTOLOGIYA__PYA"),
        
        ("import_md_to_neo4j.py", "REQUIREMENT-SYSTEM__EVOLUTION_PROTOCOL__META_GRAPH_C"),
        ("extract_md_content.py", "REQUIREMENT-TOOL__READ_NODE__CONTENT_ACCESS"),
        
        ("db_config.py", "REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION")
    ]
    
    with driver.session(database="neo4j") as session:
        count = 0
        for filename, req_uid in MAPPINGS:
            # Find File by substring in uid or name
            query = """
            MATCH (f:File)
            WHERE f.uid CONTAINS $fname OR f.name = $fname
            MATCH (r:Requirement {uid: $req})
            MERGE (f)-[:IMPLEMENTS]->(r)
            RETURN f.uid as f_uid
            """
            result = session.run(query, fname=filename.replace(".", "_"), req=req_uid)
            record = result.single()
            
            if record:
                print(f"   ✅ Linked: {filename} -> {req_uid}")
                count += 1
            else:
                # Try finding by exact name property if UID match failed
                result_retry = session.run("""
                    MATCH (f:File {name: $real_name})
                    MATCH (r:Requirement {uid: $req})
                    MERGE (f)-[:IMPLEMENTS]->(r)
                    RETURN f.uid as f_uid
                """, real_name=filename, req=req_uid)
                
                if result_retry.single():
                     print(f"   ✅ Linked (by name): {filename} -> {req_uid}")
                     count += 1
                else:
                     print(f"   ⚠️ Failed to link: {filename} (Node not found?)")
                     
        print(f"✅ Created {count} direct relationships. Checking islands is advised.")

if __name__ == "__main__":
    force_link_files()
