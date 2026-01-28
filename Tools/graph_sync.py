import os
import json
import glob
from neo4j import GraphDatabase
import time

import sys
# Add parent directory to path if running as script
if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    from db_config import get_driver, close_driver, WORKSPACE_ROOT

# Folder Mapping
TYPE_TO_FOLDER = {
    "Epic": "0_Epics",
    "Idea": "1_Ideas",
    "Spec": "2_Specs",
    "Task": "3_Tasks",
    "Bug": "3_Tasks",
    "Requirement": "4_Requirements",
    "Domain": "5_Domain",
    "Roadmap": "2_Specs",
    "File": "6_Code/Files",
    "Class": "6_Code/Classes",
    "Function": "6_Code/Functions",
    "Module": "6_Code/Modules",
    # Architecture Nodes
    "Constraint": "Graph_Physics",
    "Action": "Graph_Physics",
    "NodeType": "Graph_Physics"
}

class GraphSync:
    def __init__(self):
        self.driver = None

    def get_driver(self):
        return get_driver()

    def close(self):
        if self.driver:
            self.driver.close()

    def fetch_node(self, uid: str):
        """
        Fetches full node state from Neo4j:
        - Properties
        - Labels (Type)
        - Incoming/Outgoing Relationships
        """
        drv = self.get_driver()

        # 1. Fetch Node Properties
        query_node = """
        MATCH (n)
        WHERE n.uid = $uid
        RETURN n, labels(n) as labels
        """
        records, _, _ = drv.execute_query(query_node, {"uid": uid}, database_="neo4j")

        if not records:
            return None

        node_props = dict(records[0]['n'])
        labels = records[0]['labels']

        # Determine Primary Type
        node_type = "Unknown"
        # Prioritize known types
        for label in labels:
            if label in TYPE_TO_FOLDER:
                node_type = label
                break

        # 2. Fetch Relationships
        # STRICT CANONICAL: We only care about IMPLEMENTS, DECOMPOSES, DEPENDS_ON, CONFLICT, IMPORTS
        # RELATED_TO is forbidden and ignored.
        query_rels = """
        MATCH (n {uid: $uid})-[r]-(other)
        WHERE type(r) IN ['IMPLEMENTS', 'DECOMPOSES', 'DEPENDS_ON', 'CONFLICT', 'IMPORTS']
        RETURN
            startNode(r).uid as source,
            endNode(r).uid as target,
            type(r) as type,
            r.justification as justification,
            r.auto as auto,
            other.title as title,
            other.name as name,
            other.uid as other_uid
        """
        rel_records, _, _ = drv.execute_query(query_rels, {"uid": uid}, database_="neo4j")

        relationships = []
        for rel in rel_records:
            is_outgoing = (rel['source'] == uid)
            other_uid = rel['other_uid']
            other_title = rel['title'] or rel['name'] or other_uid

            relationships.append({
                "type": rel['type'],
                "target": other_uid if is_outgoing else uid,
                "other_uid": other_uid,
                "other_title": other_title,
                "direction": "OUT" if is_outgoing else "IN",
                "justification": rel.get('justification'),
                "auto": rel.get('auto', False)
            })

        return {
            "props": node_props,
            "type": node_type,
            "labels": labels,
            "relationships": relationships
        }

    def render_markdown(self, node_data: dict) -> str:
        """
        Generates premium Markdown content for Obsidian + Juggl.
        """
        props = node_data['props']
        node_type = node_data['type']
        uid = props.get('uid')
        title = props.get('title') or props.get('name') or uid
        description = props.get('description') or ""
        status = props.get('status', 'Draft')

        # CSS Classes for Juggl and Modern Look
        css_classes = ["juggl-node", f"type-{node_type.lower()}", "premium-card"]
        if node_type in ["Task", "Bug"]:
            css_classes.append("kanban-card")
        if node_type == "Epic":
            css_classes.append("epic-node")
        
        # Frontmatter
        fm_lines = ["---"]
        fm_lines.append(f'uid: "{uid}"')
        fm_lines.append(f'title: "{title}"')
        fm_lines.append(f'type: "{node_type}"')

        # Add all metadata properties
        for key, val in props.items():
            if key not in ['uid', 'type', 'title', 'description', 'created_at', 'updated_at', 'content', 'embedding']:
                if val is not None:
                    if isinstance(val, bool):
                        fm_lines.append(f'{key}: {str(val).lower()}')
                    elif isinstance(val, (int, float)):
                        fm_lines.append(f'{key}: {val}')
                    else:
                        # Escape quotes
                        safe_val = str(val).replace('"', '\\"')
                        fm_lines.append(f'{key}: "{safe_val}"')

        fm_lines.append(f'tags: [graph/{node_type.lower()}, state/{status.lower().replace(" ", "_")}]')
        fm_lines.append(f'cssclasses: [{", ".join(css_classes)}]')

        # --- RELATIONSHIPS (YAML ONLY) ---
        rels = sorted(node_data['relationships'], key=lambda x: (x['type'], x['other_uid']))
        
        # We store relationships in a structured way that Juggl can exploit
        # and as flat properties for Obsidian's native 'Properties' view.
        typed_rels = {}
        for rel in rels:
            # We treat OUTGOING as primary semantic links
            if rel['direction'] == 'OUT':
                rel_type = rel['type'].lower().replace('_', '-')
                target = rel['other_uid']
                
                if rel_type not in typed_rels:
                    typed_rels[rel_type] = []
                typed_rels[rel_type].append(f"[[{target}]]")

        # Add to frontmatter
        for key, links in typed_rels.items():
            if links:
                # Obsidian standard for multiple links in properties
                fm_lines.append(f"{key}:")
                for link in links:
                    fm_lines.append(f"  - \"{link}\"")

        fm_lines.append("---")

        # Body
        body = []
        body.append(f"# {title}")
        body.append("")
        
        # Status Bar / Breadcrumbs (Optional but premium)
        body.append(f"> [!abstract] {node_type} Context")
        body.append(f"> **ID:** `{uid}` | **Status:** `{status}`")
        body.append("")

        if description:
            body.append("## Description")
            body.append(description)
            body.append("")
            
        # Content (Full Body)
        content = props.get('content')
        if content:
             # Just append the content directly without wrapping it in "## Content"
             # This allows full markdown documents to be synched properly.
             body.append(content)
             body.append("")
         
        return "\n".join(fm_lines + body)

    def extract_body_from_markdown(self, file_path: str) -> str:
        """
        Extracts the body (text after frontmatter) from an existing markdown file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple Frontmatter extraction
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    return parts[2].strip()
            return content
        except Exception:
            return ""

    def sync_node(self, uid: str, sync_connected: bool = False):
        """
        Full Sync: Fetch -> Render -> Write.
        If sync_connected is True, also syncs nodes directly connected to this one.
        
        SAFE MODE: If file exists and Neo4j 'content' is empty, preserve existing file body.
        """
        node_data = self.fetch_node(uid)
        if not node_data:
            print(f"⚠️ GraphSync: Node {uid} not found in Neo4j.")
            return None

        node_type = node_data['type']
        subfolder = TYPE_TO_FOLDER.get(node_type, "9_Unclassified")
        filename = f"{uid}.md"
        safe_filename = filename.replace("/", "_").replace("\\", "_")

        dir_path = os.path.join(WORKSPACE_ROOT, "Graph_Export", subfolder)
        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, safe_filename)
        
        # === CONTENT MERGE STRATEGY ===
        # Priority 1: Content from Neo4j (if exists)
        # Priority 2: Existing Body from File (if Neo4j content is empty)
        # Priority 3: Description from Neo4j
        
        db_content = node_data['props'].get('content')
        existing_body = ""
        
        if os.path.exists(file_path):
             existing_body = self.extract_body_from_markdown(file_path)
        
        if db_content:
            # DB has authority
            pass 
        elif existing_body:
            # DB is empty, but file has content -> Preserve file content
            # We inject it into node_data temporarily for rendering
            # Note: We append it as 'content' property to be handled by render_markdown
            node_data['props']['content'] = existing_body
            # Also ensure we don't double-h3 title if body already has it.
            # render_markdown handles 'content' by appending it.
        
        content = self.render_markdown(node_data)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✅ GraphSync: Synced {uid} to {file_path}")

        if sync_connected:
            print(f"🔄 GraphSync: Syncing neighbors of {uid}...")
            for rel in node_data['relationships']:
                neighbor_uid = rel['other_uid']
                self.sync_node(neighbor_uid, sync_connected=False) # Avoid recursion loop

        return file_path

    def delete_node(self, uid: str):
        """
        Removes the markdown file associated with a UID.
        Neo4j deletion must be handled separately.
        """
        # We don't know the type easily without fetching, so we search all folders
        export_root = os.path.join(WORKSPACE_ROOT, "Graph_Export")
        filename = f"{uid}.md"
        safe_filename = filename.replace("/", "_").replace("\\", "_")
        
        found = False
        for root, dirs, files in os.walk(export_root):
            if safe_filename in files:
                file_path = os.path.join(root, safe_filename)
                os.remove(file_path)
                print(f"🗑️ GraphSync: Removed file {file_path}")
                found = True
        
        if not found:
            print(f"ℹ️ GraphSync: No file found for {uid} to delete.")
        return found

    def sync_all(self):
        """
        Regenerate ALL markdown files from Neo4j.
        """
        drv = self.get_driver()

        query = "MATCH (n) RETURN n.uid as uid"
        records, _, _ = drv.execute_query(query, database_="neo4j")

        count = 0
        for r in records:
            uid = r['uid']
            if uid:
                self.sync_node(uid)
                count += 1

        return f"Synced {count} nodes."

if __name__ == "__main__":
    # Test run
    syncer = GraphSync()
    syncer.sync_all()
