import os
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

def hard_reset_duplicates():
    print("🧹 Starting HARD RESET of duplicates...")
    count = 0
    cleaned_count = 0
    
    # 1. Iterate all MD files
    for md_file in GRAPH_EXPORT.rglob("*.md"):
        try:
            content = md_file.read_text(encoding='utf-8')
            
            # 1. Removing Conflict Markers (Iterative until clean)
            while "## 🔄 SYNC CONFLICT: Database Version" in content:
                 content = content.split("## 🔄 SYNC CONFLICT: Database Version")[0].strip()
            
            # 2. Body Deduplication (Robust)
            # We enforce a clean structure: Header -> Body.
            # If "## Description" exists, we split by it.
            if "## Description" in content:
                parts = content.split("## Description", 1) # Split on first only
                header = parts[0]
                body_raw = parts[1]
                
                # If there were MORE descriptions, they are now inside body_raw.
                # removing them:
                body_raw = body_raw.replace("## Description", "")
                
                # STRICT DEDUPLICATION
                # We normalize lines (strip) and ensure no sequential duplicates.
                # We ALSO filter out duplicates that are separated by just empty lines.
                body_lines = body_raw.split('\n')
                unique_lines = []
                seen_lines_block = set() # Track unique lines in the current block of text
                
                for line in body_lines:
                    sline = line.strip()
                    
                    if not sline:
                        unique_lines.append(line)
                        continue
                    
                    # Heuristic: If we see the exact same non-empty line again in this file,
                    # AND it is effectively the 'main content' (long enough), it's probably duplication spam.
                    if len(sline) > 20 and sline in seen_lines_block:
                         continue
                    
                    unique_lines.append(line)
                    seen_lines_block.add(sline)
                
                body = "\n".join(unique_lines)
                content = header + "## Description" + body
                cleaned_count += 1
                
            md_file.write_text(content, encoding='utf-8')
            count += 1
        except Exception as e:
            print(f"⚠️ Error processing {md_file}: {e}")
            
    print(f"✅ Processed {count} files, cleaned {cleaned_count} files.")

    # 3. Clean DB Bugs
    driver = get_driver()
    if driver:
        with driver.session(database="neo4j") as session:
             session.run("MATCH (b:Bug) WHERE b.uid STARTS WITH 'BUG-Conflict-' DETACH DELETE b")
        print("🗑️ Deleted Conflict Bugs")
        close_driver()

if __name__ == "__main__":
    hard_reset_duplicates()
