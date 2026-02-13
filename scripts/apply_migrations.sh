#!/bin/bash

# Script to apply database migrations to Supabase
# Usage: ./apply_migrations.sh [migration_file]

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
MIGRATIONS_DIR="$SCRIPT_DIR/../migrations"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Olleey Database Migration Tool ===${NC}\n"

# Check if .env file exists
if [ ! -f "$SCRIPT_DIR/../.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create a .env file with SUPABASE_URL and SUPABASE_SERVICE_KEY"
    exit 1
fi

# Load environment variables
source "$SCRIPT_DIR/../.env"

if [ -z "$SUPABASE_URL" ] || [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo -e "${RED}Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not set${NC}"
    echo "Please add these to your .env file"
    exit 1
fi

# Extract database connection details from Supabase URL
PROJECT_REF=$(echo $SUPABASE_URL | sed -E 's/https:\/\/([^.]+).*/\1/')
DB_HOST="db.${PROJECT_REF}.supabase.co"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="postgres"

echo -e "${YELLOW}Supabase Project:${NC} $PROJECT_REF"
echo -e "${YELLOW}Database Host:${NC} $DB_HOST"
echo ""

# Check if psql is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed${NC}"
    echo "Please install PostgreSQL client:"
    echo "  macOS: brew install postgresql"
    echo "  Ubuntu: sudo apt-get install postgresql-client"
    echo "  Or use Supabase Dashboard SQL Editor"
    exit 1
fi

# Function to apply a migration
apply_migration() {
    local migration_file=$1
    local migration_name=$(basename "$migration_file")

    echo -e "${YELLOW}Applying migration:${NC} $migration_name"

    # Note: You'll need to enter your database password when prompted
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -f "$migration_file" \
        --echo-errors \
        --single-transaction

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Migration applied successfully${NC}\n"
    else
        echo -e "${RED}✗ Migration failed${NC}\n"
        exit 1
    fi
}

# If specific migration file provided, apply only that
if [ ! -z "$1" ]; then
    migration_file="$MIGRATIONS_DIR/$1"
    if [ ! -f "$migration_file" ]; then
        echo -e "${RED}Error: Migration file not found: $migration_file${NC}"
        exit 1
    fi
    apply_migration "$migration_file"
else
    # Apply all migrations in order
    echo -e "${YELLOW}Applying all migrations in order...${NC}\n"

    for migration in "$MIGRATIONS_DIR"/*.sql; do
        if [ -f "$migration" ]; then
            apply_migration "$migration"
        fi
    done
fi

echo -e "${GREEN}=== All migrations applied successfully ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Verify tables in Supabase Dashboard"
echo "  2. Update supabase_db.py service to use new fields"
echo "  3. Update dubbing.py to store data in detail tables"
