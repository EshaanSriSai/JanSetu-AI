# Architecture

```text
Citizen
   |
   v
React / Vite web app
   |
Firebase Authentication
   |
   v
Cloud Run / FastAPI
   |
   +---- Gemini API ----> Structured civic analysis
   |
   +---- Firestore -----> citizen_requests
                              |
                              v
                       Dashboard aggregation
                              |
                              v
                    Hotspots + project signals
```

The backend is stateless. Firestore is the system of record. Gemini is used for structured extraction and classification. Priority calculations are deterministic after the AI classification so the dashboard can explain how the signal was formed.
