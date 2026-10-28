# Talent Growth — 24/7 Production Deployment & Hosting Architecture Guide

This guide details the root cause of the Streamlit Community Cloud inactivity sleep screen, provides an enterprise comparison of reliable 24/7 hosting alternatives, and includes complete step-by-step instructions for deploying Talent Growth on persistent cloud infrastructure without sleep interruptions or data loss.

---

## 1. Root Cause Analysis: The "Zzzz" Inactivity Sleep Issue

### Why Does the App Sleep?
The current deployment runs on **Streamlit Community Cloud** (`https://share.streamlit.io`).

Streamlit Community Cloud is a free, shared-tier container platform intended primarily for hobbyist prototyping and temporary demonstrations. Its platform architecture operates under strict resource constraints:
1. **Automated Container Shutdown**: When an app receives no interactive user traffic for a period (as documented by Streamlit, apps sleep after several days of inactivity, or whenever idle resources are reclaimed), Streamlit’s ingress router stops the container to reclaim CPU and memory.
2. **The "Zzzz" Interstitial Screen**: Subsequent visitors to the URL are redirected to a sleeping proxy screen displaying:
   > *"Zzzz — This app has gone to sleep due to inactivity. It may take a minute or two to wake up."*
   Waking the container requires a visitor to manually click *"Yes, get this app back up!"*, wait 60–180 seconds for image pulls and dependency installations, and re-establish WebSocket connections.
3. **Iframe Failure**: When embedded inside an iframe (such as via your Vercel frontend `index.html`), the waking prompt often breaks or gets blocked by browser iframe sandboxing, preventing end-users from accessing the platform.
4. **Why Automated Pingers Fail**: Third-party keep-alive bots or GitHub Actions (e.g. `gpenessot/streamlit-keep-alive`) attempt periodic HTTP requests. However, modern Streamlit routing relies on active WebSocket sessions; simple HTTP pings fail to satisfy traffic heuristics, and abusive bot traffic is systematically filtered.

### The Ephemeral Storage Danger
On Streamlit Community Cloud, **container filesystems are completely ephemeral**. Any changes saved by users—such as newly registered accounts, updated skills, assessments, performance reviews, or Resume Studio drafts—written to local SQLite database files (`data/talentsphere.db`) are **permanently wiped out** whenever the container sleeps, restarts, or rebuilds.

> [!CAUTION]
> Free hosting tiers that lack persistent volume storage will inevitably cause user data loss upon container recycling. To achieve a reliable, always-on 24/7 production application, Talent Growth must be deployed on a platform with continuous runtime guarantees and persistent disk storage.

---

## 2. 24/7 Hosting Options Comparison & Evaluation

| Hosting Platform | Always-On (No Sleep) | Monthly Cost | Persistent Storage Support | Deployment Complexity | Maintenance Requirements |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Render (Web Service)** *(Recommended)* | **Yes** (Paid Starter) | **~$7.25 – $8.00/mo** ($7 compute + $0.25/GB disk) | **Yes** (Persistent SSD Disk mounted to `/app/data`) | **Low** (Git-push auto deploy via `render.yaml`) | **Zero** (Fully managed PaaS, automated SSL, zero OS patching) |
| **Railway (Hobby / Pro)** | **Yes** (Standard Plan) | **~$5.00 – $7.00/mo** ($5 base credit + usage) | **Yes** (Persistent Volume mounted to `/app/data`) | **Low** (Git-push auto deploy via `railway.json`) | **Zero** (Fully managed PaaS, automated SSL) |
| **Cloud VPS (DigitalOcean / Hetzner / AWS Lightsail)** | **Yes** (100% Dedicated VM) | **~$4.00 – $6.00/mo** ($4–$6/mo all-inclusive) | **Yes** (Native persistent NVMe/SSD root drive) | **Medium** (Docker Compose or automated `setup_vps.sh`) | **Low-Medium** (Run system updates periodically) |
| **Fly.io** | **Yes** (`auto_stop_machines=false`) | **~$3.50 – $5.00/mo** | **Yes** (Fly Volume mounted to `/app/data`) | **Medium** (`fly.toml` + Fly CLI) | **Zero** (Managed MicroVMs) |

---

## 3. Recommended Platform Selection

### Primary Recommendation: Render (Web Service + Persistent Disk)
* **Estimated Cost**: ~$7.25/month ($7.00/mo Starter compute + $0.25/mo 1GB persistent disk).
* **Why Render**:
  - **Zero Server Management**: Automated container builds directly from your GitHub repository using our pre-configured [render.yaml](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/render.yaml).
  - **Persistent Disk**: Database records (`/app/data/talentsphere.db`) and backups persist permanently across code updates and restarts.
  - **No Sleep**: Paid Starter instances run continuously 24 hours a day, 7 days a week, 365 days a year.
  - **Automatic SSL & Custom Domains**: Instant `https://` provisioning.
  - **Native Health Checks**: Directly monitors `/_stcore/health`.

### Alternative Recommendation: DigitalOcean / Hetzner VPS (Maximum Control & Cost Efficiency)
* **Estimated Cost**: $4.00 to $6.00/month (e.g. DigitalOcean 1 vCPU / 1GB RAM Droplet at $4 or $6/mo; Hetzner Cloud at ~€3.50/mo).
* **Why VPS**: Complete root ownership, permanent local SSD storage, systemd auto-restart supervision, and full Docker Compose support.

---

## 4. Production Artifacts & Configuration Added

The following enterprise configuration files have been prepared and validated in your repository:

1. **[Dockerfile](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/Dockerfile)**:
   - Built on `python:3.11-slim` with multi-arch Linux/ARM support.
   - Non-root user (`appuser`, UID 1000) for strict enterprise security.
   - Configures `/app/data` with persistent permissions.
   - Built-in Docker `HEALTHCHECK` using `healthcheck.py`.
2. **[.dockerignore](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/.dockerignore)**:
   - Excludes virtual environments, IDE files, cache files, and local `.env` secrets from container images.
3. **[docker-compose.yml](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/docker-compose.yml)**:
   - Pre-configured `talent-growth` service with `restart: unless-stopped`.
   - Named persistent volume `talent_growth_data` mapped to `/app/data`.
   - Standard port mapping (`8501:8501`) and environment variable ingestion.
4. **[render.yaml](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/render.yaml)**:
   - Declarative Render Blueprint for 1-click deployment with a 1GB persistent disk.
5. **[railway.json](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/railway.json)**:
   - Production deployment schema with restart policy and health checks.
6. **[fly.toml](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/fly.toml)**:
   - Fly.io MicroVM specification with `auto_stop_machines = false` to guarantee continuous uptime.
7. **[scripts/run_app.sh](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/scripts/run_app.sh)**:
   - POSIX container startup script that automatically detects the host `$PORT`, runs pre-flight database migrations, and launches Streamlit with production headless flags.
8. **[scripts/db_backup.py](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/scripts/db_backup.py)**:
   - Non-blocking online SQLite snapshot utility using SQLite's native backup API. Retains the last 14 snapshots with automated pruning.
9. **[healthcheck.py](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/healthcheck.py)**:
   - Diagnostic script verifying both Streamlit HTTP availability and SQLite database integrity without exposing any employee credentials or sensitive data.
10. **[deploy/systemd/talent-growth.service](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/deploy/systemd/talent-growth.service)** & **[deploy/nginx/talent-growth.conf](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/deploy/nginx/talent-growth.conf)**:
    - Production systemd unit file and Nginx reverse proxy configuration with WebSocket support for Linux VPS deployments.

---

## 5. Step-by-Step Deployment Runbooks

### Runbook A: Deploying to Render (Recommended)

1. **Sign in to Render**:
   - Go to [render.com](https://render.com) and sign in with your GitHub account.
2. **Create New Blueprint / Web Service**:
   - In the Render Dashboard, click **New +** → **Blueprint**.
   - Select your GitHub repository: `madhan023-mn/Talent-Management-Career-Growth-Platform`.
   - Render will automatically detect [render.yaml](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/render.yaml).
3. **Configure Plan & Disk**:
   - Service Name: `talent-growth-platform`
   - Plan: **Starter** ($7/mo — ensures 24/7 always-on operation without sleep).
   - Disk: Render will automatically configure a 1GB Persistent Disk mounted to `/app/data`.
4. **Set Environment Variables**:
   Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: *(Optional)* Your Gemini API key for AI Coaching and Resume Auditing.
   - `APP_URL`: Your production URL (e.g. `https://talent-growth-platform.onrender.com`).
   - `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`: *(Optional)* For enterprise email notifications.
5. **Deploy**:
   - Click **Apply**. Render will build the Docker container and start your 24/7 instance.
   - Once deployment finishes, your app will be live at `https://talent-growth-platform.onrender.com`.

---

### Runbook B: Deploying to a Linux VPS (DigitalOcean / Hetzner / AWS)

If you prefer a dedicated Linux server:

1. **Provision a VPS**:
   - Create an Ubuntu 22.04 or 24.04 server (1 vCPU, 1GB–2GB RAM).
2. **Clone Repository on Server**:
   ```bash
   git clone https://github.com/madhan023-mn/Talent-Management-Career-Growth-Platform.git /var/www/talent-growth
   cd /var/www/talent-growth
   ```
3. **Run Automated Provisioning**:
   ```bash
   sudo bash deploy/setup_vps.sh yourdomain.com
   ```
   *This script automatically installs Python 3.11, Nginx, Certbot SSL, systemd service, firewall rules, and an automated 2:00 AM daily backup cron job.*
4. **Issue Free SSL Certificate**:
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```
5. **Verify Status**:
   ```bash
   sudo systemctl status talent-growth
   curl -I http://127.0.0.1:8501/_stcore/health
   ```

---

### Runbook C: Deploying to Railway

1. Sign in to [railway.app](https://railway.app) via GitHub.
2. Click **New Project** → **Deploy from GitHub repo** → select `Talent-Management-Career-Growth-Platform`.
3. In service **Settings** → **Volumes**:
   - Click **Add Volume**.
   - Mount Path: `/app/data`.
4. In **Variables**, add any required secrets (`GEMINI_API_KEY`, `APP_URL`).
5. In **Networking**, click **Generate Domain** (e.g. `talent-growth.up.railway.app`).

---

## 6. Updating Your Vercel Frontend Iframe

Once your 24/7 backend is running on Render, Railway, or your VPS:

1. Open [index.html](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/index.html).
2. Update line 10 with your new permanent URL:
   ```html
   <meta name="app-backend-url" content="https://talent-growth-platform.onrender.com" />
   ```
3. Commit and push to GitHub. Vercel will automatically redeploy the frontend wrapper.
4. Visitors opening `https://talent-growth.vercel.app` will now load the live platform immediately with **zero loading delays, zero sleep screens, and full 24/7 availability**.

---

## 7. Database Protection, WAL Mode & Recovery Procedures

### SQLite High-Concurrency WAL Mode
In [`services/core.py`](file:///c:/Users/madha/OneDrive/Desktop/infosys_project/services/core.py#L156-L163), the database engine is configured with:
- `PRAGMA journal_mode = WAL`: Write-Ahead Logging allows simultaneous non-blocking concurrent reads while writes occur.
- `PRAGMA busy_timeout = 30000`: Extends busy wait timeout to 30 seconds to prevent `database is locked` errors during high traffic.
- `PRAGMA synchronous = NORMAL`: Maximizes write throughput while remaining completely crash-safe in WAL mode.

### Online Snapshots & Backups
You can create consistent database backups anytime without stopping the server:
```bash
# Create a live snapshot
python scripts/db_backup.py --backup

# List existing snapshots
python scripts/db_backup.py --list

# Restore from a backup if needed
python scripts/db_backup.py --restore data/backups/talentsphere_backup_YYYYMMDD_HHMMSS.db
```

---

## 8. External Monitoring & Alerting Setup

To ensure you are notified immediately of any network or infrastructure issues:

1. Create a free account at [UptimeRobot](https://uptimerobot.com) or [Better Stack](https://betterstack.com).
2. Click **Add New Monitor**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `Talent Growth 24/7 Platform`
   - **URL / IP**: `https://<your-deployed-domain>/_stcore/health`
   - **Monitoring Interval**: Every 5 minutes (or 1 minute on paid).
3. **Alert Contacts**: Add your email address or Slack/Discord webhook.
4. If an unexpected outage occurs, UptimeRobot will notify you immediately.
