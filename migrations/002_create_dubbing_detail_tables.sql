-- Migration: Create Dubbing Pipeline Detail Tables
-- Date: 2026-02-11
-- Purpose: Create tables for transcripts, translations, and dubbed audio

-- ============================================================
-- TRANSCRIPTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.transcripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES public.processing_jobs(id) ON DELETE CASCADE,
  video_id VARCHAR(255) NOT NULL,
  user_id TEXT NOT NULL,

  -- Transcript data
  language_code VARCHAR(10) NOT NULL CHECK (language_code ~* '^[a-z]{2}$'),
  transcript_text TEXT NOT NULL,
  word_timestamps JSONB DEFAULT '[]',

  -- Metadata
  provider VARCHAR(50) DEFAULT 'elevenlabs',  -- elevenlabs, whisper, assemblyai, etc.
  confidence_score DECIMAL(3, 2),  -- 0.00 to 1.00
  duration INTEGER,  -- Duration in seconds
  status VARCHAR(50) DEFAULT 'completed' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Unique constraint: one transcript per job
  CONSTRAINT unique_transcript_per_job UNIQUE (job_id)
);

-- Indexes for transcripts
CREATE INDEX IF NOT EXISTS idx_transcripts_job_id ON public.transcripts(job_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_video_id ON public.transcripts(video_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_user_id ON public.transcripts(user_id);

COMMENT ON TABLE public.transcripts IS 'Stores video transcripts from transcription services';

-- ============================================================
-- TRANSLATIONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.translations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transcript_id UUID REFERENCES public.transcripts(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES public.processing_jobs(id) ON DELETE CASCADE,
  video_id VARCHAR(255) NOT NULL,
  user_id TEXT NOT NULL,

  -- Translation data
  source_language VARCHAR(10) NOT NULL CHECK (source_language ~* '^[a-z]{2}$'),
  target_language VARCHAR(10) NOT NULL CHECK (target_language ~* '^[a-z]{2}$'),
  translated_text TEXT NOT NULL,
  word_timestamps JSONB DEFAULT '[]',

  -- Metadata
  provider VARCHAR(50) DEFAULT 'elevenlabs',  -- elevenlabs, deepl, google, etc.
  confidence_score DECIMAL(3, 2),
  status VARCHAR(50) DEFAULT 'completed' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  reviewed BOOLEAN DEFAULT FALSE,

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Unique constraint: one translation per job + language combination
  CONSTRAINT unique_translation_per_job_language UNIQUE (job_id, target_language)
);

-- Indexes for translations
CREATE INDEX IF NOT EXISTS idx_translations_job_id ON public.translations(job_id);
CREATE INDEX IF NOT EXISTS idx_translations_transcript_id ON public.translations(transcript_id);
CREATE INDEX IF NOT EXISTS idx_translations_target_language ON public.translations(target_language);
CREATE INDEX IF NOT EXISTS idx_translations_user_id ON public.translations(user_id);

COMMENT ON TABLE public.translations IS 'Stores translated text for each target language';

-- ============================================================
-- DUBBED AUDIO TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS public.dubbed_audio (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  translation_id UUID REFERENCES public.translations(id) ON DELETE CASCADE,
  job_id UUID NOT NULL REFERENCES public.processing_jobs(id) ON DELETE CASCADE,
  language_code VARCHAR(10) NOT NULL CHECK (language_code ~* '^[a-z]{2}$'),
  user_id TEXT NOT NULL,

  -- Audio data
  audio_url TEXT NOT NULL,
  duration INTEGER,  -- Duration in seconds
  file_size INTEGER,  -- File size in bytes
  format VARCHAR(10) DEFAULT 'mp3',  -- mp3, wav, aac, etc.

  -- Voice settings
  voice_id VARCHAR(255),
  voice_name VARCHAR(255),
  voice_settings JSONB DEFAULT '{}',

  -- Audio segments (for multi-segment audio)
  segments JSONB DEFAULT '[]',

  -- Metadata
  provider VARCHAR(50) DEFAULT 'elevenlabs',
  status VARCHAR(50) DEFAULT 'completed' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Unique constraint: one dubbed audio per job + language
  CONSTRAINT unique_dubbed_audio_per_job_language UNIQUE (job_id, language_code)
);

-- Indexes for dubbed_audio
CREATE INDEX IF NOT EXISTS idx_dubbed_audio_job_id ON public.dubbed_audio(job_id);
CREATE INDEX IF NOT EXISTS idx_dubbed_audio_translation_id ON public.dubbed_audio(translation_id);
CREATE INDEX IF NOT EXISTS idx_dubbed_audio_language_code ON public.dubbed_audio(language_code);
CREATE INDEX IF NOT EXISTS idx_dubbed_audio_user_id ON public.dubbed_audio(user_id);

COMMENT ON TABLE public.dubbed_audio IS 'Stores dubbed audio files generated from translations';

-- ============================================================
-- LIP SYNC JOBS TABLE (for tracking SyncLabs jobs)
-- ============================================================
CREATE TABLE IF NOT EXISTS public.lip_sync_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID NOT NULL REFERENCES public.processing_jobs(id) ON DELETE CASCADE,
  dubbed_audio_id UUID REFERENCES public.dubbed_audio(id) ON DELETE CASCADE,
  language_code VARCHAR(10) NOT NULL CHECK (language_code ~* '^[a-z]{2}$'),
  user_id TEXT NOT NULL,

  -- SyncLabs data
  synclabs_job_id VARCHAR(255) UNIQUE,
  status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  progress INTEGER DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),

  -- URLs
  input_video_url TEXT NOT NULL,
  input_audio_url TEXT NOT NULL,
  output_video_url TEXT,

  -- Quality metrics
  quality_score DECIMAL(3, 2),
  processing_time_seconds INTEGER,

  -- Cost tracking
  cost DECIMAL(10, 2),

  -- Timestamps
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE,

  -- Unique constraint: one lip sync job per parent job + language
  CONSTRAINT unique_lipsync_per_job_language UNIQUE (job_id, language_code)
);

-- Indexes for lip_sync_jobs
CREATE INDEX IF NOT EXISTS idx_lipsync_job_id ON public.lip_sync_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_lipsync_synclabs_id ON public.lip_sync_jobs(synclabs_job_id);
CREATE INDEX IF NOT EXISTS idx_lipsync_status ON public.lip_sync_jobs(status);
CREATE INDEX IF NOT EXISTS idx_lipsync_user_id ON public.lip_sync_jobs(user_id);

COMMENT ON TABLE public.lip_sync_jobs IS 'Tracks SyncLabs lip sync processing jobs';

-- ============================================================
-- UPDATE LOCALIZED_VIDEOS TABLE
-- ============================================================
-- Add references to new tables
ALTER TABLE public.localized_videos
  ADD COLUMN IF NOT EXISTS transcript_id UUID REFERENCES public.transcripts(id),
  ADD COLUMN IF NOT EXISTS translation_id UUID REFERENCES public.translations(id),
  ADD COLUMN IF NOT EXISTS dubbed_audio_id UUID REFERENCES public.dubbed_audio(id),
  ADD COLUMN IF NOT EXISTS lip_sync_job_id UUID REFERENCES public.lip_sync_jobs(id),
  ADD COLUMN IF NOT EXISTS dubbed_audio_url TEXT,  -- For quick access
  ADD COLUMN IF NOT EXISTS storage_url TEXT;  -- For final video storage

-- Add index for dubbed audio URL lookups
CREATE INDEX IF NOT EXISTS idx_localized_videos_dubbed_audio_id
  ON public.localized_videos(dubbed_audio_id);

COMMENT ON COLUMN public.localized_videos.transcript_id IS 'Reference to transcript used for this video';
COMMENT ON COLUMN public.localized_videos.translation_id IS 'Reference to translation used for this video';
COMMENT ON COLUMN public.localized_videos.dubbed_audio_id IS 'Reference to dubbed audio used for this video';
COMMENT ON COLUMN public.localized_videos.lip_sync_job_id IS 'Reference to lip sync job for this video';
