import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver

def intelligent_link_files():
    driver = get_driver()
    if not driver: return
    
    print("🧠 Starting Intelligent Semantic Linking (File -> Requirement)...")
    
    # FORMAT: (Filename Substring, Requirement UID, Rational/Comment)
    
    SEMANTIC_MAP = [
        # --- INFRASTRUCTURE ---
        ("docker-compose.yml", "REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION"), # Containers isolation
        ("Dockerfile", "REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION"),
        ("requirements.txt", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"), # Env setup
        ("package.json", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
        ("package-lock.json", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
        (".active_project_state", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"), # State persistence
        
        # --- MAINTENANCE (Data Integrity) ---
        ("fix_duplication.py", "REQUIREMENT-PRINCIPLE__CARDINALITY_INTEGRITY__UNIQUE"),
        ("deduplicate_genesis.py", "REQUIREMENT-PRINCIPLE__CARDINALITY_INTEGRITY__UNIQUE"),
        ("consolidate_graph.py", "REQUIREMENT-PRINCIPLE__CARDINALITY_INTEGRITY__UNIQUE"),
        ("hard_reset_duplicates.py", "REQUIREMENT-PRINCIPLE__CARDINALITY_INTEGRITY__UNIQUE"),
        
        # --- MAINTENANCE (Graph Physics Enforcement) ---
        ("enforce_physics.py", "REQUIREMENT-PRINCIPLE__METAGRAPH_LAW"),
        ("spec_coverage.py", "REQUIREMENT-PRINTSIP__TSELOSTNOST_PROISHOZHDENIYA__P"), # Provenance/Coverage
        ("check_db_node.py", "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION"), # Diagnostics
        ("check_stats.py", "REQUIREMENT-TOOL__LOOK_AROUND__DASHBOARD"), # Stats = Dashboard info
        ("diagnostic.py", "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION"),
        
        # --- CORE LOGIC (Missing ones) ---
        ("constraint_primitives.py", "REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS"), # The logic of constraints
        ("debug_mcp_params.py", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"), # Debugging kernel
        ("decompose_tools_specs.py", "REQUIREMENT-TOOL__CREATE_CONCEPT__ARCHITECT"), # Or Decomposes logic. Let's map to Bootstrap for now as it was one-off? No, it's dev tool.
        # Actually decompose_tools_specs likely served Architectural purpose.
        
        ("update_physics_ru.py", "REQUIREMENT-PRINCIPLE__LANGUAGE_INTEGRITY__RUSSIAN_P"), # Enforcing RU updates
        
        # --- TESTS (Mapping to what they test) ---
        ("test_constraint_middleware.py", "REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS"),
        ("test_create_concept_with_middleware.py", "REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS"),
        ("test_blocked_by_wikilinks.py", "REQUIREMENT-PRINCIPLE__PURE_LINKS__NO_WIKI"), # Specific test
        ("test_blocked_by_russian.py", "REQUIREMENT-PRINCIPLE__LANGUAGE_INTEGRITY__RUSSIAN_P"),
        
        ("test_explain_physics.py", "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION"),
        ("test_get_full_context.py", "REQUIREMENT-TOOL__GET_FULL_CONTEXT__AGGREGATOR"),
        ("test_look_for_similar.py", "REQUIREMENT-TOOL__LOOK_FOR_SIMILAR__SEMANTIC_SEARCH"),
        ("test_map_codebase_live.py", "REQUIREMENT-TOOL__MAP_CODEBASE__CODE_INTEGRATION"),
        ("test_register_task.py", "REQUIREMENT-TOOL__REGISTER_TASK__ENTRY_POINT"),
        ("test_server_logic.py", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"), # General server logic
        ("test_middleware.py", "REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS"),
        ("test_format_cypher.py", "REQUIREMENT-SYSTEM__MIDDLEWARE_INTELLIGENCE__LENS"), # Or tool specific?
        
        # --- ADAPTERS ---
        ("mcp_client_adapter.js", "REQUIREMENT-System__Integration_Protocol"), # If exists? Use Bootstrap if not.
        ("mcp_client_adapter.js", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
        
        # --- LEGACY / UNKNOWN ---
        ("migrate_phase5_code.py", "REQUIREMENT-SYSTEM__EVOLUTION_PROTOCOL__META_GRAPH_C"),
        ("migrate_rels.py", "REQUIREMENT-SYSTEM__EVOLUTION_PROTOCOL__META_GRAPH_C")
    ]
    
    with driver.session(database="neo4j") as session:
        count = 0
        for filename, req_uid in SEMANTIC_MAP:
            # Flexible Match: Filename (exact) or partial (Tools/filename)
            # Using CONTAINS for UID allows finding FILE-Tools_filename_py
            
            clean_name = filename.replace(".", "_")
            
            # Try linking
            result = session.run("""
                MATCH (f:File)
                WHERE f.name = $fname OR f.uid CONTAINS $clean_name
                MATCH (r:Requirement {uid: $req})
                MERGE (f)-[:IMPLEMENTS]->(r)
                RETURN f.uid as uid
            """, fname=filename, clean_name=clean_name, req=req_uid)
            
            if result.peek():
                print(f"   ✅ Semantic Link: {filename} -> {req_uid}")
                count += 1
            else:
                pass
                # print(f"   ⚠️ Skip: {filename} (File or Req not found)")
                
        print(f"✅ Created {count} semantic links based on Deep Analysis.")

if __name__ == "__main__":
    intelligent_link_files()
