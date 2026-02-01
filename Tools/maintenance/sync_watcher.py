import time
import os
import sys

# Add parent directory to path to import Tools explicitly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir) # Tools
sys.path.append(parent_dir)

from graph_sync import GraphSync

try:
    from db_config import WORKSPACE_ROOT
except ImportError:
    # Fallback if running from different context
    WORKSPACE_ROOT = os.path.dirname(parent_dir)

class SyncWatcher:
    def __init__(self, root_dir, poll_interval=5):
        self.root_dir = root_dir
        self.sync = GraphSync()
        self.file_cache = {} # path -> mtime
        self.poll_interval = poll_interval
        # Debounce: path -> last_change_detected_time
        self.pending_changes = {} 
        self.debounce_seconds = 2 

    def scan(self):
        """
        Scans for file changes. 
        Implements polling + simple debounce to avoid spamming DB on partial writes.
        """
        # 1. Discovery Phase
        current_state = {}
        for root, dirs, files in os.walk(self.root_dir):
            # Skip hidden folders?
            if "/." in root: continue
            
            for file in files:
                if not file.endswith(".md"): continue
                
                path = os.path.join(root, file)
                try:
                    mtime = os.path.getmtime(path)
                    current_state[path] = mtime
                    
                    last_mtime = self.file_cache.get(path)
                    
                    if last_mtime is None:
                        # Init cache
                        self.file_cache[path] = mtime
                    elif mtime > last_mtime:
                        # Change detected!
                        now = time.time()
                        print(f"📝 Detected change in {file} (mtime: {mtime})")
                        self.pending_changes[path] = now
                        self.file_cache[path] = mtime
                        
                except Exception as e:
                    print(f"⚠️ Error accessing {path}: {e}")

        # 2. Processing Phase (Debounced)
        now = time.time()
        to_remove = []
        
        for path, detect_time in self.pending_changes.items():
            # If no new changes for N seconds, push it
            # We check if file mtime is still same as cached? 
            # Actually, scan() updates cache immediately.
            # If file changed AGAIN since detect_time, scan() would have updated pending_changes entry?
            # No, if scan updates entry, we need to defer push.
            
            # Simple logic: If we are here, we detected a change.
            # Wait until (now - detect_time) > debounce
            if now - detect_time > self.debounce_seconds:
                try:
                    self.sync.push_file_to_db(path)
                    to_remove.append(path)
                except Exception as e:
                    print(f"❌ Failed to push {path}: {e}")
                    # Don't remove, try again? Or remove to avoid loop? Remove.
                    to_remove.append(path)

        for path in to_remove:
            del self.pending_changes[path]

    def start(self):
        print(f"👀 SyncWatcher started.")
        print(f"📂 Watching: {self.root_dir}")
        print(f"⏱️  Poll Interval: {self.poll_interval}s | Debounce: {self.debounce_seconds}s")
        
        cycles = 0
        HEALTH_CHECK_CYCLES = 12 # 12 * 5s = 60s
        
        try:
            while True:
                self.scan()
                
                # Periodic DB -> Disk Sync
                if cycles % HEALTH_CHECK_CYCLES == 0:
                     # Runs efficiently? sync_all() fetches all UIDs and renders them.
                     # It relies on sync_node logic which CHECKS content diff before writing.
                     # So it shouldn't churn disk unless needed.
                     # However, sync_all processes ALL nodes. If graph grows, this loops slows down.
                     # For now, acceptable.
                     print("🏥 Running DB Health Check (Sync All)...")
                     try:
                        self.sync.sync_all()
                     except Exception as e:
                        print(f"❌ Health Check Failed: {e}")

                cycles += 1
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n🛑 Stopped SyncWatcher.")
            self.sync.close()

if __name__ == "__main__":
    target_dir = os.path.join(WORKSPACE_ROOT, "Graph_Export")
    if not os.path.exists(target_dir):
        print(f"❌ Target directory not found: {target_dir}")
        sys.exit(1)
        
    watcher = SyncWatcher(target_dir)
    watcher.start()
