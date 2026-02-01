import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

def apply_semantic_links():
    driver = get_driver()
    if not driver: return
    
    # List of Semantic Links identified by the Host Agent (AntiGravity)
    # Rationale: Direct mapping of Tool implementations to their Requirements in SPEC-Graph_Physics
    
    LINKS_TO_CREATE = [
        # --- File: server.py ---
        
        # Physics / Constraints
        {"source": "FUNC-Tools_server_py-validate_physics_constraints", "target": "REQUIREMENT-PRINCIPLE__METAGRAPH_LAW", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-check_constraints", "target": "REQUIREMENT-PRINCIPLE__METAGRAPH_LAW", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_explain_physics", "target": "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION", "type": "IMPLEMENTS"},
        
        # Tools Implementation
        {"source": "FUNC-Tools_server_py-tool_create_concept", "target": "REQUIREMENT-PRINCIPLE__LANGUAGE_INTEGRITY__RUSSIAN_P", "type": "IMPLEMENTS"}, # Enforces RU
        {"source": "FUNC-Tools_server_py-tool_register_task", "target": "REQUIREMENT-TOOL__REGISTER_TASK__ENTRY_POINT", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_switch_project", "target": "REQUIREMENT-TOOL__SWITCH_PROJECT__CONTEXT_ISOLATION", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_switch_project", "target": "REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_set_workflow", "target": "REQUIREMENT-TOOL__SET_WORKFLOW__MODE_CONTROL", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_set_workflow", "target": "REQUIREMENT-SYSTEM__WORKFLOW_ENFORCEMENT__ROLE_BASED", "type": "IMPLEMENTS"},
        
        {"source": "FUNC-Tools_server_py-tool_map_codebase", "target": "REQUIREMENT-TOOL__MAP_CODEBASE__CODE_INTEGRATION", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_look_for_similar", "target": "REQUIREMENT-TOOL__LOOK_FOR_SIMILAR__SEMANTIC_SEARCH", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_get_full_context", "target": "REQUIREMENT-TOOL__GET_FULL_CONTEXT__AGGREGATOR", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_look_around", "target": "REQUIREMENT-TOOL__LOOK_AROUND__DASHBOARD", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_read_node", "target": "REQUIREMENT-TOOL__READ_NODE__CONTENT_ACCESS", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_server_py-tool_illuminate_path", "target": "REQUIREMENT-TOOL__ILLUMINATE_PATH__VERTICAL_TRACE", "type": "IMPLEMENTS"},
        
        # Auth / System
        {"source": "FUNC-Tools_server_py-get_current_project_id", "target": "REQUIREMENT-AUTH_REQUIREMENT", "type": "IMPLEMENTS"},
        
        # --- File: graph_sync.py ---
        
        {"source": "CLASS-Tools_graph_sync_py-GraphSync", "target": "REQUIREMENT-PRINCIPLE__PURE_LINKS__NO_WIKI", "type": "IMPLEMENTS"}, 
        # (Since it handles rendering and cleaning links)
        
        # --- File: bootstrap_metagraph.py ---
        {"source": "FUNC-Tools_bootstrap_metagraph_py-bootstrap_metagraph", "target": "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO", "type": "IMPLEMENTS"},
        {"source": "FUNC-Tools_bootstrap_metagraph_py-verify_metagraph", "target": "REQUIREMENT-PRINCIPLE__METAGRAPH_LAW", "type": "IMPLEMENTS"},

        # --- File: db_config.py ---
        {"source": "FUNC-Tools_db_config_py-get_driver", "target": "REQUIREMENT-SYSTEM__MULTI_DATABASE_ISOLATION", "type": "IMPLEMENTS"},
    ]
    
    print(f"🚀 Deploying {len(LINKS_TO_CREATE)} Semantic Links...")
    
    with driver.session(database="neo4j") as session:
        count = 0
        for link in LINKS_TO_CREATE:
            s_uid = link['source']
            t_uid = link['target']
            rel = link['type']
            
            # Check existence first to avoid errors if nodes missing
            check = session.run("MATCH (s {uid: $s}), (t {uid: $t}) RETURN count(s) as c", s=s_uid, t=t_uid).single()['c']
            
            if check > 0:
                session.run(f"""
                    MATCH (s {{uid: $s}})
                    MATCH (t {{uid: $t}})
                    MERGE (s)-[:{rel}]->(t)
                """, s=s_uid, t=t_uid)
                print(f"   Mapped: {s_uid} -> {t_uid}")
                count += 1
            else:
                print(f"   ⚠️ Skip (Node missing): {s_uid} -> {t_uid}")
                
        print(f"✅ Created {count} high-confidence semantic links.")

if __name__ == "__main__":
    apply_semantic_links()
