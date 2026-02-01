import sys
import os
import time

# Add parent directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from graph_sync import GraphSync

def test_push():
    print("🧪 Starting Push Test...")
    sync = GraphSync()
    
    # 1. Create a dummy file
    test_uid = "IDEA-SyncTest"
    filename = f"Graph_Export/1_Ideas/{test_uid}.md"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    content = f"""---
uid: "{test_uid}"
title: "Sync Test Node"
description: "Initial description"
status: "Draft"
project_id: "test_proj"
type: "Idea"
---
# Sync Test Node

## Description
This is the content from DISK.
"""
    with open(filename, "w") as f:
        f.write(content)
        
    print(f"📄 Created test file: {filename}")
    
    # 2. Push to DB
    print("🚀 Pushing to Neo4j...")
    sync.push_file_to_db(filename)
    
    # 3. Verify in DB
    print("🔍 Verifying in Neo4j...")
    node = sync.fetch_node(test_uid)
    
    if node:
        props = node['props']
        print(f"   [DB] Title: {props.get('title')}")
        print(f"   [DB] Content: {props.get('content')}")
        
        if props.get('content') == "This is the content from DISK." and props.get('title') == "Sync Test Node":
             print("✅ PASS: DB matches Disk content.")
        else:
             print("❌ FAIL: Content mismatch.")
    else:
        print("❌ FAIL: Node not found in DB.")

    # Cleanup
    # os.remove(filename) # Keep it for inspection if needed

if __name__ == "__main__":
    test_push()
