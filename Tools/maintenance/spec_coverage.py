
import os
import re
import sys
from pathlib import Path

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

SPEC_FILE = Path(WORKSPACE_ROOT) / "Graph_Export/2_Specs/SPEC-Graph_Physics.md"

def extract_spec_items(file_path):
    """Parses MD tables and extracts IDs and titles."""
    if not file_path.exists():
        return {}
    
    content = file_path.read_text(encoding='utf-8')
    # Match lines like | 1.2.1 | Name | ... |
    # We want the ID (group 1) and the Name (group 2)
    pattern = r"\|\s*([0-9.]+)\s*\|\s*([^|]+)\s*\|"
    items = {}
    
    for match in re.finditer(pattern, content):
        item_id = match.group(1).strip()
        item_title = match.group(2).strip()
        
        # Skip table headers (like 'ID')
        if item_id.lower() == 'id':
            continue
            
        items[item_id] = item_title
    
    return items

def get_coverage():
    spec_items = extract_spec_items(SPEC_FILE)
    if not spec_items:
        print("❌ Could not find any spec items in SPEC-Graph_Physics.md")
        return

    driver = get_driver()
    # Query coverage via relationships: (Req)-[:SATISFIES]->(SpecItem)
    query = """
    MATCH (si:SpecItem)
    OPTIONAL MATCH (req:Requirement)-[:SATISFIES]->(si)
    RETURN si.spec_id as item_id, si.title as title, collect(req.uid) as req_uids
    """
    records, _, _ = driver.execute_query(query, database_="neo4j")
    
    # Map spec_id -> list of covering requirements
    coverage_map = {}
    
    for r in records:
        item_id = r['item_id']
        req_uids = r['req_uids']
        coverage_map[item_id] = req_uids if req_uids and req_uids[0] else []

    # Print Report
    print("\n" + "="*80)
    print(f"{'ID':<10} | {'SPECIFICATION ITEM':<40} | {'COVERAGE'}")
    print("-"*80)
    
    covered_count = 0
    total_count = len(spec_items)
    
    # Sort IDs numerically (if possible) or lexicographically
    sorted_ids = sorted(spec_items.keys(), key=lambda x: [int(i) for i in x.split('.') if i.isdigit()] or [x])
    
    for item_id in sorted_ids:
        title = spec_items[item_id]
        reqs = coverage_map.get(item_id, [])
        
        status = "✅ OK" if reqs else "❌ MISSING"
        if reqs:
            covered_count += 1
            coverage_text = ", ".join(reqs)
        else:
            coverage_text = "-"
            
        # Truncate title for display
        display_title = (title[:37] + '...') if len(title) > 40 else title
        
        print(f"{item_id:<10} | {display_title:<40} | {status}")
        if reqs:
            for req in reqs:
                print(f"{' ':<10} | {' ':<40} |   ↳ {req}")

    print("-"*80)
    percentage = (covered_count / total_count * 100) if total_count > 0 else 0
    print(f"SUMMARY: {covered_count}/{total_count} items covered ({percentage:.1f}%)")
    print("="*80 + "\n")
    
    close_driver()

if __name__ == "__main__":
    get_coverage()
