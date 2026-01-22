# Mock Data Scripts

Scripts for seeding Firebase Auth and Firestore with mock data for development and UI testing.

## Available Scripts

### 1. `seed_mock_data.py` (Basic)
Creates a minimal new user for testing authentication flow.

**What it creates:**
- 1 new user (user1@gmail.com) without YouTube connection
- No jobs or processing data

**Use case:** Testing authentication and initial user onboarding

### 2. `seed_rich_mock_data.py` (Comprehensive) ⭐
Creates a complete mock dataset with processing jobs, videos, and multiple statuses.

**What it creates:**
- Test user with full account setup
- YouTube connection (1 main channel)
- Language channels (4 channels: Spanish, French, German, Japanese)
- Processing jobs (5 jobs with various statuses)
- Localized videos for completed/processing jobs

**Use case:** Building and testing the full UI with realistic data

## Usage

### Running the Rich Mock Data Script

```bash
cd /Users/amoltafet1/youtube-dubbing-platform
python3 scripts/seed_rich_mock_data.py
```

### Test Credentials

After running the script, use these credentials:

```
Email: testuser@example.com
Password: testpass123
```

## Mock Data Details

### Processing Jobs Created

The script creates 5 processing jobs with different statuses:

| Video | Status | Progress | Languages |
|-------|--------|----------|-----------|
| Never Gonna Give You Up | ✅ Completed | 100% | Random 2-4 languages |
| GANGNAM STYLE | 🔄 Processing | 65% | Random 2-4 languages |
| Despacito | ⬆️ Uploading | 85% | Random 2-4 languages |
| Uptown Funk | ⬇️ Downloading | 25% | Random 2-4 languages |
| Counting Stars | ⏳ Pending | 0% | Random 2-4 languages |

### Localized Videos

- **Processing jobs**: Create localized video records with status "processing"
- **Uploading jobs**: Create localized videos with status "uploaded" and mock video IDs
- **Completed jobs**: Create localized videos with status "published" and mock video IDs

### Language Channels

Four pre-configured language channels:
- 🇪🇸 Spanish (es) - Spanish Dubbing Channel
- 🇫🇷 French (fr) - French Dubbing Channel
- 🇩🇪 German (de) - German Dubbing Channel
- 🇯🇵 Japanese (ja) - Japanese Dubbing Channel

## API Endpoints to Test

After seeding data, test these endpoints:

### 1. Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "testpass123"
  }'
```

### 2. Dashboard
```bash
curl http://localhost:8000/dashboard \
  -H "Authorization: Bearer <id_token>"
```

### 3. Jobs List
```bash
curl http://localhost:8000/jobs \
  -H "Authorization: Bearer <id_token>"
```

### 4. Videos List
```bash
curl http://localhost:8000/videos/list \
  -H "Authorization: Bearer <id_token>"
```

## Re-running the Script

The script is **idempotent** - it checks for existing data and reuses it:
- If user exists, it uses the existing user
- If YouTube connection exists, it skips creation
- If language channels exist, it skips creation
- Jobs and videos are always created fresh

To start completely fresh, delete the user from Firebase Console first.

## Troubleshooting

### Import Errors
Make sure you're running from the project root:
```bash
cd /Users/amoltafet1/youtube-dubbing-platform
python3 scripts/seed_rich_mock_data.py
```

### Firebase Not Initialized
Ensure your Firebase credentials file exists:
```bash
ls vox-translate-b8c94-firebase-adminsdk-*.json
```

### Permission Errors
The script requires Firebase Admin SDK permissions for:
- Creating users in Firebase Auth
- Writing to Firestore collections

Make sure your service account has the necessary permissions.
