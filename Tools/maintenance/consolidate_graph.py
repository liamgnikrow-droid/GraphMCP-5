import os
import sys

# Standard boilerplate for Tools
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # Tools/
sys.path.append(parent_dir)

try:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    # Docker fallback
    sys.path.append(os.path.dirname(parent_dir))
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

def consolidate_graph():
    print("🧹 Starting Operation Clean Slate...")
    
    # whitelist
    WHITELIST = {
        "IDEA-Genesis",
        "SPEC-Graph_Physics",
        "SPEC-GRAPH_NATIVE_CONSTRAINTS"
    }
    
    driver = get_driver()
    
    # 1. Find Candidates
    query = """
    MATCH (n)
    WHERE (n:Idea OR n:Spec OR n:Task)
    RETURN n.uid as uid, labels(n)[0] as type, n.title as title
    """
    
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    to_delete = []
    
    print(f"🔍 Found {len(records)} candidate nodes.")
    
    for r in records:
        uid = r["uid"]
        rtype = r["type"]
        title = r["title"]
        
        if uid in WHITELIST:
            print(f"   ✅ KEEPING: [{rtype}] {uid}")
        else:
            print(f"   ❌ MARKED FOR DELETION: [{rtype}] {uid} ({title})")
            to_delete.append((uid, rtype))
            
    if not to_delete:
         print("✨ No nodes to clean up. Graph is clean.")
         return

    # 2. Execute Purge
    print(f"\n⚡ Purging {len(to_delete)} nodes...")
    
    # A. Delete from DB
    delete_uids = [item[0] for item in to_delete]
    
    del_query = """
    MATCH (n)
    WHERE n.uid IN $uids
    DETACH DELETE n
    """
    driver.execute_query(del_query, {"uids": delete_uids}, database_="neo4j")
    print("   ✅ DB Nodes deleted.")
    
    # B. Delete Files
    # We need to find the files. Since we know standard structure:
    # Ideas -> 1_Ideas
    # Specs -> 2_Specs
    # Tasks -> 3_Tasks
    
    counts = {"deleted": 0, "failed": 0}
    
    for uid, rtype in to_delete:
        folder = ""
        if rtype == "Idea": folder = "1_Ideas"
        elif rtype == "Spec": folder = "2_Specs"
        elif rtype == "Task": folder = "3_Tasks"
        
        if folder:
            # Try to find file
            filename = f"{uid}.md"
            path = os.path.join(WORKSPACE_ROOT, "Graph_Export", folder, filename)
            
            if os.path.exists(path):
                try:
                    os.remove(path)
                    print(f"   🗑️  Deleted file: {path}")
                    counts["deleted"] += 1
                except Exception as e:
                    print(f"   ⚠️  Failed to delete {path}: {e}")
                    counts["failed"] += 1
            else:
                print(f"   ⚠️  File not found (already gone?): {path}")
        
    print(f"\n🏁 Operation Clean Slate Complete.")
    print(f"   Nodes Removed from One Truth (DB): {len(delete_uids)}")
    print(f"   Files Deleted: {counts['deleted']}")
    
    close_driver()

if __name__ == "__main__":
    consolidate_graph()
