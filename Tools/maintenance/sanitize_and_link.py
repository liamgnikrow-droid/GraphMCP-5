import os
import sys
import shutil
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

def sanitize_and_link():
    driver = get_driver()
    if not driver: return
    
    print("🧹 Starting Graph Sanitization & Final Linking...")
    
    with driver.session(database="neo4j") as session:
        # 1. PURGE JUNK NODES
        # We define "Junk" as Files that should not be in the graph as distinct 'Code' nodes
        # e.g. logs, documentation markdowns (which are usually mapped as artifacts elsewhere), temporary json
        
        JUNK_EXTENSIONS = ['.log', '.md', '.txt'] # .md files are mapped as Files by codebase_mapper but usually represent Docs.
        # Exception: We might want to keep some, but generally for "Code->Req", .md files are noise.
        
        # We also filter by specific names if needed
        JUNK_NAMES = [
            'auth_debug.log', 
            'GENESIS_MANIFESTO.md', 
            'README.md', 
            'NEXT_STEPS.md', 
            'SECURITY_CONSTRAINTS.md',
            'implementation_plan.md',
            'Переписка по созданию v.5.md',
            'ROADMAP.md',
            'cline_mcp_settings.json', # User setting, not project code
            '.devcontainer.json'
        ]
        
        print(f"   🗑️  Removing {len(JUNK_NAMES)} specific junk nodes + logs...")
        
        deleted_count = 0
        for name in JUNK_NAMES:
             res = session.run("MATCH (f:File {name: $name}) DETACH DELETE f RETURN count(f) as c", name=name)
             c = res.single()['c']
             if c > 0:
                 print(f"      - Deleted {name}")
                 deleted_count += c
                 
        # Bulk delete logs
        res = session.run("MATCH (f:File) WHERE f.name ENDS WITH '.log' DETACH DELETE f RETURN count(f) as c")
        deleted_count += res.single()['c']
        
        print(f"   ✅ Purged {deleted_count} junk nodes.")

        # 2. LINK REMAINING ORPHANS
        # The remaining files (python, js, env) must be linked.
        
        print("   🔗 Linking remaining orphans...")
        
        LINKS = [
             ("test_impact_analysis.py", "REQUIREMENT-TOOL__EXPLAIN_PHYSICS__INTROSPECTION"),
             ("decompose_tools_specs.py", "REQUIREMENT-TOOL__CREATE_CONCEPT__ARCHITECT"), # Helper tool
             ("debug_ideas.py", "REQUIREMENT-TOOL__CREATE_CONCEPT__ARCHITECT"),
             ("test_codebase_map.js", "REQUIREMENT-TOOL__MAP_CODEBASE__CODE_INTEGRATION"),
             (".env", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"),
             (".mcp", "REQUIREMENT-SYSTEM__BOOTSTRAP___KERNEL_INITIALIZATIO"), # MCP config
        ]
        
        linked_count = 0
        for fname, req_uid in LINKS:
             # Flexible match
             res = session.run("""
                MATCH (f:File) 
                WHERE f.name = $fname OR f.uid CONTAINS $fname
                MATCH (r:Requirement {uid: $req})
                MERGE (f)-[:IMPLEMENTS]->(r)
                RETURN f.uid
             """, fname=fname, req=req_uid)
             
             if res.peek():
                 print(f"      - Linked {fname}")
                 linked_count += 1
                 
        print(f"   ✅ Linked {linked_count} files.")
        
    print("✨ Sanitization Complete.")

if __name__ == "__main__":
    sanitize_and_link()
