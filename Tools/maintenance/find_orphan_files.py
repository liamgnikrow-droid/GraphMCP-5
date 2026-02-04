#!/usr/bin/env python3
"""
Диагностика и синхронизация файлов-призраков (orphan files).
Файлы, которые существуют в Graph_Export, но отсутствуют в Neo4j.
"""
import os
import sys
from pathlib import Path

sys.path.append("/opt/tools")
from db_config import get_driver, close_driver

def find_orphan_files():
    driver = get_driver()
    
    # Get all UIDs from Neo4j
    q = 'MATCH (n) WHERE NOT (n:NodeType) RETURN n.uid as uid'
    graph_recs, _, _ = driver.execute_query(q, database_='neo4j')
    graph_uids = set(r['uid'] for r in graph_recs if r['uid'])
    
    # Get all UIDs from files
    file_map = {}  # uid -> full path
    for root, dirs, files in os.walk('/workspace/Graph_Export'):
        for f in files:
            if f.endswith('.md') and not f.startswith('.'):
                uid = f[:-3]  # Remove .md
                file_map[uid] = os.path.join(root, f)
    
    # Find orphans
    orphan_files = set(file_map.keys()) - graph_uids
    
    print("🔍 ORPHAN FILES REPORT")
    print("=" * 60)
    print(f"Total files in Graph_Export: {len(file_map)}")
    print(f"Total nodes in Neo4j: {len(graph_uids)}")
    print(f"Orphan files (not in DB): {len(orphan_files)}")
    print()
    
    if orphan_files:
        print("📋 ORPHAN FILES:")
        for uid in sorted(orphan_files):
            path = file_map[uid]
            rel_path = path.replace('/workspace/', '')
            
            # Check if file has content
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    has_frontmatter = content.startswith('---')
                    size_kb = len(content) / 1024
                    
                print(f"\n  📄 {uid}")
                print(f"     Path: {rel_path}")
                print(f"     Size: {size_kb:.1f} KB, Lines: {len(lines)}")
                print(f"     Has frontmatter: {has_frontmatter}")
                
                # Categorize
                if uid.startswith('PROPOSAL-'):
                    print(f"     ⚠️ Category: Temporary proposal (safe to delete)")
                elif uid.startswith("'") or uid.endswith("'"):
                    print(f"     ⚠️ Category: Invalid filename format (quotes)")
                else:
                    print(f"     ℹ️ Category: Legacy/orphaned node (needs import)")
                    
            except Exception as e:
                print(f"     ❌ Error reading file: {e}")
    else:
        print("✅ No orphan files found. Graph and filesystem are in sync.")
    
    print()
    print("=" * 60)
    print("💡 RECOMMENDATIONS:")
    print("1. Delete PROPOSAL-* files (temporary meta-graph suggestions)")
    print("2. Fix filenames with quotes (rename or delete)")
    print("3. Import legitimate orphans using import_md_to_neo4j.py")
    
    close_driver()

if __name__ == "__main__":
    find_orphan_files()
