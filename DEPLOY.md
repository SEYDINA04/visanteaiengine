# Deploying Visanté AI Engine to Render

This guide covers deploying the Visanté AI Engine to [Render](https://render.com) so the mobile app can access the API endpoints.

## Git repo and Render host

- **Git repository**: `https://github.com/YOUR_USERNAME/visanteaiengine` — replace `YOUR_USERNAME` with your GitHub username or org.
- **Render host** (after deploy): `https://visante-ai-engine.onrender.com` — matches the service name in `render.yaml`; use your actual Render service URL if you chose a different name.

## Prerequisites

- [GitHub](https://github.com) account (or GitLab / Bitbucket)
- [Render](https://render.com) account
- [Google AI API key](https://aistudio.google.com/apikey) for Gemini

---

## Option A: Blueprint (Infrastructure as Code)

1. **Push your code to GitHub**

   ```bash
   git init
   git add main.py requirements.txt render.yaml runtime.txt .env.example
   git commit -m "Initial commit - Visanté AI Engine"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/visanteaiengine.git
   git push -u origin main
   ```

2. **Create a Render Blueprint**

   - Go to [Render Dashboard](https://dashboard.render.com)
   - **New** → **Blueprint**
   - Connect your GitHub repo
   - Render will detect `render.yaml` and create the web service

3. **Add `GOOGLE_API_KEY`**

   - Open your service → **Environment** tab
   - Add variable: `GOOGLE_API_KEY` = your Gemini API key
   - Click **Save Changes** (Render will redeploy)

4. **Get the live URL**

   - Your API will be at `https://visante-ai-engine.onrender.com` (or your custom service name)
   - Share this base URL with the mobile dev

---

## Option B: Manual Setup

1. **Push code to GitHub** (same as above)

2. **Create a Web Service on Render**

   - Go to [Render Dashboard](https://dashboard.render.com)
   - **New** → **Web Service**
   - Connect your repository

3. **Configure the service**

   | Field         | Value                                              |
   |---------------|----------------------------------------------------|
   | Name          | `visante-ai-engine`                                |
   | Region        | Oregon (or nearest to users)                       |
   | Branch        | `main`                                             |
   | Runtime       | Python 3                                           |
   | Build Command | `pip install -r requirements.txt`                  |
   | Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT`     |

4. **Environment variables**

   - Add `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) with your API key
   - Render will not commit this; it’s kept in the dashboard

5. **Health check (optional)**

   - **Settings** → **Health Check Path**: `/api/v1/status`
   - Render will use this for health checks

6. **Create Web Service**

   - Render will build and deploy automatically
   - Once ready, your API URL will be `https://visante-ai-engine.onrender.com` (or your custom service name)

---

## Option C: Docker

Use the included `Dockerfile` if you prefer a container-based deploy:

1. In the Render dashboard, create a **Web Service**
2. Set **Runtime** to **Docker**
3. Leave **Build Command** empty; Render will use the Dockerfile
4. Add `GOOGLE_API_KEY` under **Environment**
5. Deploy

---

## API Endpoints for Mobile Dev

Once deployed, the base URL is:

```
https://visante-ai-engine.onrender.com
```

(Use your actual Render service URL if you set a different service name.)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info and links |
| `/api/v1/status` | GET | Health check (use for connectivity tests) |
| `/docs` | GET | Interactive API docs (Swagger UI) |
| `/ws/triage` | WebSocket | Bi-directional audio stream (PCM 16-bit, mono, 16 kHz) |

### WebSocket Example

```text
wss://visante-ai-engine.onrender.com/ws/triage
```

- **Input**: Raw binary PCM 16-bit, mono, 16000 Hz
- **Output**: Raw binary audio bytes from Gemini
- Do not wrap audio in JSON; send/receive raw bytes only.

---

## Free Tier Notes

- **Render free tier**: Services spin down after ~15 minutes of inactivity
- First request after spin-down can take 30–60 seconds to wake
- For production, consider a paid plan for always-on service and WebSockets

---

## Troubleshooting

| Issue | Action |
|-------|--------|
| `GOOGLE_API_KEY required` | Add it in Render Dashboard → Environment |
| Build fails | Check Python 3.11 in `runtime.txt`; verify `requirements.txt` |
| WebSocket fails | Ensure the mobile app uses `wss://` on HTTPS |
| Slow first request | Normal on free tier; service is waking from idle |
