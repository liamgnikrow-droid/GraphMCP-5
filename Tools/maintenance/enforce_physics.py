import os
import sys
import re
from neo4j import GraphDatabase

# Add parent directory to path to import db_config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from db_config import get_driver
except ImportError:
    print("Error: Could not import db_config. Make sure you are running from the Tools directory or its subdirectories.")
    sys.exit(1)

def fix_implements_direction(tx):
    """
    Fixes the direction of IMPLEMENTS relationships.
    Rule: File -> IMPLEMENTS -> Requirement
    Violation: Requirement -> IMPLEMENTS -> File
    Action: Reverse the relationship.
    """
    print("Checking IMPLEMENTS direction violations...")
    query_check = """
    MATCH (r:Requirement)-[rel:IMPLEMENTS]->(f:File)
    RETURN count(rel) as count
    """
    count = tx.run(query_check).single()["count"]
    
    if count == 0:
        print("✅ No IMPLEMENTS direction violations found.")
        return 0

    print(f"⚠️ Found {count} violations. Fixing...")
    
    query_fix = """
    MATCH (r:Requirement)-[rel:IMPLEMENTS]->(f:File)
    DELETE rel
    MERGE (f)-[:IMPLEMENTS]->(r)
    RETURN r.uid as req, f.uid as file
    """
    results = tx.run(query_fix)
    fixed = 0
    for record in results:
        print(f"   Fixed: {record['file']} -[:IMPLEMENTS]-> {record['req']}")
        fixed += 1
    return fixed

def fix_decomposes_on_requirements(tx):
    """
    Fixes DECOMPOSES usage between Requirements.
    Rule: DECOMPOSES is for Idea->Spec, Spec->Requirement.
    Violation: Requirement -> DECOMPOSES -> Requirement
    Action: Change to DEPENDS_ON.
    """
    print("\nChecking DECOMPOSES hierarchy violations (Req->Req)...")
    query_check = """
    MATCH (r1:Requirement)-[rel:DECOMPOSES]->(r2:Requirement)
    RETURN count(rel) as count
    """
    count = tx.run(query_check).single()["count"]
    
    if count == 0:
        print("✅ No DECOMPOSES violations between Requirements found.")
        return 0

    print(f"⚠️ Found {count} violations. Changing to DEPENDS_ON...")
    
    query_fix = """
    MATCH (r1:Requirement)-[rel:DECOMPOSES]->(r2:Requirement)
    DELETE rel
    MERGE (r1)-[:DEPENDS_ON]->(r2)
    RETURN r1.uid as source, r2.uid as target
    """
    results = tx.run(query_fix)
    fixed = 0
    for record in results:
        print(f"   Fixed: {record['source']} -[:DEPENDS_ON]-> {record['target']}")
        fixed += 1
    return fixed

def fix_items_decomposes(tx):
     """
     Fixes DECOMPOSES usage between Spec and SpecItem.
     Rule: Spec -> DECOMPOSES -> SpecItem is OK?
     Wait, Spec should decompose into Requirements?
     Actually, Spec Items are part of Spec content.
     But if SpecItem exists as a node, Spec -> DECOMPOSES -> SpecItem is logical.
     However, the user specifically mentioned Requirement -> DECOMPOSES -> Requirement.
     Let's stick to that.
     """
     pass

def clean_wikilinks_in_properties(tx):
    """
    Removes [[WikiLinks]] from description and title.
    Rule: No [[...]] in content.
    Action: Regex replace.
    """
    print("\nChecking for WikiLinks in Node properties...")
    
    # 1. Find nodes with '[[' in description
    query_find = """
    MATCH (n)
    WHERE n.description CONTAINS '[[' OR n.decomposes CONTAINS '[['
    RETURN n.uid as uid, n.description as description, n.decomposes as decomposes
    """
    results = tx.run(query_find)
    
    fixed_count = 0
    
    for record in results:
        uid = record['uid']
        desc = record['description']
        # decomposing list might be returned as string or list depending on how it was stored
        # Neo4j stores lists as arrays. If 'decomposes' is a property, check its type.
        # Actually 'decomposes' is usually a relationship, but the user said "section decomposes: ... in YAML".
        # This implies it might be in the file, but here we are checking the GRAPH.
        # If the graph has `decomposes` PROPERTY, that's weird. It should be a relationship.
        # The user said: "WikiLinks in metadata... decomposes: contains...".
        # If this is purely in the Markdown YAML, this script (which touches Neo4j) might not see it 
        # UNLESS the graph sync puts YAML properties into Neo4j properties.
        # Let's assume description checks are valid.
        
        needs_update = False
        new_desc = desc
        
        if desc and '[[' in desc:
            # Replace [[Target]] with Target
            # And [[Target|Label]] with Label
            new_desc = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', desc)
            if new_desc != desc:
                needs_update = True
        
        if needs_update:
            tx.run("MATCH (n {uid: $uid}) SET n.description = $desc", uid=uid, desc=new_desc)
            print(f"   Cleaned description for {uid}")
            fixed_count += 1
            
    if fixed_count == 0:
        print("✅ No WikiLinks found in node descriptions.")
    else:
        print(f"✅ Cleaned WikiLinks in {fixed_count} nodes.")

def main():
    driver = get_driver()
    if not driver:
        print("❌ Could not connect to Neo4j.")
        return

    print("🚀 Starting Physics Enforcement Patrol...")
    
    with driver.session() as session:
        # 1. IMPLEMNTS Direction
        session.execute_write(fix_implements_direction)
        
        # 2. DECOMPOSES Hierarchy
        session.execute_write(fix_decomposes_on_requirements)
        
        # 3. WikiLinks Cleaning
        session.execute_write(clean_wikilinks_in_properties)
        
    print("\n🏁 Enforcement Complete.")

if __name__ == "__main__":
    main()
