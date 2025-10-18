#!/usr/bin/env python3
"""
Clean up auto-startup files
Removes auto-startup related test files since auto-startup is disabled
"""

import os
import glob

def cleanup_auto_startup_files():
    """Clean up auto-startup related files"""
    print("🧹 Cleaning up auto-startup files")
    print("=" * 40)
    
    # List of auto-startup related files to remove
    files_to_remove = [
        "fix_session_broker.py",
        "test_auto_startup.py", 
        "configure_auto_startup.py",
        "test_session_persistence.py",
        "diagnose_broker_auth.py",
        "fix_rate_limit_broker.py",
        "comprehensive_session_fix.py",
        "maintain_session.py",
        "debug_session.py",
        "final_solution.py",
        "test_corrected_flow.py",
        "final_working_solution.py",
        "AUTO_STARTUP_README.md",
        "reset_and_test_autostartup.py",
        "quick_test_autostartup.py"
    ]
    
    removed_count = 0
    for filename in files_to_remove:
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"✅ Removed: {filename}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Failed to remove {filename}: {e}")
        else:
            print(f"⚠️ Not found: {filename}")
    
    print(f"\n📋 Summary:")
    print(f"✅ Removed {removed_count} auto-startup related files")
    print("✅ Auto-startup functionality disabled in app.py")
    print("✅ Auto-startup variables commented out in .env")
    print("✅ Auto-startup documentation updated in .sample.env")
    
    print(f"\n🎯 Auto-startup cleanup completed!")
    print("The server will now start without attempting automatic login.")

def main():
    """Main function"""
    print("🚀 Auto-Startup Cleanup")
    print("=" * 30)
    
    cleanup_auto_startup_files()

if __name__ == "__main__":
    main()
