
import os
import sys

# Standard boilerplate for Tools
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # Tools/
sys.path.append(parent_dir)

try:
    from db_config import get_driver, close_driver
except ImportError:
    # Docker fallback
    sys.path.append(os.path.dirname(parent_dir))
    from Tools.db_config import get_driver, close_driver

def fix_all_nodes():
    driver = get_driver()
    print("🔍 Fetching nodes with content...")
    
    # Fetch nodes where content is NOT NULL
    query = "MATCH (n) WHERE n.content IS NOT NULL RETURN n.uid as uid, n.content as content"
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    print(f"📊 Analyzing {len(records)} nodes...")
    
    updated_count = 0
    for r in records:
        uid = r['uid']
        content = r['content']
        
        if not uid or not content:
            continue
            
        # Split by paragraphs/double newlines
        parts = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # Deduplicate blocks while preserving order
        seen = set()
        unique_parts = []
        for p in parts:
            if p not in seen:
                unique_parts.append(p)
                seen.add(p)
        
        new_content = '\n\n'.join(unique_parts)
        
        if new_content != content:
            print(f"   ✨ Deduplicating node: {uid}")
            update_query = "MATCH (n {uid: $uid}) SET n.content = $content"
            driver.execute_query(update_query, {"uid": uid, "content": new_content}, database_="neo4j")
            updated_count += 1
            
    print(f"✅ Deduplication complete. Updated {updated_count} nodes.")
    close_driver()

if __name__ == "__main__":
    fix_all_nodes()
