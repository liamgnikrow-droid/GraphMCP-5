import sys
import os
import asyncio
import traceback

# Add proper path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import get_driver, tool_find_orphans

async def test():
    print("--- STARTING TEST: FIND ORPHANS ---")
    driver = get_driver()
    
    orphan_uid = "TEST_ORPHAN_01"
    
    # 1. Cleanup before start
    driver.execute_query("MATCH (n {uid: $uid}) DETACH DELETE n", {"uid": orphan_uid}, database_="neo4j")
    
    try:
        # 2. Create an Orphan Node
        print(f"\n[1] Creating Orphan Node: {orphan_uid}")
        driver.execute_query(
            "CREATE (:Idea {uid: $uid, title: 'Test Orphan', project_id: 'test_proj'})", 
            {"uid": orphan_uid}, 
            database_="neo4j"
        )
        
        # 3. Call tool_find_orphans (Should Find It)
        print("\n[2] Calling tool_find_orphans()...")
        # Ensure we are in the right project context for the query, or query returns project agnostic if we don't switch context in test.
        # But wait, logic in tool uses `get_current_project_id`. 
        # By default it might be default project. 
        # The tool says: WHERE (n.project_id = $project_id OR n.project_id IS NULL).
        # We need to make sure we create the orphan with the current project ID or generic.
        # Let's check what the current project ID is.
        # For this test, I'll rely on the tool filtering.
        # I'll update the orphan creation to have NULL project_id to be visible globally just in case,
        # OR I should check what get_current_project_id returns.
        # Since I can't easily check that without importing, I'll assume it defaults to something.
        # BETTER: I'll create the orphan with NO project_id.
        
        driver.execute_query(
             "MATCH (n {uid: $uid}) SET n.project_id = null", 
             {"uid": orphan_uid}, 
             database_="neo4j"
        )
        
        result = await tool_find_orphans({"limit": 50})
        text = result[0].text
        print(f"Result:\n{text}")
        
        if orphan_uid in text:
            print("✅ PASS: Orphan found.")
        else:
            print("❌ FAIL: Orphan NOT found.")
            return

        # 4. Link the Node (Should No Longer Be Orphan)
        print(f"\n[3] Linking {orphan_uid} to something...")
        driver.execute_query("""
            MATCH (n {uid: $uid}) 
            MERGE (root:Idea {uid: 'IDEA-Genesis'}) 
            MERGE (n)-[:RELATED_TO]->(root)
        """, {"uid": orphan_uid}, database_="neo4j")
        
        # 5. Call tool_find_orphans (Should NOT Find It)
        print("\n[4] Calling tool_find_orphans() again...")
        result = await tool_find_orphans({"limit": 50})
        text = result[0].text
        # print(f"Result:\n{text}")
        
        if orphan_uid not in text:
            print("✅ PASS: Node is no longer listed as orphan.")
        else:
            print("❌ FAIL: Node is STILL listed as orphan despite having links!")
            
    finally:
        # 6. Cleanup
        print(f"\n[5] Cleanup: Deleting {orphan_uid}")
        driver.execute_query("MATCH (n {uid: $uid}) DETACH DELETE n", {"uid": orphan_uid}, database_="neo4j")

if __name__ == "__main__":
    asyncio.run(test())
