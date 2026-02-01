import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver

def manual_link_confirmed():
    driver = get_driver()
    if not driver: return
    
    print("✍️ Executing Manual Linking based on Content Analysis...")
    
    # Pre-approved list based on User-requested analysis
    LINKS = [
        # Helper script for Requirements Generation -> System Bootstrap
        ("decompose_tools_specs.py", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
        
        # Debug script inspecting DB nodes -> Introspection Tool
        ("debug_ideas.py", "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION"),
        
        # Test script for Create Concept logic -> Create Concept Tool
        ("test_impact_analysis.py", "REQUIREMENT-TOOL__CREATE_CONCEPT__ARCHITECT"),
        
        # JS Test Client for MCP Protocol -> Map Codebase Tool (primary target of test)
        ("test_codebase_map.js", "REQUIREMENT-TOOL__MAP_CODEBASE__CODE_INTEGRATION"),
        
        # Configs
        (".env", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
        (".mcp", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO")
    ]
    
    with driver.session(database="neo4j") as session:
        count = 0
        for fname, req_uid in LINKS:
             result = session.run("""
                MATCH (f:File)
                WHERE f.name = $fname OR f.uid CONTAINS $clean_name
                MATCH (r:Requirement {uid: $req})
                MERGE (f)-[:IMPLEMENTS]->(r)
                RETURN f.uid
             """, fname=fname, clean_name=fname.replace(".", "_"), req=req_uid)
             
             if result.peek():
                 print(f"   ✅ Linked {fname} -> {req_uid}")
                 count += 1
             else:
                 print(f"   ⚠️ Node not found: {fname}")
                 
             # --- JUNK REMOVAL PROPOSAL (Commented out) ---
             # session.run("MATCH (f:File {name: 'auth_debug_log.md'}) DETACH DELETE f")
             
    print(f"✅ Created {count} validated links.")

if __name__ == "__main__":
    manual_link_confirmed()
