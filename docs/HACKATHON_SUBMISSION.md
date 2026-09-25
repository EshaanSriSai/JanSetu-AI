# JanSetu AI — Hackathon Submission Checklist

## 1. Repository

Push the contents of this folder to a public GitHub repository.

Before pushing, verify that none of these exist in Git:
- `.env`
- `service-account.json`
- `firebase-adminsdk*.json`
- API keys
- passwords

## 2. Firebase

- Create/confirm Firebase project `jansetu-ai-352e4`
- Enable Firestore
- Enable Firebase Authentication
- Enable Anonymous Authentication for the included demo flow, or replace with an approved sign-in method
- Register a Web App and copy its public Firebase config into `frontend/.env`

## 3. Backend

Set:
- `GEMINI_API_KEY`
- `FIREBASE_PROJECT_ID`
- `CORS_ORIGINS`

For Cloud Run, prefer the Cloud Run service identity / Application Default Credentials for Firestore rather than shipping a service-account JSON file.

## 4. Frontend

Set all `VITE_FIREBASE_*` values in `frontend/.env`.

Run:

```bash
npm install
npm run build
```

## 5. Demo story

1. Citizen enters a complaint in Telugu/Hindi/English.
2. Gemini structures the complaint.
3. JanSetu assigns severity, urgency and a priority signal.
4. Firestore stores the citizen request.
5. Dashboard aggregates demand by location/category.
6. JanSetu generates evidence-backed public project recommendations.

## 6. 3–5 minute demo

- 0:00–0:30: Problem
- 0:30–1:15: Citizen complaint
- 1:15–2:00: Gemini analysis
- 2:00–2:45: Firestore persistence
- 2:45–3:45: Hotspots and recommendations
- 3:45–4:30: Architecture, scale and impact
