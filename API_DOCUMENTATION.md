# Olleey Backend API Documentation

**Base URL:** `http://localhost:8000` (development) | `https://api.olleey.com` (production)

**Authentication:** Most endpoints require Bearer token authentication via `Authorization: Bearer <token>` header.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Dashboard](#dashboard)
3. [Projects](#projects)
4. [Jobs (Processing)](#jobs-processing)
5. [Videos](#videos)
6. [Channels](#channels)
7. [YouTube Connection](#youtube-connection)
8. [Webhooks](#webhooks)
9. [Localization](#localization)
10. [Costs](#costs)
11. [Settings](#settings)
12. [Events (SSE)](#events-sse)

---

## Authentication

Base path: `/auth`

### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}

Response: 200 OK
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword"
}

Response: 200 OK
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Google OAuth Login
```http
POST /auth/google
Content-Type: application/json

{
  "id_token": "google_id_token_from_frontend"
}

Response: 200 OK
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Get Current User
```http
GET /auth/me
Authorization: Bearer <token>

Response: 200 OK
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "auth_provider": "email",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Refresh Token
```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}

Response: 200 OK
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Logout
```http
POST /auth/logout
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Logged out successfully"
}
```

---

## Dashboard

Base path: `/dashboard`

### Get Dashboard Stats
```http
GET /dashboard/stats?project_id=<optional_project_id>
Authorization: Bearer <token>

Response: 200 OK
{
  "total_videos": 150,
  "total_jobs": 45,
  "active_jobs": 12,
  "completed_jobs": 33,
  "total_views": 125000,
  "total_languages": 8
}
```

### Get Dashboard Jobs
```http
GET /dashboard/jobs?project_id=<optional_project_id>&limit=10
Authorization: Bearer <token>

Response: 200 OK
{
  "jobs": [
    {
      "job_id": "uuid",
      "source_video_id": "video_uuid",
      "status": "processing",
      "progress": 65,
      "target_languages": ["es", "fr", "de"],
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### Get Dashboard Channels
```http
GET /dashboard/channels?project_id=<optional_project_id>
Authorization: Bearer <token>

Response: 200 OK
{
  "channels": [
    {
      "channel_id": "uuid",
      "channel_name": "Spanish Channel",
      "language_code": "es",
      "video_count": 25,
      "status": "active"
    }
  ]
}
```

### Get Dashboard Projects
```http
GET /dashboard/projects
Authorization: Bearer <token>

Response: 200 OK
{
  "projects": [
    {
      "id": "uuid",
      "name": "Marketing Campaign 2025",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### Get YouTube Connections
```http
GET /dashboard/connections?project_id=<optional_project_id>
Authorization: Bearer <token>

Response: 200 OK
{
  "connections": [
    {
      "connection_id": "uuid",
      "youtube_channel_id": "UC...",
      "youtube_channel_name": "My Channel",
      "is_primary": true,
      "connected_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### Get Activity Feed
```http
GET /dashboard/activity?project_id=<optional_project_id>&limit=20
Authorization: Bearer <token>

Response: 200 OK
{
  "activities": [
    {
      "id": "uuid",
      "type": "job_completed",
      "message": "Video dubbed to Spanish",
      "timestamp": "2025-01-01T00:00:00Z",
      "metadata": {}
    }
  ]
}
```

### Get Full Dashboard Data
```http
GET /dashboard?project_id=<optional_project_id>
Authorization: Bearer <token>

Response: 200 OK
{
  "user_id": "uuid",
  "email": "user@example.com",
  "youtube_connections": [...],
  "recent_jobs": [...],
  "language_channels": [...],
  "projects": [...],
  "weekly_stats": {
    "videos_completed": 12,
    "languages_added": 3,
    "growth_percentage": 15.5
  },
  "credits_summary": {
    "total_credits": 1000,
    "used_credits": 350,
    "remaining_credits": 650
  }
}
```

---

## Projects

Base path: `/projects`

### List Projects
```http
GET /projects
Authorization: Bearer <token>

Response: 200 OK
[
  {
    "id": "uuid",
    "name": "Marketing Campaign 2025",
    "master_connection_id": "uuid",
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

### Create Project
```http
POST /projects
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "New Project",
  "master_connection_id": "uuid"  // optional
}

Response: 201 Created
{
  "id": "uuid",
  "name": "New Project",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Get Project
```http
GET /projects/{project_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "id": "uuid",
  "name": "Marketing Campaign 2025",
  "master_connection_id": "uuid",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Update Project
```http
PATCH /projects/{project_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Updated Project Name"
}

Response: 200 OK
{
  "id": "uuid",
  "name": "Updated Project Name",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Delete Project
```http
DELETE /projects/{project_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Project deleted successfully"
}
```

### Get Project Activity
```http
GET /projects/{project_id}/activity
Authorization: Bearer <token>

Response: 200 OK
[
  {
    "id": "uuid",
    "project_id": "uuid",
    "type": "job_created",
    "message": "New dubbing job created",
    "timestamp": "2025-01-01T00:00:00Z"
  }
]
```

---

## Jobs (Processing)

Base path: `/jobs`

### Create Dubbing Job
```http
POST /jobs
Authorization: Bearer <token>
Content-Type: application/json

{
  "source_video_id": "video_uuid",
  "source_channel_id": "channel_uuid",
  "target_languages": ["es", "fr", "de"],
  "project_id": "project_uuid",
  "title": "My Video Title",
  "description": "Video description",
  "is_simulation": false  // optional: true for demo mode
}

Response: 201 Created
{
  "job_id": "uuid",
  "source_video_id": "video_uuid",
  "status": "pending",
  "progress": 0,
  "target_languages": ["es", "fr", "de"],
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Create Manual Job
```http
POST /jobs/manual
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "video_url": "https://youtube.com/watch?v=...",
  "target_languages": ["es", "fr"],
  "project_id": "project_uuid"
}

Response: 201 Created
{
  "job_id": "uuid",
  "source_video_id": "video_uuid",
  "status": "pending",
  "target_languages": ["es", "fr"]
}
```

### List Jobs
```http
GET /jobs?project_id=<optional>&limit=50&status=<optional>
Authorization: Bearer <token>

Response: 200 OK
{
  "jobs": [
    {
      "job_id": "uuid",
      "source_video_id": "video_uuid",
      "status": "processing",
      "progress": 65,
      "target_languages": ["es", "fr"],
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T01:00:00Z"
    }
  ],
  "total": 125
}
```

### Get Job Details
```http
GET /jobs/{job_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "job_id": "uuid",
  "source_video_id": "video_uuid",
  "source_channel_id": "channel_uuid",
  "status": "completed",
  "progress": 100,
  "target_languages": ["es", "fr"],
  "created_at": "2025-01-01T00:00:00Z",
  "completed_at": "2025-01-01T02:00:00Z",
  "workflow_state": {
    "metadata_extraction": {...},
    "translations": {...},
    "video_dubbing": {...}
  }
}
```

### Get Job Videos (Localized)
```http
GET /jobs/{job_id}/videos
Authorization: Bearer <token>

Response: 200 OK
[
  {
    "id": "uuid",
    "job_id": "uuid",
    "language_code": "es",
    "storage_url": "https://storage.url/video.mp4",
    "status": "completed",
    "title": "Mi Video",
    "description": "Descripción del video",
    "thumbnail_url": "https://...",
    "dubbed_audio_url": "https://..."
  }
]
```

### Get Job Transcript
```http
GET /jobs/{job_id}/transcript
Authorization: Bearer <token>

Response: 200 OK
{
  "job_id": "uuid",
  "source_language": "en",
  "transcript_text": "This is the full transcript...",
  "confidence_score": 0.95,
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Get Job Translations
```http
GET /jobs/{job_id}/translations
Authorization: Bearer <token>

Response: 200 OK
[
  {
    "job_id": "uuid",
    "target_language": "es",
    "translated_text": "Esta es la traducción completa...",
    "confidence_score": 0.92,
    "translation_engine": "elevenlabs"
  }
]
```

### Get Job Translation (Single Language)
```http
GET /jobs/{job_id}/translations/{language_code}
Authorization: Bearer <token>

Response: 200 OK
{
  "job_id": "uuid",
  "target_language": "es",
  "source_language": "en",
  "translated_text": "Esta es la traducción completa...",
  "confidence_score": 0.92,
  "translation_engine": "elevenlabs",
  "created_at": "2025-01-01T00:00:00Z"
}
```

### Update Transcript
```http
PATCH /jobs/{job_id}/transcript
Authorization: Bearer <token>
Content-Type: application/json

{
  "transcript_text": "Updated transcript text..."
}

Response: 200 OK
{
  "success": true,
  "message": "Transcript updated successfully"
}
```

### Update Translation
```http
PATCH /jobs/{job_id}/translations/{language_code}
Authorization: Bearer <token>
Content-Type: application/json

{
  "translated_text": "Texto de traducción actualizado..."
}

Response: 200 OK
{
  "success": true,
  "message": "Translation updated successfully"
}
```

### Update Localized Video Metadata
```http
PATCH /jobs/{job_id}/videos/{language_code}
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "title": "New Title",
  "description": "New Description",
  "thumbnail_file": <file>  // optional
}

Response: 200 OK
{
  "success": true,
  "message": "Localized video updated",
  "updated_fields": ["title", "description"]
}
```

### Approve Job
```http
POST /jobs/{job_id}/approve
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Job approved successfully",
  "job_id": "uuid"
}
```

### Approve Localized Videos
```http
POST /jobs/{job_id}/videos/approve
Authorization: Bearer <token>
Content-Type: application/json

{
  "language_codes": ["es", "fr", "de"]
}

Response: 200 OK
{
  "message": "Videos approved",
  "approved_count": 3
}
```

### Reject Localized Videos
```http
POST /jobs/{job_id}/videos/reject
Authorization: Bearer <token>
Content-Type: application/json

{
  "language_codes": ["es"],
  "reason": "Poor audio quality",
  "feedback": "The voice sounds robotic at 0:45"
}

Response: 200 OK
{
  "message": "Videos rejected",
  "rejected_count": 1
}
```

### Update Video Status
```http
POST /jobs/{job_id}/videos/{language_code}/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "approved"
}

Response: 200 OK
{
  "message": "Status updated successfully"
}
```

### Start Job Processing
```http
POST /jobs/{job_id}/start-processing
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Job processing started",
  "job_id": "uuid"
}
```

### Pause Job
```http
POST /jobs/{job_id}/pause
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Job paused successfully"
}
```

### Cancel Job
```http
DELETE /jobs/{job_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "success": true,
  "message": "Job cancelled",
  "cancelled_videos": 3
}
```

### Save as Draft
```http
POST /jobs/{job_id}/save-draft
Authorization: Bearer <token>
Content-Type: application/json

{
  "language_code": "es"
}

Response: 200 OK
{
  "message": "Draft saved successfully"
}
```

### Update Job Status (Admin/Demo)
```http
PATCH /jobs/{job_id}/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "waiting_approval"
}

Response: 200 OK
{
  "message": "Job status updated"
}
```

### Get Job Statistics - Metrics
```http
GET /jobs/statistics/metrics
Authorization: Bearer <token>

Response: 200 OK
{
  "success": true,
  "metrics": {
    "total_jobs": 150,
    "completed_jobs": 120,
    "failed_jobs": 5,
    "average_processing_time": 3600,
    "success_rate": 0.96
  }
}
```

### Get Job Statistics - Recent
```http
GET /jobs/statistics/recent
Authorization: Bearer <token>

Response: 200 OK
{
  "success": true,
  "recent_jobs": [...]
}
```

### Get Job Statistics - Errors
```http
GET /jobs/statistics/errors?days=7
Authorization: Bearer <token>

Response: 200 OK
{
  "success": true,
  "errors": [
    {
      "job_id": "uuid",
      "error_type": "transcription_failed",
      "error_message": "...",
      "timestamp": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### Get Job Statistics - Languages
```http
GET /jobs/statistics/languages
Authorization: Bearer <token>

Response: 200 OK
{
  "success": true,
  "languages": [
    {
      "language_code": "es",
      "language_name": "Spanish",
      "job_count": 45,
      "completion_rate": 0.95
    }
  ]
}
```

### Get Job Statistics - Insights
```http
GET /jobs/statistics/insights
Authorization: Bearer <token>

Response: 200 OK
{
  "success": true,
  "insights": [
    {
      "type": "recommendation",
      "message": "Spanish videos have 20% higher completion rate",
      "impact": "high"
    }
  ]
}
```

---

## Videos

Base path: `/videos`

### List Videos
```http
GET /videos/list?page=1&page_size=50&channel_id=<optional>&project_id=<optional>&video_type=all
Authorization: Bearer <token>

Response: 200 OK
{
  "videos": [
    {
      "video_id": "uuid",
      "title": "My Video",
      "description": "Video description",
      "thumbnail_url": "https://...",
      "duration": 180,
      "view_count": 1000,
      "status": "published",
      "channel_id": "uuid",
      "published_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 250,
  "page": 1,
  "page_size": 50
}
```

### Get Video by ID
```http
GET /videos/{video_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "video_id": "uuid",
  "title": "My Video",
  "description": "Video description",
  "channel_id": "uuid",
  "channel_name": "My Channel",
  "thumbnail_url": "https://...",
  "duration": 180,
  "view_count": 1000,
  "localizations": {
    "es": {
      "status": "live",
      "video_url": "https://...",
      "title": "Mi Video"
    }
  }
}
```

### Upload Video
```http
POST /videos/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "video_file": <file>,
  "title": "My Video",
  "description": "Video description",
  "channel_id": "uuid",
  "thumbnail_file": <file>  // optional
}

Response: 201 Created
{
  "video_id": "uuid",
  "success": true,
  "message": "Video uploaded successfully"
}
```

### Subscribe to Channel
```http
POST /videos/subscribe
Authorization: Bearer <token>
Content-Type: application/json

{
  "channel_id": "UC..."
}

Response: 200 OK
{
  "success": true,
  "message": "Subscribed to channel",
  "subscription_id": "uuid"
}
```

### Unsubscribe from Channel
```http
POST /videos/unsubscribe
Authorization: Bearer <token>
Content-Type: application/json

{
  "channel_id": "UC..."
}

Response: 200 OK
{
  "success": true,
  "message": "Unsubscribed from channel"
}
```

---

## Channels

Base path: `/channels`

### Get Channel Graph
```http
GET /channels/graph?project_id=<optional>
Authorization: Bearer <token>

Response: 200 OK
{
  "master_nodes": [
    {
      "connection_id": "uuid",
      "channel_id": "UC...",
      "channel_name": "English Master",
      "language_code": "en",
      "is_primary": true,
      "language_channels": [
        {
          "id": "uuid",
          "channel_id": "UC...",
          "channel_name": "Spanish Channel",
          "language_code": "es",
          "videos_count": 25
        }
      ]
    }
  ],
  "total_connections": 5,
  "active_connections": 4
}
```

### List Language Channels
```http
GET /channels?project_id=<optional>
Authorization: Bearer <token>

Response: 200 OK
{
  "channels": [
    {
      "id": "uuid",
      "channel_id": "UC...",
      "channel_name": "Spanish Channel",
      "language_code": "es",
      "language_name": "Spanish",
      "videos_count": 25,
      "status": "active",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### Create Language Channel
```http
POST /channels
Authorization: Bearer <token>
Content-Type: application/json

{
  "channel_id": "UC...",
  "language_code": "es",
  "channel_name": "Spanish Channel",
  "master_connection_id": "uuid",
  "project_id": "uuid"
}

Response: 201 Created
{
  "id": "uuid",
  "channel_id": "UC...",
  "channel_name": "Spanish Channel",
  "language_code": "es"
}
```

### Update Language Channel
```http
PATCH /channels/{channel_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "channel_name": "Updated Spanish Channel",
  "is_paused": false
}

Response: 200 OK
{
  "id": "uuid",
  "channel_name": "Updated Spanish Channel"
}
```

### Pause Channel
```http
PUT /channels/{channel_id}/pause
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Channel paused successfully"
}
```

### Unpause Channel
```http
PUT /channels/{channel_id}/unpause
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Channel unpaused successfully"
}
```

### Delete Language Channel
```http
DELETE /channels/{channel_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Language channel deleted successfully"
}
```

---

## YouTube Connection

Base path: `/youtube`

### Get Channel Graph
```http
GET /youtube/channel_graph?project_id=<optional>
Authorization: Bearer <token>

Response: 200 OK
{
  "master_nodes": [...],
  "total_connections": 5,
  "active_connections": 4,
  "expired_connections": 1
}
```

### Initiate YouTube Connection
```http
GET /youtube/connect?token=<access_token>&master_connection_id=<optional>&redirect_to=<optional>
Authorization: Bearer <token>

Response: 302 Redirect
Redirects to Google OAuth consent screen
```

### YouTube OAuth Callback
```http
GET /youtube/connect/callback?code=<oauth_code>&state=<state>

Response: 302 Redirect
Redirects back to frontend with connection result
```

### List YouTube Connections
```http
GET /youtube/connections
Authorization: Bearer <token>

Response: 200 OK
{
  "connections": [
    {
      "connection_id": "uuid",
      "youtube_channel_id": "UC...",
      "youtube_channel_name": "My Channel",
      "channel_avatar_url": "https://...",
      "language_code": "en",
      "is_primary": true,
      "connected_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### Update Connection
```http
PATCH /youtube/connections/{connection_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "language_code": "en"
}

Response: 200 OK
{
  "connection_id": "uuid",
  "language_code": "en"
}
```

### Set Primary Connection
```http
PUT /youtube/connections/{connection_id}/set-primary
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Connection set as primary"
}
```

### Unset Primary Connection
```http
DELETE /youtube/connections/{connection_id}/unset-primary
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Primary status removed"
}
```

### Disconnect YouTube Channel
```http
DELETE /youtube/connections/{connection_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "message": "Connection removed",
  "connection_id": "uuid",
  "connection_type": "master",
  "unassigned_language_channels": 3
}
```

---

## Webhooks

Base path: `/webhooks`

### YouTube Webhook Verification
```http
GET /webhooks/youtube?hub.mode=subscribe&hub.challenge=<challenge>&hub.topic=<topic>

Response: 200 OK
<challenge>
```

### YouTube Webhook Notification
```http
POST /webhooks/youtube
Content-Type: application/atom+xml

<feed>...</feed>

Response: 200 OK
```

---

## Localization

Base path: `/localization`

### Upload Captions
```http
POST /localization/captions/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "caption_file": <file>,
  "language_code": "es",
  "video_id": "uuid"
}

Response: 200 OK
{
  "caption_id": "uuid",
  "language_code": "es",
  "success": true
}
```

---

## Costs

Base path: `/costs`

### Estimate Job Cost
```http
POST /costs/estimate
Authorization: Bearer <token>
Content-Type: application/json

{
  "video_duration_seconds": 180,
  "target_languages": ["es", "fr", "de"],
  "include_lip_sync": true
}

Response: 200 OK
{
  "estimated_cost": 15.75,
  "breakdown": {
    "dubbing": 9.00,
    "lip_sync": 6.75,
    "per_language": 5.25
  },
  "currency": "USD"
}
```

### Get User Cost Summary
```http
GET /costs/summary
Authorization: Bearer <token>

Response: 200 OK
{
  "total_spent": 450.00,
  "current_month": 125.50,
  "last_month": 98.75,
  "currency": "USD",
  "breakdown_by_service": {
    "dubbing": 300.00,
    "lip_sync": 150.00
  }
}
```

### Get Job Cost Details
```http
GET /costs/job/{job_id}
Authorization: Bearer <token>

Response: 200 OK
{
  "job_id": "uuid",
  "estimated_cost": 15.75,
  "actual_cost": 14.50,
  "cost_breakdown": {
    "dubbing": 8.50,
    "lip_sync": 6.00
  },
  "currency": "USD"
}
```

---

## Settings

Base path: `/settings`

### Get User Settings
```http
GET /settings
Authorization: Bearer <token>

Response: 200 OK
{
  "theme": "dark",
  "timezone": "America/Los_Angeles",
  "notifications": {
    "email_notifications": true,
    "distribution_updates": true,
    "error_alerts": true
  }
}
```

### Update User Settings
```http
PATCH /settings
Authorization: Bearer <token>
Content-Type: application/json

{
  "theme": "light",
  "notifications": {
    "email_notifications": false
  }
}

Response: 200 OK
{
  "theme": "light",
  "timezone": "America/Los_Angeles",
  "notifications": {
    "email_notifications": false,
    "distribution_updates": true,
    "error_alerts": true
  }
}
```

---

## Events (SSE)

Base path: `/events`

### Server-Sent Events Stream
```http
GET /events/stream
Authorization: Bearer <token>
Accept: text/event-stream

Response: 200 OK (streaming)
Content-Type: text/event-stream

data: {"type": "job_update", "job_id": "uuid", "status": "processing", "progress": 65}

data: {"type": "job_completed", "job_id": "uuid", "status": "completed"}
```

**Event Types:**
- `job_created` - New job created
- `job_update` - Job progress update
- `job_completed` - Job finished successfully
- `job_failed` - Job encountered an error
- `video_ready` - Localized video ready for review

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or expired token"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this resource"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limits

- **Authentication endpoints:** 10 requests per minute per IP
- **Standard endpoints:** 100 requests per minute per user
- **Upload endpoints:** 10 requests per hour per user
- **Webhook endpoints:** No rate limit

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1609459200
```

---

## Pagination

List endpoints support pagination via query parameters:

```http
GET /videos/list?page=2&page_size=50
```

Response includes pagination metadata:
```json
{
  "videos": [...],
  "total": 250,
  "page": 2,
  "page_size": 50,
  "total_pages": 5
}
```

---

## Filtering & Sorting

Many list endpoints support filtering and sorting:

```http
GET /jobs?status=processing&sort_by=created_at&sort_order=desc
```

Common filters:
- `status` - Filter by status
- `project_id` - Filter by project
- `channel_id` - Filter by channel
- `language_code` - Filter by language
- `created_after` - Date filter
- `created_before` - Date filter

Common sort fields:
- `created_at` - Creation date
- `updated_at` - Last update date
- `name` - Alphabetical
- `status` - Status order

---

## WebSocket Support (Future)

WebSocket endpoint for real-time updates:
```
ws://localhost:8000/ws/jobs?token=<access_token>
```

Currently using Server-Sent Events (SSE) at `/events/stream` for real-time updates.

---

**Last Updated:** 2025-02-12
**API Version:** 1.0.0
**Contact:** support@olleey.com
