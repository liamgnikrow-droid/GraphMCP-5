import os
import yaml
import glob

def audit_file_links():
    base_dir = "/Users/yuri/Documents/PROJECTS/AI-Infrastructure/GraphMCP-5/Graph_Export/6_Code/Files"
    if not os.path.exists(base_dir):
        # Fallback for Docker path if running inside container
        base_dir = "/workspace/Graph_Export/6_Code/Files"
        if not os.path.exists(base_dir):
             print(f"❌ Directory not found: {base_dir}")
             return

    print(f"🔍 Auditing Files in: {base_dir}")
    
    files = glob.glob(os.path.join(base_dir, "*.md"))
    total = len(files)
    linked = 0
    orphans = []
    junk_orphans = [] # logs, json, etc
    code_orphans = [] # py, js, etc

    for fpath in files:
        fname = os.path.basename(fpath)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse Frontmatter
        try:
            if content.startswith("---"):
                fm_end = content.find("---", 3)
                if fm_end > 0:
                    fm_str = content[3:fm_end]
                    data = yaml.safe_load(fm_str)
                    
                    # Check for relationships
                    has_implements = 'implements' in data and data['implements']
                    # We might also consider depends-on or decomposes as "links", but for Code->Req, user wants Implements.
                    
                    if has_implements:
                        linked += 1
                    else:
                        # Classify orphan
                        if fname.lower().endswith("log.md") or fname.lower().endswith("json.md") or fname.lower().endswith("txt.md") or fname.lower().startswith("file-md_"):
                            junk_orphans.append(fname)
                        else:
                            code_orphans.append(fname)
        except Exception as e:
            print(f"⚠️ Error parsing {fname}: {e}")

    print(f"\n📊 AUDIT RESULT:")
    print(f"   Total Files: {total}")
    print(f"   Linked: {linked}")
    print(f"   Orphaned: {total - linked} ({(total - linked)/total*100:.1f}%)")
    
    print(f"\n🗑️  'Junk' Orphans (Logs, JSON, Docs): {len(junk_orphans)}")
    for f in junk_orphans[:10]:
        print(f"   - {f}")
    if len(junk_orphans) > 10: print(f"     ... and {len(junk_orphans)-10} more")

    print(f"\n⚠️  'Code' Orphans (Scripts, Source): {len(code_orphans)}")
    for f in code_orphans:
        print(f"   - {f}")

if __name__ == "__main__":
    audit_file_links()
