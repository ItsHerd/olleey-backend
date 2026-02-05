#!/bin/bash
# Quick setup script for S3 integration

echo "=================================================="
echo "  AWS S3 Integration Setup"
echo "=================================================="
echo ""

# Check if boto3 is installed
echo "1. Checking dependencies..."
python3 -c "import boto3" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "   ❌ boto3 not installed"
    echo "   Installing boto3..."
    pip3 install boto3 botocore
    if [ $? -ne 0 ]; then
        echo "   ❌ Failed to install boto3"
        exit 1
    fi
    echo "   ✅ boto3 installed"
else
    echo "   ✅ boto3 already installed"
fi

echo ""
echo "2. Checking configuration..."

# Check if .env has S3 configuration
if grep -q "AWS_S3_BUCKET" .env 2>/dev/null; then
    echo "   ✅ S3 configuration found in .env"
else
    echo "   ⚠️  S3 configuration not found in .env"
    echo ""
    echo "   Add these lines to your .env file:"
    echo ""
    cat .env.s3.example
    echo ""
    echo "   Then run this script again."
    exit 1
fi

echo ""
echo "3. Testing S3 connection..."
python3 scripts/test_s3_storage.py --check-only 2>/dev/null

echo ""
echo "=================================================="
echo "  Setup Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Review S3_INTEGRATION.md for detailed documentation"
echo "  2. Test S3: python3 scripts/test_s3_storage.py"
echo "  3. Enable S3: Set STORAGE_TYPE=s3 in .env"
echo "  4. Migrate files: python3 scripts/migrate_to_s3.py"
echo ""
