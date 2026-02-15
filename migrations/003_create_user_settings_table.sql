-- Create user_settings table used by /settings endpoints.
-- Idempotent: safe to run multiple times.

CREATE TABLE IF NOT EXISTS public.user_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL UNIQUE,
  theme text NOT NULL DEFAULT 'dark' CHECK (theme IN ('light', 'dark')),
  timezone text NOT NULL DEFAULT 'America/Los_Angeles',
  notifications jsonb NOT NULL DEFAULT '{"email_notifications": true, "distribution_updates": true, "error_alerts": true}'::jsonb,
  auto_approve_jobs boolean NOT NULL DEFAULT false,
  detected_upload_window text NOT NULL DEFAULT 'last_7_days' CHECK (detected_upload_window IN ('last_1_day', 'last_7_days', 'last_31_days')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON public.user_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_settings_updated_at ON public.user_settings(updated_at DESC);

