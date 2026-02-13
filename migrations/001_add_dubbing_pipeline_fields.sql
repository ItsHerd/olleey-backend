-- Migration: Add ElevenLabs Dubbing Pipeline Fields to processing_jobs
-- Date: 2026-02-11
-- Purpose: Enhance processing_jobs table to track dubbing pipeline details

-- Add ElevenLabs-specific fields
ALTER TABLE public.processing_jobs
  ADD COLUMN IF NOT EXISTS elevenlabs_job_id VARCHAR(255),
  ADD COLUMN IF NOT EXISTS source_language VARCHAR(10) DEFAULT 'auto',
  ADD COLUMN IF NOT EXISTS estimated_cost DECIMAL(10, 2) DEFAULT 0,
  ADD COLUMN IF NOT EXISTS actual_cost DECIMAL(10, 2),
  ADD COLUMN IF NOT EXISTS cost_breakdown JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS current_stage VARCHAR(50),
  ADD COLUMN IF NOT EXISTS dubbing_metadata JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS processing_time_seconds INTEGER;

-- Add index for ElevenLabs job ID lookups
CREATE INDEX IF NOT EXISTS idx_processing_jobs_elevenlabs_id
  ON public.processing_jobs(elevenlabs_job_id);

-- Add index for user_id and status for faster queries
CREATE INDEX IF NOT EXISTS idx_processing_jobs_user_status
  ON public.processing_jobs(user_id, status);

-- Add index for created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_processing_jobs_created_at
  ON public.processing_jobs(created_at DESC);

-- Update existing status constraint to include new stages
ALTER TABLE public.processing_jobs
  DROP CONSTRAINT IF EXISTS processing_jobs_status_check;

ALTER TABLE public.processing_jobs
  ADD CONSTRAINT processing_jobs_status_check
  CHECK (status::text = ANY (ARRAY[
    'pending'::character varying,
    'downloading'::character varying,
    'transcribing'::character varying,
    'translating'::character varying,
    'dubbing'::character varying,
    'syncing'::character varying,
    'assembling'::character varying,
    'processing'::character varying,
    'waiting_approval'::character varying,
    'uploading'::character varying,
    'completed'::character varying,
    'failed'::character varying,
    'cancelled'::character varying
  ]::text[]));

-- Add comment to table
COMMENT ON TABLE public.processing_jobs IS 'Tracks video dubbing pipeline jobs including transcription, translation, dubbing, and lip sync';

-- Add comments to new columns
COMMENT ON COLUMN public.processing_jobs.elevenlabs_job_id IS 'ElevenLabs API job ID for tracking dubbing tasks';
COMMENT ON COLUMN public.processing_jobs.source_language IS 'Source video language code (e.g., en, es) or auto for auto-detection';
COMMENT ON COLUMN public.processing_jobs.estimated_cost IS 'Estimated cost in USD before job execution';
COMMENT ON COLUMN public.processing_jobs.actual_cost IS 'Actual cost in USD after job completion';
COMMENT ON COLUMN public.processing_jobs.cost_breakdown IS 'JSON object with cost details: {dubbing: X, lipsync: Y, total: Z}';
COMMENT ON COLUMN public.processing_jobs.current_stage IS 'Current pipeline stage: transcribing, translating, dubbing, syncing, etc.';
COMMENT ON COLUMN public.processing_jobs.dubbing_metadata IS 'Provider-specific metadata (ElevenLabs settings, SyncLabs parameters, etc.)';
COMMENT ON COLUMN public.processing_jobs.processing_time_seconds IS 'Total processing time in seconds';
