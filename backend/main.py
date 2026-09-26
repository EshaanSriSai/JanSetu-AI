import os
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai

import firebase_admin
from firebase_admin import credentials, firestore, auth


load_dotenv()


API_KEY = os.getenv("GEMINI_API_KEY")
PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured.")


client = genai.Client(api_key=API_KEY)


# ---------------------------------------------------------
# Firebase initialization
# ---------------------------------------------------------

if not firebase_admin._apps:
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    if service_account_path and os.path.exists(service_account_path):
        firebase_admin.initialize_app(
            credentials.Certificate(service_account_path),
            {"projectId": PROJECT_ID} if PROJECT_ID else None,
        )
    else:
        firebase_admin.initialize_app(
            options={"projectId": PROJECT_ID} if PROJECT_ID else None
        )


db = firestore.client()


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="JanSetu AI",
    version="2.0.0",
    description="Citizen infrastructure intelligence platform",
)


# ---------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------

PRODUCTION_ORIGIN = "https://jansetu-ai-1ky6.onrender.com"

configured_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

allowed_origins = list(
    dict.fromkeys(
        configured_origins
        + [
            PRODUCTION_ORIGIN,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Data models
# ---------------------------------------------------------

class CitizenRequest(BaseModel):
    message: str = Field(min_length=3, max_length=5000)
    source: str = Field(default="text", max_length=50)


class CitizenAnalysis(BaseModel):
    language: str
    category: str
    location: str
    problem_summary: str
    severity: str
    urgency: str


class Complaint(CitizenAnalysis):
    id: str
    original_message: str
    source: str
    priority_score: int
    created_at: str
    user_id: Optional[str] = None


# ---------------------------------------------------------
# Priority scoring
# ---------------------------------------------------------

SEVERITY_POINTS = {
    "Low": 10,
    "Medium": 25,
    "High": 40,
    "Critical": 50,
}

URGENCY_POINTS = {
    "Low": 5,
    "Medium": 15,
    "High": 25,
}


def priority_score(a: CitizenAnalysis) -> int:
    return min(
        100,
        SEVERITY_POINTS.get(a.severity, 10)
        + URGENCY_POINTS.get(a.urgency, 5)
        + 25,
    )


# ---------------------------------------------------------
# Firebase authentication
# ---------------------------------------------------------

def verify_user(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """
    Verify a Firebase ID token.

    Local development can use DEV_BYPASS_AUTH=true only.
    """

    if os.getenv("DEV_BYPASS_AUTH", "false").lower() == "true":
        return "local-demo-user"

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Firebase ID token required.",
        )

    token = authorization.split(" ", 1)[1]

    try:
        decoded = auth.verify_id_token(token)
        return decoded["uid"]

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired Firebase ID token.",
        )


# ---------------------------------------------------------
# Gemini analysis
# ---------------------------------------------------------

def analyze_with_gemini(message: str) -> CitizenAnalysis:

    prompt = f"""
You are JanSetu AI, a multilingual citizen infrastructure intelligence system for India.

Analyze this citizen complaint:

{message}

Return structured data:
- language
- category
- location
- problem_summary
- severity
- urgency

Allowed categories:
Roads, Water, Electricity, Healthcare, Education, Sanitation, Public Transport, Other

Allowed severity:
Low, Medium, High, Critical

Allowed urgency:
Low, Medium, High

If location is not mentioned, use "Unspecified".
Do not invent a precise location.
"""

    # Bounded retry:
    # temporary 429/503 capacity failures must not hang the app.

    models = [
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model in models:

        for attempt in range(2):

            try:

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": CitizenAnalysis,
                        "http_options": {
                            "timeout": 20000
                        },
                    },
                )

                return CitizenAnalysis.model_validate_json(
                    response.text
                )

            except Exception as exc:

                last_error = exc

                time.sleep(
                    1.5 * (attempt + 1)
                )

    raise HTTPException(
        status_code=503,
        detail=(
            "Gemini temporarily unavailable. "
            f"Please retry shortly. {last_error}"
        ),
    )


# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------

@app.get("/")
def root():

    return {
        "project": "JanSetu AI",
        "status": "running",
        "version": "2.0.0",
    }


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------

@app.get("/health")
def health():

    try:

        db.collection(
            "citizen_requests"
        ).limit(1).get()

        firestore_ok = True

    except Exception:

        firestore_ok = False

    return {
        "status": "healthy",
        "firestore_connected": firestore_ok,
    }


# ---------------------------------------------------------
# Analyze citizen request
# ---------------------------------------------------------

@app.post("/analyze", response_model=dict)
def analyze_request(
    request: CitizenRequest,
    user_id: str = Depends(verify_user),
):

    analysis = analyze_with_gemini(
        request.message
    )

    complaint = {
        "id": f"req_{uuid.uuid4().hex[:12]}",
        **analysis.model_dump(),
        "original_message": request.message,
        "source": request.source,
        "priority_score": priority_score(
            analysis
        ),
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "user_id": user_id,
    }

    db.collection(
        "citizen_requests"
    ).document(
        complaint["id"]
    ).set(complaint)

    return {
        "success": True,
        "saved": True,
        "complaint": complaint,
    }


# ---------------------------------------------------------
# Citizen requests
# ---------------------------------------------------------

@app.get("/requests")
def get_requests(
    limit: int = 100,
    user_id: str = Depends(verify_user),
):

    docs = (
        db.collection("citizen_requests")
        .order_by(
            "created_at",
            direction=firestore.Query.DESCENDING,
        )
        .limit(min(limit, 200))
        .stream()
    )

    requests = [
        document.to_dict()
        for document in docs
    ]

    return {
        "count": len(requests),
        "requests": requests,
    }


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

@app.get("/dashboard")
def dashboard(
    user_id: str = Depends(verify_user),
):

    docs = (
        db.collection(
            "citizen_requests"
        ).stream()
    )

    requests = [
        document.to_dict()
        for document in docs
    ]

    category_counts = Counter(
        r.get("category", "Other")
        for r in requests
    )

    severity_counts = Counter(
        r.get("severity", "Low")
        for r in requests
    )

    grouped = {}

    for r in requests:

        key = (
            f'{r.get("location", "Unspecified")}'
            f'|{r.get("category", "Other")}'
        )

        if key not in grouped:

            grouped[key] = {
                "location": r.get(
                    "location",
                    "Unspecified",
                ),
                "category": r.get(
                    "category",
                    "Other",
                ),
                "requests": 0,
                "high_priority": 0,
                "total_priority": 0,
            }

        grouped[key]["requests"] += 1

        grouped[key]["total_priority"] += int(
            r.get("priority_score", 0)
        )

        if int(
            r.get("priority_score", 0)
        ) >= 65:

            grouped[key]["high_priority"] += 1

    hotspots = sorted(
        grouped.values(),
        key=lambda x: (
            x["high_priority"],
            x["requests"],
            x["total_priority"],
        ),
        reverse=True,
    )

    average_priority = (
        round(
            sum(
                r.get("priority_score", 0)
                for r in requests
            )
            / len(requests),
            1,
        )
        if requests
        else 0
    )

    return {
        "total_requests": len(requests),
        "category_counts": dict(
            category_counts
        ),
        "severity_counts": dict(
            severity_counts
        ),
        "hotspots": hotspots[:20],
        "average_priority": average_priority,
    }


# ---------------------------------------------------------
# Recommendations
# ---------------------------------------------------------

@app.get("/recommendations")
def recommendations(
    user_id: str = Depends(verify_user),
):

    data = dashboard(user_id)

    action_map = {

        "Water":
            "Upgrade drinking-water supply and inspect local distribution lines.",

        "Roads":
            "Prioritize road repair and inspect damaged or high-traffic stretches.",

        "Electricity":
            "Inspect distribution reliability and transformer capacity.",

        "Healthcare":
            "Assess nearby primary-healthcare capacity and service gaps.",

        "Education":
            "Assess school infrastructure and access to essential facilities.",

        "Sanitation":
            "Prioritize sanitation, drainage and waste-management improvements.",

        "Public Transport":
            "Review public-transport coverage and route frequency.",

        "Other":
            "Conduct a local needs assessment for the reported service gap.",
    }

    result = []

    for h in data["hotspots"][:8]:

        if h["location"] == "Unspecified":
            continue

        result.append({

            "location":
                h["location"],

            "category":
                h["category"],

            "evidence_requests":
                h["requests"],

            "high_priority_requests":
                h["high_priority"],

            "priority_signal":
                min(
                    100,
                    h["total_priority"]
                    // max(
                        1,
                        h["requests"],
                    )
                    + min(
                        30,
                        h["requests"] * 3,
                    ),
                ),

            "recommended_project":
                action_map.get(
                    h["category"],
                    action_map["Other"],
                ),
        })

    return {
        "recommendations": result
    }
