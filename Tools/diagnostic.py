import os
from neo4j import GraphDatabase

NEO4J_URI = "bolt://neo4j-db:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

def check_graph():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        # Check current location of agent
        result = session.run("MATCH (a:Agent {id: 'yuri_agent'})-[:LOCATED_AT]->(n) RETURN n.uid as uid, labels(n) as labels, n.title as title")
        record = result.single()
        if record:
            print(f"Agent Location: {record['uid']} ({record['labels'][0]}: {record['title']})")
        else:
            print("Agent Location: NOT SET")
            
        # Check all nodes
        print("\nAll Nodes:")
        result = session.run("MATCH (n) RETURN n.uid as uid, labels(n) as labels, n.title as title, n.embedding IS NOT NULL as has_emb LIMIT 15")
        for record in result:
            emb_str = "✅" if record['has_emb'] else "❌"
            print(f"- {record['uid']} ({record['labels'][0]}: {record['title']}) Emb: {emb_str}")
            
        # Check physics
        print("\nPhysics Node:")
        result = session.run("MATCH (n:Spec {uid: 'SPEC-Graph_Physics'}) RETURN n.uid as uid")
        if result.single():
            print("✅ SPEC-Graph_Physics found")
        else:
            print("❌ SPEC-Graph_Physics NOT FOUND")
            
    driver.close()

if __name__ == "__main__":
    check_graph()
