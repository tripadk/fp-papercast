# PaperCast

PaperCast is a full-stack starter app for turning research papers into summaries, podcast-style audio, and interactive Q&A.

## Stack

- Frontend: Next.js (App Router), React, TypeScript, NextAuth (Google OAuth)
- Backend: FastAPI, Python, PDF text extraction, LLM summary/dialogue generation, TTS audio generation

## Project Structure

- `frontend/` - Next.js client app
- `backend/` - FastAPI API server

## Quick Start

### 1) Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # macOS/Linux
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend

```bash
cd frontend
npm install
copy .env.example .env.local  # Windows
# cp .env.example .env.local  # macOS/Linux
npm run dev
```

Open `http://localhost:3000`.

## Environment Variables

### Frontend (`frontend/.env.local`)

- `NEXTAUTH_URL=http://localhost:3000`
- `NEXTAUTH_SECRET=change-me`
- `GOOGLE_CLIENT_ID=...`
- `GOOGLE_CLIENT_SECRET=...`
- `NEXT_PUBLIC_BACKEND_URL=http://localhost:8000`

### Backend (`backend/.env`)

- `OPENAI_API_KEY=` (optional but recommended)
- `OPENAI_MODEL=gpt-4o-mini`
- `UPLOAD_DIR=backend/data/uploads`
- `AUDIO_DIR=backend/data/audio`
- `CORS_ORIGINS=http://localhost:3000`

## Notes

- If `OPENAI_API_KEY` is not set, summary/dialogue endpoints use deterministic fallback text.
- Podcast audio generation uses the ElevenLabs API and requires `ELEVENLABS_API_KEY` in `backend/.env`.
- The backend saves uploaded PDFs to `UPLOAD_DIR` and generated MP3 files to `AUDIO_DIR`.
