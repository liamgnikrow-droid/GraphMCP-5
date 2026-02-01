import os
import sys
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

# CANONICAL 5 RELATIONSHIP TYPES
# Reduced and simplified schema for maximum clarity.

SCHEMA_RULES = [
    # --- 1. DECOMPOSES (Vertical / Hierarchy) ---
    ("Idea", "DECOMPOSES", "Spec"),
    ("Spec", "DECOMPOSES", "Requirement"), 
    ("Spec", "DECOMPOSES", "SpecItem"),
    # Code Structure (Mapped from CONTAINS/PART_OF)
    ("File", "DECOMPOSES", "Class"),
    ("Class", "DECOMPOSES", "Function"),
    # Note: File->Function directly is also a decomposition if top-level
    ("File", "DECOMPOSES", "Function"),

    # --- 2. DEPENDS_ON (Horizontal / Dependency) ---
    ("Requirement", "DEPENDS_ON", "Requirement"),
    ("Spec", "DEPENDS_ON", "Spec"),
    # Code Dependencies (Mapped from IMPORTS/CALLS)
    ("File", "DEPENDS_ON", "File"),
    ("File", "DEPENDS_ON", "Module"),
    ("Function", "DEPENDS_ON", "Function"),

    # --- 3. IMPLEMENTS (Cross-Layer / Saturation) ---
    # STRICT MODE: Only File -> Requirement is allowed now (per Spec 3.4.3 update)
    ("File", "IMPLEMENTS", "Requirement"),
    
    # --- 4. RELATES_TO (Meta / Context) ---
    ("Task", "RELATES_TO", "Spec"),
    ("Task", "RELATES_TO", "Requirement"),
    ("Domain", "RELATES_TO", "Spec"),
    ("Domain", "RELATES_TO", "Requirement"),
    ("Domain", "RELATES_TO", "Idea"),
    # Bugs
    ("Bug", "RELATES_TO", "Spec"),
    ("Bug", "RELATES_TO", "Requirement"),
    ("Bug", "RELATES_TO", "Task"),

    # --- 5. CONFLICT (Logic / Friction) ---
    ("Requirement", "CONFLICT", "Requirement"),
    ("Bug", "CONFLICT", "Spec"),
    ("Bug", "CONFLICT", "Requirement")
]

def bootstrap_schema():
    driver = get_driver()
    if not driver: return
    
    print("🚀 Bootstrapping CANONICAL 5 Schema in Meta-Graph...")
    
    with driver.session(database="neo4j") as session:
        # 1. Ensure NodeTypes
        unique_types = set()
        for s, _, t in SCHEMA_RULES:
            unique_types.add(s)
            unique_types.add(t)
            
        print(f"Ensuring {len(unique_types)} NodeTypes exist...")
        for nt in unique_types:
            session.run("MERGE (:NodeType {name: $name})", name=nt)
            
        # 2. Clear OLD Schema
        print("Clearing OLD schema rules...")
        session.run("MATCH (:NodeType)-[r:ALLOWS_CONNECTION]->(:NodeType) DELETE r")
        
        # 3. Inject NEW Rules
        print(f"Injecting {len(SCHEMA_RULES)} Canonical rules...")
        count = 0
        for s, r_type, t in SCHEMA_RULES:
            session.run("""
                MATCH (source:NodeType {name: $s})
                MATCH (target:NodeType {name: $t})
                MERGE (source)-[:ALLOWS_CONNECTION {type: $r}]->(target)
            """, s=s, t=t, r=r_type)
            count += 1
            
        print(f"✅ Successfully created {count} rules. Iron Dome Updated.")

if __name__ == "__main__":
    bootstrap_schema()
