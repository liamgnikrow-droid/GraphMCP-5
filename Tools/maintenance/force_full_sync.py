import os
import sys

# Setup environment to direct to Tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Tools.graph_sync import GraphSync
    from Tools.db_config import get_driver, close_driver, WORKSPACE_ROOT
except ImportError:
    # Fallback if run directly from Tools/maintenance
    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Tools"))
    from graph_sync import GraphSync
    from db_config import get_driver, close_driver, WORKSPACE_ROOT

def force_full_sync():
    print("🚀 Starting FORCE FULL SYNC (Direct Mode)...")
    
    syncer = GraphSync()
    
    # Use sync_all which fetches all nodes from DB and rewrites files
    # This bypasses the server API logic completely
    result = syncer.sync_all()
    
    print(f"\n✅ Sync Complete.")
    print(f"   Processed: {result.get('processed', 0)}")
    print(f"   Updated: {result.get('updated', 0)}")
    print(f"   Errors: {len(result.get('errors', []))}")
    
    if result.get('errors'):
        print("\n⚠️ Errors Sample:")
        for e in result['errors'][:5]:
            print(f"   - {e}")

    syncer.close()

if __name__ == "__main__":
    force_full_sync()
