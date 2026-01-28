import sys
import os
import asyncio
# Add proper path
sys.path.append("/opt/tools")

from server import get_driver, get_agent_location, get_node_type, get_allowed_tool_names, tool_create_concept

async def test():
    print("--- STARTING PHYSICS TEST: TASK FLEXIBILITY ---")
    
    # helper
    async def try_create_task(context_uid, context_type, task_title):
        print(f"\n[Testing Context: {context_type} ({context_uid})]")
        
        # 1. Force Move (Backdoor for testing)
        driver = get_driver()
        driver.execute_query("""
            MERGE (a:Agent {id: 'yuri_agent'})
            WITH a
            MATCH (target {uid: $uid})
            OPTIONAL MATCH (a)-[r:LOCATED_AT]->(old)
            DELETE r
            CREATE (a)-[:LOCATED_AT]->(target)
        """, {"uid": context_uid}, database_="neo4j")
        
        # 2. Check Allowed Tools
        allowed = get_allowed_tool_names(context_type)
        print(f"  Allowed Tools: {allowed}")
        
        if "create_concept" not in allowed:
            print(f"  ❌ FAIL: create_concept forbiden in {context_type}")
            return

        # 3. Try Create Task
        result = await tool_create_concept({
            "type": "Task",
            "title": task_title,
            "description": f"Testing task creation from {context_type}"
        })
        
        print(f"  Result: {result[0].text}")

    # --- EXECUTION ---
    
    # 1. IDEA Level
    # Ensure IDEA-Genesis exists
    get_driver().execute_query("MERGE (:Idea {uid: 'IDEA-Genesis', title: 'Genesis'})", database_="neo4j")
    await try_create_task("IDEA-Genesis", "Idea", "TASK-From-Idea")
    
    # 2. SPEC Level
    # Create a dummy Spec to attach to
    get_driver().execute_query("MERGE (:Spec {uid: 'SPEC-Test', title: 'Test Spec'})", database_="neo4j")
    await try_create_task("SPEC-Test", "Spec", "TASK-From-Spec")
    
    # 3. REQUIREMENT Level
    # Create a dummy Req
    get_driver().execute_query("MERGE (:Requirement {uid: 'REQ-Test', title: 'Test Req'})", database_="neo4j")
    await try_create_task("REQ-Test", "Requirement", "TASK-From-Req")

    # 4. RUSSIAN TITLE Test
    get_driver().execute_query("MERGE (:Idea {uid: 'IDEA-RussianTest', title: 'Russian Test'})", database_="neo4j")
    await try_create_task("IDEA-RussianTest", "Idea", "Задача на Русском")


if __name__ == "__main__":
    asyncio.run(test())
