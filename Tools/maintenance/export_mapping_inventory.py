import os
import sys
import json
from neo4j import GraphDatabase

# Setup environment
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from db_config import get_driver
except ImportError:
    print("Error: Could not import db_config.")
    sys.exit(1)

def export_mapping_data():
    driver = get_driver()
    if not driver: return
    
    data = {"requirements": [], "code": []}
    
    with driver.session(database="neo4j") as session:
        # 1. Fetch Requirements
        print("Fetching Requirements...")
        result_req = session.run("""
            MATCH (r:Requirement)
            RETURN r.uid as uid, r.title as title, r.description as desc
            ORDER BY r.uid
        """)
        for record in result_req:
            data["requirements"].append({
                "uid": record["uid"],
                "title": record["title"],
                "desc": record["desc"][:100] if record["desc"] else ""
            })
            
        # 2. Fetch Code (Functions & Classes in Tools/)
        print("Fetching Code structure...")
        result_code = session.run("""
            MATCH (f)
            WHERE (f:Function OR f:Class) AND f.path CONTAINS 'Tools/'
            RETURN f.uid as uid, f.name as name, f.path as path, labels(f) as type
            ORDER BY f.path, f.name
        """)
        for record in result_code:
            data["code"].append({
                "uid": record["uid"],
                "name": record["name"],
                "path": record["path"],
                "type": record["type"][0]
            })
            
    # Save to JSON for the Agent to read
    with open("mapping_inventory.json", "w", encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        
    print(f"✅ Exported {len(data['requirements'])} requirements and {len(data['code'])} code units.")

if __name__ == "__main__":
    export_mapping_data()
