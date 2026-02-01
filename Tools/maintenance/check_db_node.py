
import os
import sys

# Standard boilerplate for Tools
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # Tools/
sys.path.append(parent_dir)

from db_config import get_driver, close_driver

def check_node():
    driver = get_driver()
    query = "MATCH (n {uid: 'SPEC-Graph_Physics'}) RETURN n.content as content"
    records, _, _ = driver.execute_query(query, database_="neo4j")
    if records:
        content = records[0]['content']
        print(f"--- DB CONTENT ---")
        print(content[:500])
        print(f"--- END DB CONTENT ---")
        if "SYNC CONFLICT" in content:
            print("❌ DB contains conflict marker!")
            # Clean it
            clean_content = content.split("## 🔄 SYNC CONFLICT: Database Version")[-1]
            if "Below is the version from Neo4j Graph:" in clean_content:
                clean_content = clean_content.split("Below is the version from Neo4j Graph:")[1].strip()
            
            driver.execute_query("MATCH (n {uid: 'SPEC-Graph_Physics'}) SET n.content = $c", {"c": clean_content}, database_="neo4j")
            print("✅ DB cleaned in-place.")
    close_driver()

if __name__ == "__main__":
    check_node()
