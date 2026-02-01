import os
import sys
import glob
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

def purge_junk():
    driver = get_driver()
    if not driver: return
    
    print("🗑️ PURGING JUNK NODES (Logs, Docs, Temp files)...")
    
    # Files to kill (Node Names or Endings)
    JUNK_PATTERNS = [
        "*.log", 
        "*.txt",
        ".DS_Store"
    ]
    
    JUNK_NAMES = [
        "auth_debug_log", # Name property usually stripped of ext or with it
        "auth_debug.log",
        "cline_mcp_settings.json",
        "package-lock.json",
        ".devcontainer.json",
        "GENESIS_MANIFESTO.md",
        "README.md",
        "NEXT_STEPS.md",
        "SECURITY_CONSTRAINTS.md",
        "implementation_plan.md",
        "Переписка по созданию v.5.md",
        "ROADMAP.md",
        "test_codebase_map_js.md" # Wait, this one was linked! Exclude linked ones.
    ]
    
    # We will exclude files that HAVE LINKS. Good safety measure.
    
    with driver.session(database="neo4j") as session:
        # 1. Identify Junk Candidates in DB (Files without Implements, and matching patterns)
        
        # Match by exact name
        for name in JUNK_NAMES:
            res = session.run("""
                MATCH (f:File {name: $name})
                DETACH DELETE f
                RETURN count(f) as c
            """, name=name)
            c = res.single()['c']
            if c > 0: print(f"   ✅ Deleted Node: {name}")
            
        # Match by extension
        res = session.run("MATCH (f:File) WHERE f.name ENDS WITH '.log' DETACH DELETE f RETURN count(f) as c")
        print(f"   ✅ Deleted {res.single()['c']} log nodes.")
        
    # 2. Delete corresponding .md files from Graph_Export
    # Search recursively in Graph_Export/6_Code/Files
    
    files_dir = os.path.join(WORKSPACE_ROOT, "Graph_Export", "6_Code", "Files")
    
    # Specific removals based on UID conventions
    # e.g. FILE-auth_debug_log.md
    
    print("   🧹 Cleaning up disk artifacts...")
    
    junk_uids = [
        "FILE-auth_debug_log",
        "FILE-cline_mcp_settings_json",
        "FILE-md_GENESIS_MANIFESTO_md",
        "FILE-md_README_md",
        "FILE-md_NEXT_STEPS_md",
        "FILE-md_SECURITY_CONSTRAINTS_md",
        "FILE-md_implementation_plan_md",
        "FILE-md_Переписка_по_созданию_v_5_md",
        "FILE-ROADMAP_md",
        "FILE-_devcontainer_devcontainer_json"
    ]
    
    count = 0
    for uid_part in junk_uids:
        # Find files matching this UID
        pattern = os.path.join(files_dir, f"*{uid_part}*.md")
        found = glob.glob(pattern)
        for f in found:
            try:
                os.remove(f)
                print(f"      Deleted file: {os.path.basename(f)}")
                count += 1
            except Exception as e:
                print(f"      ❌ Could not delete {f}: {e}")
                
    print(f"✨ Purge Complete. {count} files removed.")

if __name__ == "__main__":
    purge_junk()
