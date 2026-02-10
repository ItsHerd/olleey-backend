# Data Schema Documentation

This document outlines the complete data schema for the YouTube Dubbing Platform, including all collections, fields, and relationships stored in Firebase Firestore.

---

## 📊 Collections Overview

The platform uses the following Firestore collections:
1. **users** - User authentication and OAuth tokens
2. **subscriptions** - PubSubHubbub channel subscriptions
3. **processing_jobs** - Video dubbing/processing jobs
4. **language_channels** - Language-specific YouTube channels
5. **localized_videos** - Processed and published localized videos

---

## 1. Users Collection

**Purpose**: Store user authentication credentials and OAuth tokens

**Document ID**: `{user_id}` (Google user ID)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | string | ✅ | Google user ID (document ID) |
| `email` | string | ❌ | User's email address |
| `access_token` | string | ✅ | OAuth 2.0 access token |
| `refresh_token` | string | ✅ | OAuth 2.0 refresh token |
| `token_expiry` | timestamp | ❌ | Access token expiration time |
| `created_at` | timestamp | ✅ | Account creation timestamp |
| `updated_at` | timestamp | ✅ | Last update timestamp |

**Example**:
```json
{
  "user_id": "12345678901234567890",
  "email": "user@example.com",
  "access_token": "ya29.a0AfH6SMC...",
  "refresh_token": "1//0gX...",
  "token_expiry": "2026-01-19T00:00:00Z",
  "created_at": "2026-01-18T12:00:00Z",
  "updated_at": "2026-01-18T16:30:00Z"
}
```

---

## 2. Subscriptions Collection

**Purpose**: Track PubSubHubbub subscriptions for YouTube channel notifications

**Document ID**: `{subscription_id}` (UUID)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Subscription ID (document ID) |
| `user_id` | string | ✅ | Owner user ID |
| `channel_id` | string | ✅ | YouTube channel ID being monitored |
| `callback_url` | string | ✅ | Webhook callback URL |
| `topic` | string | ✅ | PubSubHubbub topic URL |
| `lease_seconds` | integer | ✅ | Subscription lease duration (seconds) |
| `expires_at` | timestamp | ❌ | Subscription expiration time |
| `secret` | string | ❌ | Optional subscription secret |
| `created_at` | timestamp | ✅ | Subscription creation time |
| `updated_at` | timestamp | ✅ | Last update timestamp |

**Example**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "12345678901234567890",
  "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
  "callback_url": "http://localhost:8000/webhooks/youtube",
  "topic": "https://www.youtube.com/xml/feeds/videos.xml?channel_id=UCxxxxxxxxxxxxxxxxxxxxxx",
  "lease_seconds": 2592000,
  "expires_at": "2026-02-17T12:00:00Z",
  "created_at": "2026-01-18T12:00:00Z",
  "updated_at": "2026-01-18T12:00:00Z"
}
```

---

## 3. Processing Jobs Collection

**Purpose**: Track video dubbing/processing pipeline jobs

**Document ID**: `{job_id}` (UUID)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Job ID (document ID) |
| `user_id` | string | ✅ | Owner user ID |
| `source_video_id` | string | ✅ | Original YouTube video ID |
| `source_channel_id` | string | ✅ | Source YouTube channel ID |
| `target_languages` | array[string] | ✅ | List of target language codes (ISO 639-1) |
| `status` | string | ✅ | Job status: `pending`, `downloading`, `processing`, `uploading`, `completed`, `failed` |
| `progress` | integer | ✅ | Progress percentage (0-100) |
| `error_message` | string | ❌ | Error message if job failed |
| `created_at` | timestamp | ✅ | Job creation timestamp |
| `updated_at` | timestamp | ✅ | Last update timestamp |
| `completed_at` | timestamp | ❌ | Job completion timestamp |

**Status Values**:
- `pending` - Job created, waiting to start
- `downloading` - Downloading source video from YouTube
- `processing` - Processing video (lip-sync, dubbing, etc.)
- `uploading` - Uploading processed videos to YouTube
- `completed` - All localized videos published successfully
- `failed` - Job failed with error

**Example**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "12345678901234567890",
  "source_video_id": "dQw4w9WgXcQ",
  "source_channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
  "target_languages": ["es", "fr", "de"],
  "status": "processing",
  "progress": 45,
  "error_message": null,
  "created_at": "2026-01-18T14:00:00Z",
  "updated_at": "2026-01-18T14:15:00Z",
  "completed_at": null
}
```

---

## 4. Language Channels Collection

**Purpose**: Map language codes to YouTube channels for publishing localized content

**Document ID**: `{channel_doc_id}` (UUID)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Language channel record ID (document ID) |
| `user_id` | string | ✅ | Owner user ID |
| `channel_id` | string | ✅ | YouTube channel ID |
| `language_code` | string | ✅ | ISO 639-1 language code (e.g., "es", "fr", "de") |
| `channel_name` | string | ❌ | Human-readable channel name |
| `created_at` | timestamp | ✅ | Record creation timestamp |
| `updated_at` | timestamp | ✅ | Last update timestamp |

**Example**:
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "user_id": "12345678901234567890",
  "channel_id": "UCyyyyyyyyyyyyyyyyyyyy",
  "language_code": "es",
  "channel_name": "Spanish Dubbing Channel",
  "created_at": "2026-01-18T10:00:00Z",
  "updated_at": "2026-01-18T10:00:00Z"
}
```

---

## 5. Localized Videos Collection

**Purpose**: Track processed and published localized video versions

**Document ID**: `{localized_video_id}` (UUID)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Localized video record ID (document ID) |
| `job_id` | string | ✅ | Parent processing job ID |
| `source_video_id` | string | ✅ | Original YouTube video ID |
| `localized_video_id` | string | ❌ | YouTube video ID of published localized version |
| `language_code` | string | ✅ | ISO 639-1 language code |
| `channel_id` | string | ✅ | Target YouTube channel ID |
| `status` | string | ✅ | Video status: `pending`, `processing`, `uploaded`, `published`, `failed` |
| `storage_url` | string | ❌ | URL to processed video file (local storage path) |
| `created_at` | timestamp | ✅ | Record creation timestamp |
| `updated_at` | timestamp | ✅ | Last update timestamp |

**Status Values**:
- `pending` - Waiting to be processed
- `processing` - Currently being processed (lip-sync, dubbing)
- `uploaded` - Uploaded to YouTube but not yet published
- `published` - Successfully published to YouTube channel
- `failed` - Processing or upload failed

**Example**:
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "source_video_id": "dQw4w9WgXcQ",
  "localized_video_id": "aBcDeFgHiJk",
  "language_code": "es",
  "channel_id": "UCyyyyyyyyyyyyyyyyyyyy",
  "status": "published",
  "storage_url": "/storage/videos/12345678901234567890/660e8400-e29b-41d4-a716-446655440001/es/aBcDeFgHiJk.mp4",
  "created_at": "2026-01-18T14:05:00Z",
  "updated_at": "2026-01-18T14:20:00Z"
}
```

---

## 🔗 Relationships

### Job → Localized Videos
- One `processing_job` can have multiple `localized_videos` (one per target language)
- Relationship: `localized_videos.job_id` → `processing_jobs.id`

### User → All Collections
- All collections are scoped to a `user_id`
- Users can have multiple:
  - Subscriptions (monitoring multiple channels)
  - Processing jobs (processing multiple videos)
  - Language channels (publishing to multiple channels)
  - Localized videos (through jobs)

### Channel → Language Channel
- `language_channels.channel_id` references a YouTube channel
- One language channel per `(user_id, language_code)` combination

### Source Video → Processing Job
- `processing_jobs.source_video_id` references the original YouTube video
- One job per source video (but can process multiple languages)

---

## 📝 Data Flow Example

### Complete Workflow:

1. **User subscribes to channel** → Creates `subscription` record
2. **New video uploaded to YouTube** → PubSubHubbub webhook triggers
3. **System creates processing job** → Creates `processing_job` with:
   - `source_video_id`: Original video ID
   - `target_languages`: ["es", "fr", "de"]
   - `status`: "pending"
4. **Job processing starts** → Updates `processing_job.status` to "downloading" → "processing"
5. **For each target language**:
   - Creates `localized_video` record with `status: "pending"`
   - Processes video (lip-sync, dubbing)
   - Updates `localized_video.status` to "processing" → "uploaded"
   - Uploads to YouTube channel from `language_channels`
   - Updates `localized_video.status` to "published" and sets `localized_video_id`
6. **Job completes** → Updates `processing_job.status` to "completed"

---

## 🎯 Key Queries

### Get all jobs for a user:
```python
processing_jobs.where('user_id', '==', user_id)
```

### Get all localized videos for a job:
```python
localized_videos.where('job_id', '==', job_id)
```

### Get language channel for a language:
```python
language_channels.where('user_id', '==', user_id).where('language_code', '==', 'es')
```

### Get all published videos in a language:
```python
localized_videos.where('language_code', '==', 'es').where('status', '==', 'published')
```

---

## 📊 Summary Table

| Collection | Primary Key | Key Relationships | Main Purpose |
|------------|-------------|-------------------|--------------|
| **users** | `user_id` | → All collections | Authentication |
| **subscriptions** | `subscription_id` | → `users.user_id` | Channel monitoring |
| **processing_jobs** | `job_id` | → `users.user_id`, `source_video_id` | Job tracking |
| **language_channels** | `id` | → `users.user_id`, `channel_id` | Language→Channel mapping |
| **localized_videos** | `id` | → `job_id`, `source_video_id`, `channel_id` | Published video tracking |

---

## 🔄 Status Lifecycle

### Processing Job Status Flow:
```
pending → downloading → processing → uploading → completed
                                         ↓
                                      failed
```

### Localized Video Status Flow:
```
pending → processing → uploaded → published
            ↓
         failed
```

---

## 📌 Notes

- All timestamps use Firestore `SERVER_TIMESTAMP` for consistency
- Language codes follow ISO 639-1 standard (2-letter codes)
- Video IDs are YouTube video IDs (11 characters)
- Channel IDs are YouTube channel IDs (24 characters, starting with "UC")
- Storage URLs are relative paths from the storage root directory
