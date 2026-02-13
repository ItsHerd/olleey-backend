# Data Schema Documentation

This document describes the active **Supabase/PostgreSQL** schema used by the backend and dashboard.

## Source of truth

- Runtime schema: Supabase project
- Migration files:
  - `migrations/001_add_dubbing_pipeline_fields.sql`
  - `migrations/002_create_dubbing_detail_tables.sql`
- Context dump (may lag): `olleey-web/db.sql`

## Core tables

### `users`
Stores application user metadata and OAuth tokens.

Key columns:
- `id` (uuid, primary key)
- `user_id` (text, unique, required)
- `email` (text, unique, required)
- `name`, `avatar_url`
- `access_token`, `refresh_token`, `token_expiry`
- `preferences` (jsonb), `is_active`
- `created_at`, `updated_at`

Notes:
- In app auth flow, `user_id` is expected to match Supabase auth `uid` string.

### `projects`
Logical workspace grouping for channels, videos, and jobs.

Key columns:
- `id` (uuid, primary key)
- `user_id` (text, required)
- `name` (required), `description`, `settings` (jsonb)
- `created_at`, `updated_at`, `deleted_at`

### `channels`
Language-aware publishing channels linked to a project.

Key columns:
- `id` (uuid, primary key)
- `channel_id` (text, unique)
- `user_id` (text, required)
- `project_id` (uuid, FK -> `projects.id`)
- `channel_name`
- `language_code`, `language_name`
- `is_master`, `master_channel_id`
- `thumbnail_url`, `subscriber_count`, `video_count`
- `is_paused`, `deleted_at`, timestamps

### `youtube_connections`
OAuth-level channel connection records used by distribution logic.

Key columns:
- `connection_id` (uuid/text key, used by backend as unique identifier)
- `user_id`
- `youtube_channel_id`, `youtube_channel_name`
- `channel_avatar_url`
- `access_token`, `refresh_token`, `token_expiry`
- `is_primary`
- `language_code`
- `master_connection_id` (self-reference for satellite/master structure)
- `connection_type` (`master`, `satellite`, etc.)
- timestamps

Notes:
- Dashboard “Active Distributions” and channels API logic read from this table.
- This table is required for current seed + dashboard connection flow.

### `videos`
Source video library records.

Key columns:
- `id` (uuid, primary key)
- `video_id` (text, unique business key)
- `user_id` (text, required)
- `project_id` (uuid, FK)
- `channel_id`, `channel_name`
- `title`, `description`, `thumbnail_url`
- `storage_url`, `video_url`
- `duration`, `view_count`, `like_count`, `comment_count`
- `status`, `language_code`, `video_type`, `source_video_id`
- `published_at`, `deleted_at`, timestamps

### `processing_jobs`
Pipeline job records for localization flow.

Key columns:
- `id` (uuid, primary key)
- `job_id` (uuid, unique business key)
- `user_id` (text, required)
- `project_id` (uuid, FK)
- `source_video_id`, `source_channel_id`
- `target_languages` (array/json)
- `status`, `progress`, `error_message`
- `workflow_state` (jsonb)
- `started_at`, `completed_at`, `deleted_at`, timestamps

Migration-added pipeline columns:
- `elevenlabs_job_id`
- `source_language`
- `estimated_cost`, `actual_cost`
- `cost_breakdown` (jsonb)
- `current_stage`
- `dubbing_metadata` (jsonb)
- `processing_time_seconds`

### `localized_videos`
Per-language outputs for a processing job.

Key columns:
- `id` (uuid, primary key)
- `job_id` (uuid, FK -> `processing_jobs.id`)
- `source_video_id` (text)
- `user_id`, `project_id`, `channel_id`
- `language_code`
- `localized_video_id` (published platform ID)
- `title`, `description`
- `video_url`, `storage_url`, `thumbnail_url`
- `status`, `duration`, timestamps

Migration-added linkage columns:
- `transcript_id` (FK -> `transcripts.id`)
- `translation_id` (FK -> `translations.id`)
- `dubbed_audio_id` (FK -> `dubbed_audio.id`)
- `lip_sync_job_id` (FK -> `lip_sync_jobs.id`)
- `dubbed_audio_url`

### `subscriptions`
PubSubHubbub subscription tracking.

Key columns:
- `id` (uuid, primary key)
- `user_id`, `channel_id`
- `callback_url`, `topic`
- `lease_seconds`, `expires_at`
- `secret`, `status`, `last_verified_at`, `renewal_attempts`
- timestamps

## Pipeline detail tables (migration 002)

### `transcripts`
Transcript artifacts per job.

Key columns:
- `id` (uuid)
- `job_id` (FK -> `processing_jobs.id`)
- `video_id`, `user_id`
- `language_code`
- `transcript_text`, `word_timestamps` (jsonb)
- `provider`, `confidence_score`, `duration`, `status`
- timestamps

### `translations`
Translations per job + target language.

Key columns:
- `id` (uuid)
- `transcript_id` (FK -> `transcripts.id`)
- `job_id` (FK -> `processing_jobs.id`)
- `video_id`, `user_id`
- `source_language`, `target_language`
- `translated_text`, `word_timestamps` (jsonb)
- `provider`, `confidence_score`, `status`, `reviewed`
- timestamps

### `dubbed_audio`
Generated audio records per job + language.

Key columns:
- `id` (uuid)
- `translation_id` (FK -> `translations.id`)
- `job_id` (FK -> `processing_jobs.id`)
- `language_code`, `user_id`
- `audio_url`, `duration`, `file_size`, `format`
- `voice_id`, `voice_name`, `voice_settings` (jsonb), `segments` (jsonb)
- `provider`, `status`, timestamps

### `lip_sync_jobs`
Lip-sync execution tracking per job + language.

Key columns:
- `id` (uuid)
- `job_id` (FK -> `processing_jobs.id`)
- `dubbed_audio_id` (FK -> `dubbed_audio.id`)
- `language_code`, `user_id`
- `synclabs_job_id`, `status`, `progress`
- `input_video_url`, `input_audio_url`, `output_video_url`
- `quality_score`, `processing_time_seconds`, `cost`
- `created_at`, `completed_at`

## Optional/support tables used by services

### `activity_logs`
If present, used by `supabase_db.log_activity` and dashboard activity list.

Expected columns:
- `id`, `user_id`, `project_id`, `action`, `status`, `details`, `timestamp`

### `user_settings`
Read/write helper table for user preferences.

Expected columns:
- `user_id`, settings payload fields, `updated_at`

## Relationship summary

- `projects.user_id` -> logical owner
- `channels.project_id` -> `projects.id`
- `videos.project_id` -> `projects.id`
- `processing_jobs.project_id` -> `projects.id`
- `localized_videos.job_id` -> `processing_jobs.id`
- `transcripts.job_id` -> `processing_jobs.id`
- `translations.job_id` -> `processing_jobs.id`
- `dubbed_audio.job_id` -> `processing_jobs.id`
- `lip_sync_jobs.job_id` -> `processing_jobs.id`
- `youtube_connections.master_connection_id` -> `youtube_connections.connection_id`

## Status lifecycle (current app behavior)

Processing jobs commonly flow through:
- `pending` -> `downloading` -> `transcribing` -> `translating` -> `dubbing` -> `syncing` -> `uploading` -> `waiting_approval`/`completed`
- failure path: `failed`

Localized videos commonly use:
- `processing` / `draft` / `live` / `failed`

## Operational notes

- Auth-scoped frontend queries depend on `user_id` matching logged-in Supabase auth UID.
- Seed scripts should target real auth UID to make dashboard data visible immediately.
- RLS policies on `users` and content tables must permit expected app/seed operations.
