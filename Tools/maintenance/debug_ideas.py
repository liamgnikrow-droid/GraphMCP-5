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

def check_ideas():
    driver = get_driver()
    
    query = """
    MATCH (n:Idea)
    RETURN n.uid as uid, labels(n) as labels, n.title as title
    """
    
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    print("🧠 Remaining Ideas:")
    for r in records:
        print(f"   [{', '.join(r['labels'])}] {r['uid']} ({r['title']})")
        
    close_driver()

if __name__ == "__main__":
    check_ideas()
