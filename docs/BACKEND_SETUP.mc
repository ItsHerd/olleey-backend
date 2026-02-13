# Olleey Backend Service

A high-performance FastAPI backend for the Olleey platform. This service manages YouTube content, video dubbing, and localization workflows. It handles secure OAuth 2.0 authentication with Google, video inventory management, and caption track uploads.

**Live API:** [https://api.olleey.com/docs](https://api.olleey.com/docs)

---



## 💻 Local Development Setup

Follow these steps to run the backend on your laptop.

### 1. Prerequisites
* Python 3.10 or higher
* Git

### 2. Installation
```bash
# Clone the repository
git clone [https://github.com/YOUR_USERNAME/olleey-backend.git](https://github.com/YOUR_USERNAME/olleey-backend.git)
cd olleey-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt


☁️ Deployment & Infrastructure
This project uses GitHub Actions for Continuous Deployment to Google Cloud.

Architecture
VM: Google Cloud Compute Engine (Debian 12)

Process Manager: Systemd (fastapi_app.service) keeps the app running.

Reverse Proxy: Nginx listens on Port 80, forwards to Port 8000.

DNS/SSL: Cloudflare manages the domain and SSL (Flexible Mode).

How Deployment Works
Push code to main.

GitHub Actions SSHs into the server.

It pulls the latest code.

Secrets Injection: It dynamically creates the .env and service_account.json files on the server using GitHub Secrets.

It restarts the fastapi_app service.

Managing Secrets (Production)
To update API keys or Service Account credentials, do not SSH into the server. Update them in GitHub:

Go to Settings > Secrets and variables > Actions.

ENV_FILE: Contains the full production .env file content.

GCP_SA_KEY: Contains the full production Service Account JSON content.

SSH_KEY: The private SSH key for deployment.



Troubleshooting & Logs
To check the health of the production server:

View Live App Logs (Python Output):

Bash
sudo journalctl -u fastapi_app -f
View Web Traffic (Nginx):

Bash
sudo tail -f /var/log/nginx/access.log
Restart the Service Manually:

Bash
sudo systemctl restart fastapi_app



To Connect to Prod environment from local 
1. comment out test env variables and make prod accessbile in backend.
2. in front end leave NEXT_PUBLIC_API_URL to point to local
3. change the cloud key to point to prod

## Webhook Subscription Operations

- Ensure `WEBHOOK_BASE_URL` is set to a public HTTPS URL reachable by YouTube hub callbacks.
- Subscriptions are created with `hub.secret`; webhook notifications are signature-verified when secret exists.

### Renewing subscriptions

Run this periodically (recommended daily) to renew leases before expiry:

```bash
python3 scripts/renew_subscriptions.py --renew-before-hours 168
```

Optional authenticated API trigger for one user:

```http
POST /videos/subscriptions/renew?renew_before_hours=168
Authorization: Bearer <token>
```

### Optional built-in renewal scheduler

You can run automatic renewal inside the FastAPI process by adding these env vars:

```bash
ENABLE_SUBSCRIPTION_RENEWAL_SCHEDULER=true
SUBSCRIPTION_RENEWAL_INTERVAL_MINUTES=1440
SUBSCRIPTION_RENEW_BEFORE_HOURS=168
```

Production recommendation:
- Prefer external cron (calling `scripts/renew_subscriptions.py`) for stricter operational control.
- Use the built-in scheduler only when single-instance behavior is acceptable.