-- Normalize status constraints so cancellation and pipeline stages are valid.
-- Idempotent and resilient to unknown prior constraint names.

-- 1) processing_jobs.status
DO $$
DECLARE c RECORD;
BEGIN
  FOR c IN
    SELECT con.conname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'public'
      AND rel.relname = 'processing_jobs'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE public.processing_jobs DROP CONSTRAINT IF EXISTS %I', c.conname);
  END LOOP;
END $$;

ALTER TABLE public.processing_jobs
  ADD CONSTRAINT processing_jobs_status_check
  CHECK (status::text = ANY (ARRAY[
    'pending'::character varying,
    'queued'::character varying,
    'downloading'::character varying,
    'transcribing'::character varying,
    'translating'::character varying,
    'voice_cloning'::character varying,
    'dubbing'::character varying,
    'lip_sync'::character varying,
    'syncing'::character varying,
    'assembling'::character varying,
    'processing'::character varying,
    'waiting_approval'::character varying,
    'uploading'::character varying,
    'ready'::character varying,
    'completed'::character varying,
    'failed'::character varying,
    'cancelled'::character varying
  ]::text[]));

-- 2) localized_videos.status
DO $$
DECLARE c RECORD;
BEGIN
  FOR c IN
    SELECT con.conname
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
    WHERE nsp.nspname = 'public'
      AND rel.relname = 'localized_videos'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%status%'
  LOOP
    EXECUTE format('ALTER TABLE public.localized_videos DROP CONSTRAINT IF EXISTS %I', c.conname);
  END LOOP;
END $$;

ALTER TABLE public.localized_videos
  ADD CONSTRAINT localized_videos_status_check
  CHECK (status::text = ANY (ARRAY[
    'not-started'::character varying,
    'queued'::character varying,
    'processing'::character varying,
    'waiting_approval'::character varying,
    'draft'::character varying,
    'live'::character varying,
    'published'::character varying,
    'failed'::character varying,
    'cancelled'::character varying
  ]::text[]));

