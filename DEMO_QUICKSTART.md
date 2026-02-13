# Demo Pipeline - Quick Start Guide

## What This Does

The demo pipeline provides a **complete end-to-end demo** of the dubbing workflow using your pre-dubbed Spanish video from S3. When the demo user creates a job, it simulates the entire pipeline with realistic progress updates but completes in ~26 seconds instead of 5-10 minutes.

## Demo Flow

```
User creates job → [Processing 26s] → Ready for review → Plays Spanish dubbed video from S3
```

**Stages simulated:**
1. Transcription (5s) - 0% → 25%
2. Translation (3s) - 25% → 50%  
3. Dubbing (8s) - 50% → 75%
4. Lip Sync (10s) - 75% → 100%
5. Complete - Ready for review!

## Quick Test

### 1. Test the Demo Pipeline

```bash
cd olleey-backend
python scripts/test_demo_pipeline.py
```

Expected output:
```
Testing Mock Pipeline...
  [0%] transcribing
  [25%] transcribed
  [50%] translating_es
  [75%] dubbing_es
  [100%] completed
✓ Pipeline test passed
```

### 2. Test Video Accessibility

```bash
python scripts/manage_demo_videos.py --test
```

This checks if your S3 videos are accessible.

### 3. List Demo Videos

```bash
python scripts/manage_demo_videos.py --list
```

## How It Works

### Backend

1. **Demo User Detected**: When `demo@olleey.com` creates a job
2. **Mock Pipeline Started**: Background task runs `mock_pipeline.process_job()`
3. **Progress Updates**: Database updated every 5-10 seconds
4. **SSE Events**: Frontend receives real-time progress updates
5. **Completion**: Job marked as `waiting_approval` with S3 video URLs

### Frontend (No Changes Needed!)

The frontend already has everything:
- ✅ SSE connection (`useJobEvents.ts`)
- ✅ Real-time updates
- ✅ Progress bars
- ✅ Review modal
- ✅ Video player

Progress bars will automatically update as the mock pipeline runs!

## Demo User Credentials

```
Email: demo@olleey.com
Password: password
```

## Your Demo Video URLs

Configured in `config.py`:

```python
DEMO_VIDEO_LIBRARY = {
    "video_001_yceo": {
        "id": "demo_real_video_001",
        "title": "The Nature of Startups with YC CEO",
        "original_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/en.mp4",
        "languages": {
            "es": {
                "dubbed_video_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov",
                "dubbed_audio_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/es-audio.mp3",
            }
        }
    }
}
```

## Adding More Demo Videos

1. Upload videos to S3/Supabase Storage
2. Edit `config.py` and add to `DEMO_VIDEO_LIBRARY`
3. Restart backend server
4. Test with `python scripts/manage_demo_videos.py --test`

See `scripts/manage_demo_videos.py --add-help` for detailed instructions.

## Files Modified

- ✅ `config.py` - Added DEMO_VIDEO_LIBRARY and timing config
- ✅ `services/mock_pipeline.py` - Complete pipeline orchestrator
- ✅ `services/mock_elevenlabs.py` - ElevenLabs mock
- ✅ `services/synclabs.py` - Enhanced mock with demo library support
- ✅ `services/job_queue.py` - Integrated mock pipeline for demo users
- ✅ `main.py` - Added config validation on startup
- ✅ `scripts/test_demo_pipeline.py` - Test script
- ✅ `scripts/manage_demo_videos.py` - Management utility

## Next Steps

1. **Start Backend**: `python dev_server.py`
2. **Login as Demo User**: Use `demo@olleey.com` / `password`
3. **Create Job**: Select original video, choose Spanish
4. **Watch Progress**: Progress bar animates through stages
5. **Review**: Click "Review" button when complete
6. **Watch Video**: Spanish dubbed video plays from S3
7. **Approve**: Click "Approve & Publish"

The entire flow takes ~30 seconds from job creation to approval!

## Troubleshooting

**Videos not loading?**
```bash
python scripts/manage_demo_videos.py --test
```

**Pipeline not starting?**
- Check backend logs for errors
- Verify demo user exists in database
- Check config validation output on startup

**Progress not updating?**
- Frontend should auto-update via SSE
- Check browser console for SSE connection status
- Fallback polling should work if SSE fails
