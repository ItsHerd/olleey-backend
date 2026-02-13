# Database Migrations

This directory contains SQL migrations for the Olleey dubbing platform database schema.

## Overview

The database uses Supabase (PostgreSQL) and tracks the complete dubbing pipeline workflow.

## Migration Files

### 001_add_dubbing_pipeline_fields.sql
**Purpose**: Enhance the `processing_jobs` table with dubbing pipeline fields

**Changes**:
- Adds `elevenlabs_job_id` for tracking ElevenLabs API jobs
- Adds `source_language` for source video language
- Adds `estimated_cost` and `actual_cost` for cost tracking
- Adds `cost_breakdown` (JSONB) for detailed cost analysis
- Adds `current_stage` for pipeline stage tracking
- Adds `dubbing_metadata` (JSONB) for provider-specific data
- Adds `processing_time_seconds` for performance metrics
- Updates status constraint to include new stages
- Adds indexes for faster queries

**New Status Values**:
- `downloading`, `transcribing`, `translating`, `dubbing`, `syncing`, `assembling`, `uploading`, `cancelled`

---

### 002_create_dubbing_detail_tables.sql
**Purpose**: Create detailed tracking tables for dubbing pipeline stages

**New Tables**:

1. **`transcripts`** - Stores video transcriptions
   - Tracks transcript text with word-level timestamps
   - Links to processing job and video
   - Includes confidence scores and provider info

2. **`translations`** - Stores translated text
   - One record per job + target language
   - Links to source transcript
   - Tracks translation confidence and review status

3. **`dubbed_audio`** - Stores dubbed audio files
   - One record per job + language
   - Tracks audio URL, duration, format
   - Stores voice settings and segments

4. **`lip_sync_jobs`** - Tracks SyncLabs processing
   - One record per job + language
   - Stores SyncLabs job ID and status
   - Tracks quality scores and processing time

**Updates**:
- Enhances `localized_videos` table with foreign keys to new tables

---

## How to Apply Migrations

### Option 1: Supabase Dashboard (Recommended)

1. Go to your Supabase project: https://supabase.com/dashboard
2. Navigate to **SQL Editor**
3. Create a new query
4. Copy and paste the contents of each migration file in order
5. Run each migration

### Option 2: Using psql

```bash
# Connect to your Supabase database
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Apply migrations in order
\i migrations/001_add_dubbing_pipeline_fields.sql
\i migrations/002_create_dubbing_detail_tables.sql
```

### Option 3: Using Supabase CLI

```bash
# Install Supabase CLI if not already installed
npm install -g supabase

# Link to your project
supabase link --project-ref [YOUR-PROJECT-REF]

# Apply migrations
supabase db push
```

---

## Verification

After applying migrations, verify the changes:

```sql
-- Check new columns in processing_jobs
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'processing_jobs'
  AND column_name IN ('elevenlabs_job_id', 'estimated_cost', 'current_stage');

-- Check new tables exist
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN ('transcripts', 'translations', 'dubbed_audio', 'lip_sync_jobs');

-- Check indexes
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('processing_jobs', 'transcripts', 'translations', 'dubbed_audio', 'lip_sync_jobs');
```

---

## Rollback

If you need to rollback the migrations:

```sql
-- Rollback 002 (remove detail tables)
DROP TABLE IF EXISTS public.lip_sync_jobs CASCADE;
DROP TABLE IF EXISTS public.dubbed_audio CASCADE;
DROP TABLE IF EXISTS public.translations CASCADE;
DROP TABLE IF EXISTS public.transcripts CASCADE;

ALTER TABLE public.localized_videos
  DROP COLUMN IF EXISTS transcript_id,
  DROP COLUMN IF EXISTS translation_id,
  DROP COLUMN IF EXISTS dubbed_audio_id,
  DROP COLUMN IF EXISTS lip_sync_job_id,
  DROP COLUMN IF EXISTS dubbed_audio_url,
  DROP COLUMN IF EXISTS storage_url;

-- Rollback 001 (remove dubbing pipeline fields)
DROP INDEX IF EXISTS idx_processing_jobs_elevenlabs_id;
DROP INDEX IF EXISTS idx_processing_jobs_user_status;
DROP INDEX IF EXISTS idx_processing_jobs_created_at;

ALTER TABLE public.processing_jobs
  DROP COLUMN IF EXISTS elevenlabs_job_id,
  DROP COLUMN IF EXISTS source_language,
  DROP COLUMN IF EXISTS estimated_cost,
  DROP COLUMN IF EXISTS actual_cost,
  DROP COLUMN IF EXISTS cost_breakdown,
  DROP COLUMN IF EXISTS current_stage,
  DROP COLUMN IF EXISTS dubbing_metadata,
  DROP COLUMN IF EXISTS processing_time_seconds;
```

---

## Schema Diagram

```
┌──────────────────────┐
│  processing_jobs     │ (Enhanced with pipeline fields)
│  ├─ id               │
│  ├─ elevenlabs_job_id│ (NEW)
│  ├─ source_language  │ (NEW)
│  ├─ estimated_cost   │ (NEW)
│  ├─ cost_breakdown   │ (NEW)
│  └─ current_stage    │ (NEW)
└──────────┬───────────┘
           │
           ├─────────────────────────────────┐
           │                                 │
           ▼                                 ▼
┌──────────────────────┐          ┌──────────────────────┐
│  transcripts         │          │  localized_videos    │
│  ├─ job_id (FK)      │          │  ├─ job_id (FK)      │
│  ├─ transcript_text  │          │  ├─ transcript_id    │
│  └─ word_timestamps  │          │  ├─ translation_id   │
└──────────┬───────────┘          │  ├─ dubbed_audio_id  │
           │                      │  └─ lip_sync_job_id  │
           ▼                      └──────────────────────┘
┌──────────────────────┐
│  translations        │
│  ├─ transcript_id    │
│  ├─ job_id (FK)      │
│  ├─ target_language  │
│  └─ translated_text  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  dubbed_audio        │
│  ├─ translation_id   │
│  ├─ job_id (FK)      │
│  ├─ audio_url        │
│  └─ voice_settings   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  lip_sync_jobs       │
│  ├─ job_id (FK)      │
│  ├─ dubbed_audio_id  │
│  ├─ synclabs_job_id  │
│  └─ output_video_url │
└──────────────────────┘
```

---

## Next Steps

After applying migrations:

1. ✅ Update `supabase_db.py` service to use new fields
2. ✅ Update `dubbing.py` pipeline to store data in detail tables
3. ✅ Create API endpoints for transcript/translation viewing
4. ✅ Add frontend UI for reviewing transcripts/translations

---

## Notes

- All migrations are idempotent (safe to run multiple times)
- Foreign keys use `ON DELETE CASCADE` for automatic cleanup
- Indexes are optimized for common query patterns
- JSONB fields allow flexible metadata storage
- All tables include `created_at` and `updated_at` timestamps
