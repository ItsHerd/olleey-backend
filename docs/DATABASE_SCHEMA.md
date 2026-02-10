# Supabase Database Schema

This document outlines the table structures and relationships in the Olleey Supabase database.

---

## 📋 Tables Overview

1. **`users`** - User authentication and profile data
2. **`projects`** - Grouping of videos and jobs for a user
3. **`channels`** - YouTube channel connections (Master and Language Satellite)
4. **`videos`** - Source (original) videos synced from YouTube
5. **`processing_jobs`** - Video dubbing/processing pipeline jobs
6. **`localized_videos`** - Processed and published localized video versions
7. **`subscriptions`** - YouTube PubSubHubbub webhook subscriptions

---

## 1. `users` Table
Stores user profile information and OAuth credentials.

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | `uuid` (PK) | Unique user identifier |
| `email` | `text` | User's email address |
| `name` | `text` | User's full name |
| `access_token` | `text` | Google OAuth access token |
| `refresh_token` | `text` | Google OAuth refresh token |
| `token_expiry` | `timestamp` | Token expiration time |
| `created_at` | `timestamp` | Record creation time |
| `updated_at` | `timestamp` | Last update time |

---

## 2. `projects` Table
Used to organize content and jobs into logical projects.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` (PK) | Project identifier |
| `user_id` | `uuid` (FK) | Owner of the project |
| `name` | `text` | Project name |
| `description` | `text` | Project description |
| `settings` | `jsonb` | Project-specific configuration |
| `created_at` | `timestamp` | Record creation time |
| `updated_at` | `timestamp` | Last update time |

---

## 3. `channels` Table
Stores YouTube channel information connected to the platform.

| Column | Type | Description |
|--------|------|-------------|
| `channel_id` | `text` (PK) | YouTube Channel ID (starts with UC) |
| `user_id` | `uuid` (FK) | Owner of the channel |
| `project_id` | `uuid` (FK) | Associated project ID |
| `channel_name` | `text` | YouTube channel name |
| `language_code` | `text` | ISO 639-1 language code |
| `language_name` | `text` | Full language name |
| `is_master` | `boolean` | True if this is the primary source channel |
| `master_channel_id` | `text` | Links satellite channels to their master |
| `thumbnail_url` | `text` | Channel avatar URL |
| `subscriber_count` | `integer` | Current subscriber count |
| `video_count` | `integer` | Total videos on channel |
| `created_at` | `timestamp` | Record creation time |
| `updated_at` | `timestamp` | Last update time |

---

## 4. `videos` Table
Contains metadata for original source videos.

| Column | Type | Description |
|--------|------|-------------|
| `video_id` | `text` (PK) | YouTube Video ID |
| `user_id` | `uuid` (FK) | Owner of the video |
| `project_id` | `uuid` (FK) | Associated project ID |
| `channel_id` | `text` (FK) | Source channel ID |
| `channel_name` | `text` | Name of the source channel |
| `title` | `text` | Video title |
| `description` | `text` | Video description |
| `thumbnail_url` | `text` | Video thumbnail URL |
| `storage_url` | `text` | Internal storage path/URL |
| `video_url` | `text` | YouTube video URL |
| `duration` | `integer` | Video duration in seconds |
| `view_count` | `integer` | Total view count |
| `like_count` | `integer` | Total like count |
| `comment_count` | `integer` | Total comment count |
| `status` | `text` | App status (NOT_STARTED, LIVE, etc.) |
| `published_at` | `timestamp` | YouTube publication time |
| `created_at` | `timestamp` | Record creation time |
| `updated_at` | `timestamp` | Last update time |

---

## 5. `processing_jobs` Table
Tracks the dubbing and processing pipeline.

| Column | Type | Description |
|--------|------|-------------|
| `job_id` | `uuid` (PK) | Processing job identifier |
| `user_id` | `uuid` (FK) | Owner of the job |
| `project_id` | `uuid` (FK) | Associated project ID |
| `source_video_id` | `text` (FK) | Reference to original video |
| `source_channel_id` | `text` (FK) | Reference to source channel |
| `target_languages` | `jsonb` | Array of language codes to produce |
| `status` | `text` | Pipeline status (PENDING, PROCESSING, etc.) |
| `progress` | `integer` | Numeric progress (0-100) |
| `workflow_state` | `jsonb` | Detailed state of each pipeline stage |
| `error_message` | `text` | Failure details if status is FAILED |
| `created_at` | `timestamp` | Job start time |
| `updated_at` | `timestamp` | Last status update |

---

## 6. `localized_videos` Table
Stores information about the final localized versions of a video.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` (PK) | Internal record ID |
| `job_id` | `uuid` (FK) | Parent processing job ID |
| `source_video_id` | `text` (FK) | Reference to original video |
| `user_id` | `uuid` (FK) | Owner identifier |
| `project_id` | `uuid` (FK) | Associated project ID |
| `channel_id` | `text` (FK) | Target YouTube channel ID |
| `language_code` | `text` | Language of this version |
| `localized_video_id` | `text` | YouTube ID of the published version |
| `title` | `text` | Localized title |
| `description` | `text` | Localized description |
| `video_url` | `text` | Storage path or YouTube URL |
| `thumbnail_url` | `text` | Localized thumbnail path |
| `status` | `text` | Status (DRAFT, LIVE, etc.) |
| `duration` | `integer` | Duration in seconds |
| `created_at` | `timestamp` | Record creation time |
| `updated_at` | `timestamp` | Last update time |

---

## 7. `subscriptions` Table
Manages YouTube PubSubHubbub webhooks.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `uuid` (PK) | Subscription identifier |
| `user_id` | `uuid` (FK) | Associated user |
| `channel_id` | `text` | YouTube channel being monitored |
| `callback_url` | `text` | Webhook URL |
| `topic` | `text` | Feed URL (Atom feed) |
| `lease_seconds` | `integer` | Lease duration |
| `expires_at` | `timestamp` | Expiration time |
| `secret` | `text` | Webhook verification secret |
| `created_at` | `timestamp` | Record creation time |
| `updated_at` | `timestamp` | Last update time |
