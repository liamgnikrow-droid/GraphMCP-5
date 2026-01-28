import os
from neo4j import GraphDatabase

# --- CONFIG ---
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/workspace")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j-db:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

_driver = None

def get_driver():
    """
    Returns a shared Neo4j driver instance. 
    Handles lazy initialization and basic connectivity check.
    """
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            _driver.verify_connectivity()
            print(f"✅ DB: Connected to {NEO4J_URI}")
        except Exception as e:
            print(f"❌ DB: Failed to connect to Neo4j: {e}")
            _driver = None
    return _driver

def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
