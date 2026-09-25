# JanSetu AI

**AI-powered citizen infrastructure intelligence for India**

JanSetu AI turns citizen complaints into structured, prioritized development signals. Citizens can submit issues in their own language; Gemini extracts the language, category, location, severity and urgency, while Firestore stores the requests and the dashboard surfaces demand hotspots and project recommendations.

## Google Cloud / Firebase stack

- Gemini API via Google AI Studio
- Firebase Authentication
- Cloud Firestore
- Cloud Run
- FastAPI
- React + Vite

## What is implemented

- Multilingual citizen complaint analysis
- Structured Gemini JSON output
- Priority scoring
- Firestore persistence
- Hotspot aggregation
- Project recommendations
- Firebase Authentication on the web client
- Firebase ID-token verification on the backend
- Health endpoint
- Cloud Run Dockerfile
- CORS configuration
- Demo/sample complaints

## Repository safety

Never commit `.env`, Firebase service-account JSON, API keys, or other credentials. Use the provided `.env.example` files.

## Local run

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with a fresh Gemini API key and Firebase project ID. For local Firestore access, either use Google Application Default Credentials or a private service-account JSON referenced by `GOOGLE_APPLICATION_CREDENTIALS`.

Then:

```powershell
.\venv\Scripts\python.exe -m uvicorn main:app --reload
```

Backend: `http://127.0.0.1:8000`

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Set the Firebase web-app values in `frontend/.env`.

## Production

Build the frontend:

```powershell
npm run build
```

Deploy the backend to Cloud Run using the included `backend/Dockerfile`. Set `GEMINI_API_KEY`, `FIREBASE_PROJECT_ID`, and appropriate Cloud Run service identity permissions. Set `CORS_ORIGINS` to the deployed frontend origin.

For the hackathon, enable Firebase Authentication (Anonymous is sufficient for a demo if allowed by the event rules) and Firestore in the Firebase console.

## Important limitation

The repository contains the complete application code, but deployment and Firebase console configuration are account-specific actions that must be completed in the user's Google Cloud/Firebase account. Do not commit credentials.
