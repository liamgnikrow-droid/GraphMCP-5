
import os
import sys
import re

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

def aggressive_clean():
    driver = get_driver()
    if not driver:
        print("❌ Could not connect to DB")
        return

    print("🔍 Fetching all nodes with content for AGGRESSIVE cleanup...")
    query = "MATCH (n) WHERE n.content IS NOT NULL RETURN n.uid as uid, n.content as content"
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    updated_count = 0
    for r in records:
        uid = r['uid']
        content = r['content']
        
        if not content: continue

        # Robust split: any sequence of 2+ newlines with optional whitespace
        parts = re.split(r'\n\s*\n', content)
        
        seen = set()
        unique_parts = []
        for p in parts:
            clean_p = p.strip()
            if not clean_p: continue
            
            # Use lean normalization for comparison
            norm_p = re.sub(r'\s+', ' ', clean_p).lower()
            
            if norm_p not in seen:
                unique_parts.append(clean_p)
                seen.add(norm_p)
        
        new_content = '\n\n'.join(unique_parts)
        
        if new_content.strip() != content.strip():
            print(f"   ✨ Cleaned: {uid}")
            update_query = "MATCH (n {uid: $uid}) SET n.content = $content"
            driver.execute_query(update_query, {"uid": uid, "content": new_content}, database_="neo4j")
            updated_count += 1

    print(f"✅ Cleaned {updated_count} nodes in Neo4j.")
    close_driver()

if __name__ == "__main__":
    aggressive_clean()
