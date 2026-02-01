
import os
import sys

# Extract good content from the mess
file_path = "/Users/yuri/Documents/PROJECTS/AI-Infrastructure/GraphMCP-5/Graph_Export/2_Specs/SPEC-Graph_Physics.md"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

marker = "## 🔄 SYNC CONFLICT: Database Version"
if marker in content:
    # Take the header (before Description)
    parts = content.split("## Description")
    header = parts[0]
    
    # Take the good body (after the last conflict marker)
    good_body = content.split(marker)[-1]
    # Clean up the intro warning in the good body if any
    if "Below is the version from Neo4j Graph:" in good_body:
        good_body = good_body.split("Below is the version from Neo4j Graph:")[1].strip()

    new_content = header + "## Description\n\n" + good_body
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ File cleaned surgically.")
else:
    print("⚠️ No conflict marker found.")
