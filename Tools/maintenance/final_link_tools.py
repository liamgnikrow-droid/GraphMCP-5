import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver

def final_link_tools():
    driver = get_driver()
    if not driver: return
    
    print("🔧 Finalizing Tool Links (Code -> Requirements)...")
    
    # Exact mappings to ensure 100% coverage of core tools
    MAPPINGS = [
        ("Tools/codebase_mapper.py", "REQUIREMENT-TOOL__MAP_CODEBASE__CODE_INTEGRATION"),
        ("Tools/constraint_primitives.py", "REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS"),
        ("Tools/decompose_tools_specs.py", "REQUIREMENT-TOOL__CREATE_CONCEPT__ARCHITECT"), # Helper for concept creation decomp?
        ("Tools/diagnostic_py", "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION"), # Often named via UID part
        ("Tools/debug_mcp_params.py", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
        ("Tools/update_physics_ru.py", "REQUIREMENT-PRINCIPLE__LANGUAGE_INTEGRITY__RUSSIAN_P"),
    ]
    
    with driver.session(database="neo4j") as session:
        count = 0
        for filename, req_uid in MAPPINGS:
            clean_name = filename.replace("Tools/", "").replace(".", "_") # e.g. codebase_mapper_py
            
            # Try by NAME or UID part
            result = session.run("""
                MATCH (f:File)
                WHERE f.path ENDS WITH $path OR f.uid CONTAINS $clean_name
                MATCH (r:Requirement {uid: $req})
                MERGE (f)-[:IMPLEMENTS]->(r)
                RETURN f.uid as uid
            """, path=filename, clean_name=clean_name, req=req_uid)
            
            if result.peek():
                print(f"   ✅ Linked: {filename} -> {req_uid}")
                count += 1
            else:
                print(f"   ⚠️ Could not find file node for: {filename}")
                
    print(f"✅ Final Linking Complete. {count} links created.")

if __name__ == "__main__":
    final_link_tools()
