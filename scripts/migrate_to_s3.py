"""
Migration script to move existing local storage files to S3.
Use this when transitioning from local storage to S3.
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.s3_storage import S3StorageService, S3_AVAILABLE
from services.storage import StorageService
from config import settings


class StorageMigration:
    """Handle migration of files from local to S3 storage."""
    
    def __init__(self, dry_run: bool = True):
        """
        Initialize migration.
        
        Args:
            dry_run: If True, only simulate migration without actual uploads
        """
        self.dry_run = dry_run
        self.local_storage = StorageService()
        
        if not S3_AVAILABLE:
            raise ImportError("boto3 not installed. Install with: pip install boto3")
        
        self.s3_storage = S3StorageService(
            bucket_name=settings.aws_s3_bucket,
            region=settings.aws_region
        )
        
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def find_local_files(self) -> List[Tuple[str, str]]:
        """
        Find all files in local storage.
        
        Returns:
            List of (absolute_path, relative_path) tuples
        """
        files = []
        storage_dir = Path(self.local_storage.storage_dir)
        
        if not storage_dir.exists():
            print(f"⚠️  Local storage directory not found: {storage_dir}")
            return files
        
        for file_path in storage_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(storage_dir)
                files.append((str(file_path), str(relative_path)))
        
        return files
    
    async def migrate_file(self, local_path: str, relative_path: str) -> bool:
        """
        Migrate a single file from local to S3.
        
        Args:
            local_path: Absolute path to local file
            relative_path: Relative path in storage structure
            
        Returns:
            bool: True if successful
        """
        try:
            # Parse path structure: videos/{user_id}/{job_id}/{language_code}/{filename}
            parts = Path(relative_path).parts
            
            if len(parts) < 4 or parts[0] != 'videos':
                # Not a standard video path, upload to misc
                s3_key = f"migrated/{relative_path}"
            else:
                # Standard video path
                s3_key = relative_path
            
            if self.dry_run:
                print(f"  [DRY RUN] Would upload: {local_path} -> s3://{self.s3_storage.bucket_name}/{s3_key}")
                return True
            
            # Upload to S3
            filename = os.path.basename(local_path)
            content_type = self.s3_storage._get_content_type(filename)
            
            self.s3_storage.s3_client.upload_file(
                local_path,
                self.s3_storage.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            print(f"  ✅ Uploaded: {s3_key}")
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to migrate {local_path}: {e}")
            return False
    
    async def migrate_all(self, delete_after: bool = False):
        """
        Migrate all local files to S3.
        
        Args:
            delete_after: If True, delete local files after successful upload
        """
        print("=" * 70)
        print("Storage Migration: Local → S3")
        print("=" * 70)
        print(f"Source: {self.local_storage.storage_dir}")
        print(f"Destination: s3://{self.s3_storage.bucket_name}")
        print(f"Mode: {'DRY RUN (simulation only)' if self.dry_run else 'LIVE MIGRATION'}")
        print(f"Delete after: {delete_after}")
        print("=" * 70)
        
        # Find all files
        print("\n📂 Scanning local storage...")
        files = self.find_local_files()
        self.stats['total'] = len(files)
        
        if not files:
            print("   No files found to migrate")
            return
        
        print(f"   Found {len(files)} files\n")
        
        # Migrate each file
        print("🚀 Starting migration...\n")
        
        for local_path, relative_path in files:
            file_size = os.path.getsize(local_path)
            print(f"📁 {relative_path} ({file_size:,} bytes)")
            
            success = await self.migrate_file(local_path, relative_path)
            
            if success:
                self.stats['success'] += 1
                
                # Delete local file if requested and not dry run
                if delete_after and not self.dry_run:
                    try:
                        os.remove(local_path)
                        print(f"  🗑️  Deleted local file")
                    except Exception as e:
                        print(f"  ⚠️  Failed to delete local file: {e}")
            else:
                self.stats['failed'] += 1
        
        # Print summary
        print("\n" + "=" * 70)
        print("Migration Summary")
        print("=" * 70)
        print(f"Total files: {self.stats['total']}")
        print(f"✅ Successful: {self.stats['success']}")
        print(f"❌ Failed: {self.stats['failed']}")
        print(f"⏭️  Skipped: {self.stats['skipped']}")
        print("=" * 70)
        
        if self.dry_run:
            print("\n💡 This was a DRY RUN. No files were actually uploaded.")
            print("   To perform the actual migration, run with --live flag")
        elif delete_after:
            print("\n⚠️  Local files have been deleted. Verify S3 files before clearing cache.")
        else:
            print("\n💡 Local files preserved. You can delete them manually after verification.")


async def main():
    """Run migration with command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate local storage files to S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (simulate migration)
  python scripts/migrate_to_s3.py

  # Live migration (keep local files)
  python scripts/migrate_to_s3.py --live

  # Live migration (delete local files after upload)
  python scripts/migrate_to_s3.py --live --delete

  # Check configuration
  python scripts/migrate_to_s3.py --check-config
        """
    )
    
    parser.add_argument(
        '--live',
        action='store_true',
        help='Perform actual migration (default is dry run)'
    )
    
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete local files after successful upload'
    )
    
    parser.add_argument(
        '--check-config',
        action='store_true',
        help='Check S3 configuration and exit'
    )
    
    args = parser.parse_args()
    
    # Check configuration
    if args.check_config or not getattr(settings, 'aws_s3_bucket', None):
        print("\n📋 S3 Configuration:")
        print(f"   Bucket: {getattr(settings, 'aws_s3_bucket', 'Not configured')}")
        print(f"   Region: {getattr(settings, 'aws_region', 'Not configured')}")
        print(f"   Access Key: {'*' * 16 if getattr(settings, 'aws_access_key_id', None) else 'Not configured'}")
        
        if not getattr(settings, 'aws_s3_bucket', None):
            print("\n❌ S3 bucket not configured. Set AWS_S3_BUCKET in .env")
            return 1
        
        if args.check_config:
            return 0
    
    # Confirm live migration
    if args.live:
        print("\n⚠️  WARNING: This will perform a LIVE migration to S3!")
        if args.delete:
            print("⚠️  Local files will be DELETED after upload!")
        
        response = input("\nAre you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Migration cancelled")
            return 0
    
    # Run migration
    try:
        migration = StorageMigration(dry_run=not args.live)
        await migration.migrate_all(delete_after=args.delete)
        return 0
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
