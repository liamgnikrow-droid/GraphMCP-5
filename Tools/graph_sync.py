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
    "SpecItem": "2_Specs/Items",
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

        # Content / Description Handling
        # PRIORITY: Content (Full Body) > Description (Metadata)
        # If Content exists, it usually subsumes the Description (as per import logic).
        # We render Content under the "## Description" header.
        
        content = props.get('content')
        
        if content:
            body.append("## Description")
            # normalization check for legacy title
            check_content = content.strip()
            if check_content.startswith(f"# {title}"):
                 lines = check_content.split('\n')
                 content = "\n".join(lines[1:]).strip()
            
            body.append(content)
            body.append("")
        elif description:
            # Fallback if no content but description exists
            body.append("## Description")
            body.append(description)
            body.append("")
         
        return "\n".join(fm_lines + body)

    def extract_body_from_markdown(self, file_path: str) -> str:
        """
        Extracts the body (text after frontmatter) from an existing markdown file.
        ROBUST VERSION: Strips Frontmatter, IDs, Headers, and Context blocks to prevent duplication.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. Remove Frontmatter (possibly multiple)
            # Find the LAST instance of "---\n" followed by content
            # We assume frontmatter is at the top.
            if content.startswith("---"):
                parts = content.split("---")
                if len(parts) >= 3:
                     # parts[0] is empty, parts[1] is FM, parts[2:] is Body (potentially with more junk)
                     # We take the LAST part as the body candidate if multiple FMs exist due to bugs
                     content = parts[-1].strip()

            # DUPLICATION FIX: Strip conflict markers
            conflict_marker = "## 🔄 SYNC CONFLICT: Database Version"
            if conflict_marker in content:
                content = content.split(conflict_marker)[0].strip()

            lines = content.split('\n')
            clean_lines = []
            
            # 2. State Machine to skip "System Generated" headers
            # We want to skip:
            # - Metadata blocks like "> [!abstract] ..."
            # - Primary Titles like "# Title" (because we regenerate them)
            # - Empty lines at start
            
            skipping_metadata = True
            
            for line in lines:
                sline = line.strip()
                
                if skipping_metadata:
                    # Skip empty lines at start
                    if not sline:
                        continue
                        
                    # Skip Title (H1)
                    if sline.startswith("# "):
                        continue
                        
                    # Skip Context/Status blocks
                    if sline.startswith("> "):
                        continue
                    
                    # Skip Bold Labels
                    if sline.startswith("**ID:**") or sline.startswith("**Type:**") or sline.startswith("**Status:**"):
                        continue
                        
                    # Skip "## Description" or "## Content" headers
                    if sline == "## Description" or sline == "## Content":
                        continue
                        
                    # If we reach here, we found the first line of real content!
                    skipping_metadata = False
                    clean_lines.append(line)
                else:
                    # BODY CLEANUP: If we see ANOTHER "## Description", it's a duplication bug. Skip it.
                    if sline == "## Description" or sline == "## Content":
                        continue

                    clean_lines.append(line)
            
            return "\n".join(clean_lines).strip()
            
        except Exception as e:
            print(f"⚠️ Error extracting body from {file_path}: {e}")
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
        
        # SKIP SYSTEM NODES (Clean Slate Architecture)
        if node_type in ['Constraint', 'Action', 'NodeType']:
            # print(f"ℹ️ GraphSync: Skipping system node {uid} (Type: {node_type})")
            return None

        subfolder = TYPE_TO_FOLDER.get(node_type, "9_Unclassified")
        filename = f"{uid}.md"
        safe_filename = filename.replace("/", "_").replace("\\", "_")

        dir_path = os.path.join(WORKSPACE_ROOT, "Graph_Export", subfolder)
        os.makedirs(dir_path, exist_ok=True)

        file_path = os.path.join(dir_path, safe_filename)
        
        # === CONTENT MERGE STRATEGY ===
        # Priority 1: Content from Neo4j (if exists)
        # Priority 2: Existing Body from File (if Neo4j content is empty)
        
        db_content = node_data['props'].get('content', "").strip()
        existing_body = ""
        conflict_detected = False
        
        if os.path.exists(file_path):
             existing_body = self.extract_body_from_markdown(file_path).strip()
        
        # NORMALIZATION:
        # Collapse multiple newlines to single newline for comparison purposes only
        # This handles the case where DB has "A\n\nB" and file has "A\nB" or vice versa
        def normalize(text):
            return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

        db_norm = normalize(db_content)
        file_norm = normalize(existing_body)

        if db_content and existing_body and db_norm != file_norm:
            # CONFLICT DETECTED
            print(f"⚠️ Conflict details for {uid}:")
            # print(f"DB len: {len(db_content)} vs File len: {len(existing_body)}")
            # print(f"DB norm: {len(db_norm)} vs File norm: {len(file_norm)}")
            
            conflict_detected = True
            node_data['props']['content'] = existing_body # Render with local content
            
        elif existing_body and not db_content:
            # DB is empty, preserve file
            node_data['props']['content'] = existing_body
        
        # Render
        content = self.render_markdown(node_data)
        
        # Handle Conflict Append
        if conflict_detected:
            content += "\n\n"
            content += "## 🔄 SYNC CONFLICT: Database Version\n"
            content += "> [!warning] Database content differs from local file.\n"
            content += "> Below is the version from Neo4j Graph:\n\n"
            content += db_content
            
            # Create BUG node in Graph
            bug_uid = f"BUG-Conflict-{uid}"
            print(f"⚠️  CONFLICT detected for {uid}. Creating {bug_uid}...")
            
            bug_query = """
            MATCH (n {uid: $uid})
            MERGE (b:Bug {uid: $bug_uid})
            SET b.title = 'Sync Conflict: ' + $uid,
                b.description = 'Content mismatch between Obsidian (Local) and Neo4j (DB). Please resolve in file.',
                b.status = 'Open',
                b.created_at = datetime()
            MERGE (b)-[:RELATES_TO]->(n)
            """
            try:
                drv = self.get_driver()
                drv.execute_query(bug_query, {"uid": uid, "bug_uid": bug_uid}, database_="neo4j")
                print(f"🐛 Created Bug: {bug_uid}")
            except Exception as e:
                print(f"❌ Failed to create conflict bug: {e}")

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
