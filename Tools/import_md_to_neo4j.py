#!/usr/bin/env python3
"""
Import MD files → Neo4j
Reads all .md files from Graph_Export/, parses YAML frontmatter,
and creates nodes + relationships in Neo4j.
"""
import os
import re
import sys
from pathlib import Path

# Add parent directory to path if running as script
if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT

GRAPH_EXPORT = Path(WORKSPACE_ROOT) / "Graph_Export"

def parse_frontmatter(content):
    """Extract YAML frontmatter from markdown (simple regex-based parser)"""
    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not match:
        return None
    
    frontmatter = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"')
            
            # Parse lists [...]
            if value.startswith('[') and value.endswith(']'):
                # Simple list parsing
                items = value[1:-1].split(',')
                frontmatter[key] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
            else:
                frontmatter[key] = value
    
    return frontmatter if frontmatter else None

def import_md_files():
    print("🔌 Connecting to Neo4j...")
    driver = get_driver()
    if not driver:
        return

    # 1. Collect all MD files
    # Also include Graph_Physics folder!
    physics_dir = Path(WORKSPACE_ROOT) / "Graph_Physics"
    
    md_files = []
    if GRAPH_EXPORT.exists():
        md_files.extend(list(GRAPH_EXPORT.rglob("*.md")))
    
    if physics_dir.exists():
        md_files.extend(list(physics_dir.rglob("*.md")))
        
    print(f"📄 Found {len(md_files)} MD files")
    
    nodes = []
    relationships = []
    
    # 2. Parse MD files
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding='utf-8')
            frontmatter = parse_frontmatter(content)
            
            if not frontmatter or 'uid' not in frontmatter:
                continue
            
            uid = frontmatter['uid']
            node_type = frontmatter.get('type', 'Unknown')
            title = frontmatter.get('title') or frontmatter.get('name') or md_file.stem
            status = frontmatter.get('status', 'unknown')
            
            # Extract Body (everything after the frontmatter closing ---)
            body = content
            fm_end_match = re.search(r'^---\n.*?\n---\n?', content, re.DOTALL)
            if fm_end_match:
                body = content[fm_end_match.end():].strip()
            
            # Simple description extraction
            description = frontmatter.get('description', '')
            if not description and body:
                desc_lines = body.split('\n')
                # Ignore lines starting with # (headers)
                for line in desc_lines:
                    if line.strip() and not line.strip().startswith('#'):
                        description = line.strip()[:200]
                        break
            
            nodes.append({
                'uid': uid,
                'type': node_type,
                'title': title,
                'status': status,
                'description': description,
                'content': body
            })
            
            # Extract relationships
            for rel_type in ['decomposes', 'implements', 'depends_on', 'relates_to', 'restricts', 'can_perform']:
                if rel_type in frontmatter:
                    targets = frontmatter[rel_type]
                    if not isinstance(targets, list):
                        targets = [targets]
                    
                    for target in targets:
                        target_uid = target.replace('[[', '').replace(']]', '').strip()
                        if target_uid:
                            relationships.append({
                                'source': uid,
                                'target': target_uid,
                                'type': rel_type.upper()
                            })
        except Exception as e:
            print(f"⚠️ Error parsing {md_file.name}: {e}")
            continue
    
    print(f"✅ Parsed {len(nodes)} nodes, {len(relationships)} relationships")
    
    # 3. Create nodes in Neo4j
    with driver.session(database="neo4j") as session:
        created = 0
        batch_size = 100
        
        # Use simple grouping by type strategy
        nodes_by_type = {}
        for n in nodes:
            t = n['type']
            if t not in nodes_by_type: nodes_by_type[t] = []
            nodes_by_type[t].append(n)
        
        for n_type, type_nodes in nodes_by_type.items():
            safe_label = "".join([c for c in n_type if c.isalnum() or c=='_'])
            if not safe_label: safe_label = "Unknown"
            
            for i in range(0, len(type_nodes), batch_size):
                batch = type_nodes[i:i+batch_size]
                session.run(f"""
                    UNWIND $batch AS node
                    MERGE (n:{safe_label} {{uid: node.uid}})
                    SET n.title = node.title,
                        n.status = node.status,
                        n.description = node.description,
                        n.content = node.content
                """, batch=batch)
                created += len(batch)
        print(f"✅ Created {created} nodes")

        # 4. Create relationships
        linked = 0
        rels_by_type = {}
        for r in relationships:
            t = r['type']
            if t not in rels_by_type: rels_by_type[t] = []
            rels_by_type[t].append(r)
            
        for r_type, type_rels in rels_by_type.items():
             safe_type = "".join([c for c in r_type if c.isalnum() or c=='_'])
             
             for i in range(0, len(type_rels), batch_size):
                batch = type_rels[i:i+batch_size]
                try:
                    session.run(f"""
                        UNWIND $batch AS rel
                        MATCH (source {{uid: rel.source}})
                        MATCH (target {{uid: rel.target}})
                        MERGE (source)-[r:{safe_type}]->(target)
                    """, batch=batch)
                    linked += len(batch)
                except Exception as e:
                    print(f"❌ Rel error: {e}")

        print(f"✅ Created {linked} relationships")
    
    close_driver()
    print("\n" + "="*70)
    print("✅ IMPORT COMPLETE")
    print("="*70)

if __name__ == "__main__":
    import_md_files()
