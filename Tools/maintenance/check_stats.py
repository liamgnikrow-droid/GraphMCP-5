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

def check_stats():
    driver = get_driver()
    
    query = """
    MATCH (n)
    RETURN labels(n)[0] as type, count(n) as count
    ORDER BY count DESC
    """
    
    print("📊 Current Graph Statistics:")
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    total = 0
    for r in records:
        print(f"   {r['type']}: {r['count']}")
        total += r['count']
        
    print(f"\n   Total Nodes: {total}")
    
    # Check relationships
    rel_query = """
    MATCH ()-[r]->()
    RETURN type(r) as type, count(r) as count
    """
    rel_records, _, _ = driver.execute_query(rel_query, database_="neo4j")
    print("\n🔗 Relationships:")
    for r in rel_records:
        print(f"   {r['type']}: {r['count']}")

    close_driver()

if __name__ == "__main__":
    check_stats()
