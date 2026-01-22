# YouTube Dubbing Platform API

A FastAPI backend service for managing YouTube content for dubbing/localization platforms. This service handles user authentication via OAuth 2.0, fetches video inventory, and manages video uploads to specific regional channels.

## Features

- **OAuth 2.0 Authentication**: Secure Google/YouTube authentication with refresh token management
- **Video Management**: List and upload videos to YouTube
- **Localization Support**: Upload captions/subtitles for video localization
- **Async/Await**: All endpoints use async/await for optimal performance
- **Type Safety**: Full type hinting with Pydantic models
- **Auto Documentation**: Swagger UI available at `/docs`

## Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **Database**: SQLite (local dev) or Firebase Firestore (production)
- **YouTube API**: Google API Python Client (v3)
- **Authentication**: OAuth 2.0 with Google

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
- `GOOGLE_REDIRECT_URI`: OAuth redirect URI (e.g., `http://localhost:8000/auth/callback`)
- `YOUTUBE_API_KEY`: Your YouTube Data API v3 key
- `SECRET_KEY`: Secret key for application security
- `DATABASE_URL`: Database connection string (defaults to SQLite)

### 3. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **YouTube Data API v3**
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URI: `http://localhost:8000/auth/callback`
6. Copy Client ID and Client Secret to `.env`

### 4. Initialize Database

The database will be automatically initialized on first run. For SQLite, a file `youtube_dubbing.db` will be created.

### 5. Run the Application

**With hot reload (recommended for development):**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Or run directly:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`

**Hot reload is enabled** - the server automatically restarts when you make code changes.

See [START.md](START.md) for detailed startup instructions.

## API Endpoints

### Authentication

- `GET /auth/login` - Initiate OAuth 2.0 login flow
- `GET /auth/callback` - Handle OAuth callback and store tokens
- `GET /auth/me?user_id={user_id}` - Get current user information

### Videos

- `GET /videos/list?user_id={user_id}&limit=10` - List user's uploaded videos
- `POST /videos/upload` - Upload video to YouTube (multipart/form-data)

### Localization

- `POST /localization/captions/upload` - Upload caption track to video

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
youtube-dubbing-platform/
├── main.py                 # FastAPI application entry point
├── config.py                # Configuration settings
├── database.py            # Database models and session management
├── routers/
│   ├── auth.py           # Authentication router
│   ├── videos.py         # Video management router
│   └── localization.py   # Localization router
├── schemas/
│   ├── auth.py           # Authentication schemas
│   ├── videos.py         # Video schemas
│   └── localization.py   # Localization schemas
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## OAuth 2.0 Flow

1. User visits `/auth/login`
2. Redirected to Google OAuth consent screen
3. User grants permissions
4. Google redirects to `/auth/callback` with authorization code
5. Backend exchanges code for access/refresh tokens
6. Tokens stored in database associated with user_id

## Error Handling

All endpoints include comprehensive error handling:
- **400**: Bad Request (invalid parameters, OAuth errors)
- **404**: Not Found (user/video not found)
- **500**: Internal Server Error (API failures, database errors)
- **503**: Service Unavailable (YouTube API quota exceeded)

## Development

### Running Tests

```bash
# Add tests as needed
pytest
```

### Code Style

This project follows PEP 8 style guidelines. Consider using:
- `black` for code formatting
- `flake8` for linting
- `mypy` for type checking

## License

MIT
