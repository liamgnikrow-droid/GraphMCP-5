import os
import sys
from neo4j import GraphDatabase

# Setup environment
try:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT

def finalize_cleanup():
    driver = get_driver()
    if not driver: return
    
    print("🧹 Finalizing Graph Hygiene...")
    
    with driver.session(database="neo4j") as session:
        # 1. DELETE PROPOSALS and Unknowns
        # These are stale interaction artifacts
        res = session.run("MATCH (n:Proposal) DETACH DELETE n RETURN count(n) as c")
        print(f"   Deleted {res.single()['c']} Proposal nodes.")
        
        res = session.run("MATCH (n:Unknown) DETACH DELETE n RETURN count(n) as c")
        print(f"   Deleted {res.single()['c']} Unknown nodes.")
        
        # 2. DELETE devcontainer leftovers
        res = session.run("MATCH (f:File) WHERE f.name CONTAINS 'devcontainer.json' DETACH DELETE f RETURN count(f) as c")
        print(f"   Deleted {res.single()['c']} devcontainer nodes.")
        
        # 3. LINK ACTIONS/CONSTRAINTS to SPEC (The Physics Spec)
        # This grounds the physics layer into the documentation graph
        
        # Link Actions -> DECOMPOSES -> SPEC-Graph_Physics? Or DEFINED_BY?
        # Let's use DECOMPOSES as they are parts of the spec system, or PART_OF. 
        # But Schema only allows DECOMPOSES. Let's assume Spec DECOMPOSES into Actions (logically).
        # Wait, check schema rules. Spec -> DECOMPOSES -> Requirement. 
        # Spec -> DEFINED_BY? No. 
        # Requirement -> IMPLEMENTS -> Spec.
        # Maybe Action IS A Requirement? No.
        # Let's link them to REQUIREMENT-PRINCIPLE__METAGRAPH_LAW via RELATES_TO ?
        # Or just leave them alone if schema is strict.
        
        # Checking schema:
        # ("Requirement", "RELATES_TO", "Spec") is allowed? No. ("Task", "RELATES_TO", "Spec").
        # If we can't link them legally, we skip.
        # But wait, "Constraint" and "Action" are NOT in the strict schema at all?
        # They are meta-types. So we can probably link them ad-hoc or they stay islands.
        # Let's TRY to link them to REQUIREMENT-PRINCIPLE__METAGRAPH_LAW using 'RELATES_TO'.
        # Assuming we eventually allow RELATES_TO for everything meta.
        # Check graph_sync for RELATES_TO support -> YES, we added it.
        
        # Actually, let's keep it simple: DELETE JUNK ONLY. 
        # If user wants actions linked, we need a schema update. 'Islands' of physics are acceptable for now.
        
    print("✨ Cleanup Complete.")

if __name__ == "__main__":
    finalize_cleanup()
