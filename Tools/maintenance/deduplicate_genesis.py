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

def deduplicate_genesis():
    driver = get_driver()
    
    print("🔧 Deduplicating IDEA-Genesis...")
    
    query = """
    MATCH (n:Idea {uid: 'IDEA-Genesis'})
    RETURN n, id(n) as internal_id
    """
    
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    if len(records) > 1:
        print(f"   Found {len(records)} duplicates.")
        # Keep the first one, delete others by internal ID
        keep_id = records[0]['internal_id']
        delete_ids = [r['internal_id'] for r in records[1:]]
        
        print(f"   Keeping ID: {keep_id}")
        print(f"   Deleting IDs: {delete_ids}")
        
        del_query = """
        MATCH (n)
        WHERE id(n) IN $ids
        DETACH DELETE n
        """
        driver.execute_query(del_query, {"ids": delete_ids}, database_="neo4j")
        print("   ✅ Duplicates deleted.")
    else:
        print("   ✅ No duplicates found.")
        
    # Enforce Constraint
    print("\n🔒 Enforcing Unique Constraints...")
    try:
        # Check if constraint exists (lazy way: try create)
        # Neo4j 5 syntax might vary, using generic CREATE CONSTRAINT
        
        # 1. Generic Unique UID for all relevant labels? 
        # Usually we do it per label.
        labels = ["Idea", "Spec", "Requirement", "Task", "File", "Class", "Function"]
        
        for label in labels:
            c_query = f"CREATE CONSTRAINT unique_{label.lower()}_uid IF NOT EXISTS FOR (n:{label}) REQUIRE n.uid IS UNIQUE"
            driver.execute_query(c_query, database_="neo4j")
            print(f"   ✅ Constraint applied for :{label}")
            
    except Exception as e:
        print(f"   ⚠️ Constraint application warning: {e}")

    close_driver()

if __name__ == "__main__":
    deduplicate_genesis()
