
import os
import sys

# Standard boilerplate for Tools
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # Tools/
sys.path.append(parent_dir)

from db_config import get_driver, close_driver

def final_fix():
    driver = get_driver()
    
    # 1. Get the GOOD content from the "conflict" section of the file
    file_path = "/workspace/Graph_Export/2_Specs/SPEC-Graph_Physics.md"
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    marker = "## 🔄 SYNC CONFLICT: Database Version"
    if marker in content:
        good_content = content.split(marker)[-1]
        if "Below is the version from Neo4j Graph:" in good_content:
            good_content = good_content.split("Below is the version from Neo4j Graph:")[1].strip()
        
        # 2. Set DB to this good content
        driver.execute_query("MATCH (n {uid: 'SPEC-Graph_Physics'}) SET n.content = $c", {"c": good_content}, database_="neo4j")
        print("✅ DB updated with good content.")
        
        # 3. Update the file to be EXACTLY what the DB will output
        parts = content.split("## Description")
        header = parts[0]
        # Important: the sync tool expects Header + ## Description + \n + body
        new_file_content = header + "## Description\n" + good_content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_file_content)
        print("✅ File updated with good content.")
    else:
        print("⚠️ Conflict marker not found in file.")
    
    close_driver()

if __name__ == "__main__":
    final_fix()
