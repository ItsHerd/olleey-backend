#!/usr/bin/env python3
"""
One-command migration script
Replaces all Firestore imports with Supabase imports in backend
"""

import os
import re
from pathlib import Path

# Files to migrate
ROUTER_FILES = [
    'routers/videos.py',
    'routers/jobs.py',
    'routers/channels.py',
    'routers/projects.py',
    'routers/dashboard.py',
    'routers/localization.py',
]

def migrate_file(filepath: str):
    """Migrate a single file from Firestore to Supabase."""

    if not os.path.exists(filepath):
        print(f"⏭️  Skipping {filepath} (not found)")
        return

    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content

    # Replace imports
    content = content.replace(
        'from services.firestore import firestore_service, firestore_admin',
        'from services.supabase_db import supabase_service'
    )
    content = content.replace(
        'from services.firestore import firestore_service',
        'from services.supabase_db import supabase_service'
    )

    # Replace service calls - these have the same interface!
    # No changes needed for most calls since we kept the same method names

    # firestore_admin.firestore.SERVER_TIMESTAMP → datetime.now().isoformat()
    content = content.replace(
        'firestore_admin.firestore.SERVER_TIMESTAMP',
        'datetime.now(timezone.utc).isoformat()'
    )

    # Add datetime import if not present and we're using it
    if 'datetime.now(timezone.utc)' in content and 'from datetime import' not in content:
        # Add after other imports
        import_section = content.split('\n\n')[0]
        content = content.replace(
            import_section,
            import_section + '\nfrom datetime import datetime, timezone'
        )

    if content != original_content:
        # Backup original
        backup_path = filepath + '.firestore.backup'
        with open(backup_path, 'w') as f:
            f.write(original_content)

        # Write new content
        with open(filepath, 'w') as f:
            f.write(content)

        print(f"✅ Migrated {filepath}")
        print(f"   Backup saved to {backup_path}")
    else:
        print(f"⏭️  No changes needed for {filepath}")

def main():
    print("=" * 60)
    print("🚀 FIRESTORE → SUPABASE MIGRATION")
    print("=" * 60)
    print()
    print("This script will:")
    print("1. Backup original files (.firestore.backup)")
    print("2. Replace Firestore imports with Supabase imports")
    print("3. Update timestamp handling")
    print()

    for filepath in ROUTER_FILES:
        migrate_file(filepath)

    print()
    print("=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Test the API endpoints")
    print("2. If issues, restore from .firestore.backup files")
    print("3. Run: python3 -m pytest tests/ (if you have tests)")
    print()
    print("To rollback:")
    print("  for f in routers/*.backup; do mv $f ${f%.firestore.backup}; done")

if __name__ == "__main__":
    main()
