# Mierae Solar AI Bot

A full-stack Web Application integrating Groq's high-speed AI models for Text Generation and Speech-to-Text transcription. The bot acts as an incredibly fast, highly persuasive conversational AI designed out of the box to capture leads for Mierae Solar's services.

## Details & Features

* **Real-time Voice Interactions**: Talk directly to the AI through the browser. Audio is recorded through standard browser MediaRecorder APIs and processed on the backend using the lightning-fast Groq Whisper API.
* **Multilingual TTS**: Bot verbally replies in Hindi, Telugu, Urdu, and English flawlessly using `gTTS` capabilities, with audio streamed right back to the site.
* **Persistent Lead Storage**: Leads are stored in **PostgreSQL** on Render for permanent storage, with automatic fallback to a local `leads.db` SQLite file during development.
* **Dark Mode Glassmorphism UI**: Beautifully designed frontend built with vanilla HTML/CSS (`static/index.html` & `static/style.css`) featuring deep shadows, radiant accents, and dynamic interaction micro-animations.
* **CORS Configured**: Fully decoupled architecture allowing your frontend and backend APIs to scale independently if needed!

---

## Complete Local Setup Guide

Follow the instructions below to run this project perfectly on your local machine:

1. **Install Dependencies**
Ensure you have Python 3.10+ installed. Open your terminal in this repository's folder and run:
`pip install -r requirements.txt`

2. **Supply your API Keys**
Copy the `.env.example` file and create a new `.env` file within the root directory. Paste your Groq API Key:
`GROQ_API_KEY=your_key_here`

3. **Run the Uvicorn Server**
Boot up the FastAPI server via Uvicorn. This script automatically binds the ASGI socket:
`python api.py`
Wait for it to say `Application startup complete.`

4. **Experience the UI**
Open `http://localhost:8000` in any web-browser! Click the mic button to speak!

> **Local Dev Note:** Without a `DATABASE_URL` set, the app automatically uses a local `leads.db` SQLite file.

---

## Render Deployment Guide

This repository is optimized for direct push-to-deploy on Render.com Web Services. Leads are stored permanently in a managed PostgreSQL database.

### Step 1 — Create a Free PostgreSQL Database

1. In the [Render Dashboard](https://dashboard.render.com), click **New → PostgreSQL**.
2. Give it a name (e.g. `mierae-leads-db`) and choose the **Free** plan.
3. Click **Create Database** and wait for it to become available.
4. Copy the **Internal Database URL** from the database info page — you'll paste it below.

### Step 2 — Deploy the Web Service

1. Click **New → Web Service** and connect this Git repository.
2. For the **Build Command**, input:
   `pip install -r requirements.txt`
3. For the **Start Command**, input:
   `uvicorn api:app --host 0.0.0.0 --port 10000`
4. Click **Advanced** → **Add Environment Variables**:

   | Key | Value |
   |---|---|
   | `GROQ_API_KEY` | Your real Groq API Key |
   | `DATABASE_URL` | Internal Database URL copied from Step 1 |

5. Click **Create Web Service**! Render will deploy your site and provide a live `https://...` link.

> Leads are now stored **permanently** in PostgreSQL and will survive all future redeploys.
