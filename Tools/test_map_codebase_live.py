
import sys
import os
import asyncio

# Setup paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from code_mapper import CodeMapper
from server import get_driver, set_current_project, tool_map_codebase

async def test_live_mapping():
    print("🚀 Starting Live Code Mapping Test...")
    
    # 1. Setup Context
    project_id = "graphmcp"
    project_root = "/workspace" # Inside Docker
    
    # Ensure we are in the right project
    # Note: set_current_project updates global state in server.py
    set_current_project(project_id, project_root)
    
    # 2. Run Map Codebase Tool
    print(f"📂 Mapping project: {project_id} at {project_root}")
    results = await tool_map_codebase({})
    
    print("\n--- Tool Output ---")
    for res in results:
        print(res.text)
        
    # 3. Verify in Neo4j
    driver = get_driver()
    query = """
    MATCH (n:File {project_id: $pid})
    RETURN count(n) as file_count
    """
    records, _, _ = driver.execute_query(query, {"pid": project_id}, database_="neo4j")
    files = records[0]["file_count"]
    
    query_func = """
    MATCH (n:Function {project_id: $pid})
    RETURN count(n) as func_count
    """
    records_f, _, _ = driver.execute_query(query_func, {"pid": project_id}, database_="neo4j")
    funcs = records_f[0]["func_count"]
    
    print("\n--- Verification ---")
    print(f"📄 Files in Graph: {files}")
    print(f"⚡ Functions in Graph: {funcs}")
    
    if files > 0:
        print("✅ SUCCESS: Codebase mapped successfully!")
    else:
        print("❌ FAILURE: No files found in graph.")

if __name__ == "__main__":
    asyncio.run(test_live_mapping())
