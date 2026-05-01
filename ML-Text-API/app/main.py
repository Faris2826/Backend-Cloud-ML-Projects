from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
import time
import json
from datetime import datetime
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import os

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs dir exists
os.makedirs("logs", exist_ok=True)

app = FastAPI(
    title="ML Text Classification API",
    description="Production-ready sentiment/text classification API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info({
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": round(duration * 1000, 2),
        "timestamp": datetime.utcnow().isoformat()
    })
    return response

# Model loading
MODEL_PATH = "models/text_classifier.pkl"
model = None
labels = ["negative", "positive"]

def load_model():
    global model
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        logger.info("Model loaded successfully")
    else:
        logger.warning("No trained model found at %s", MODEL_PATH)

@app.on_event("startup")
async def startup():
    os.makedirs("models", exist_ok=True)
    load_model()

# Schemas
class PredictRequest(BaseModel):
    text: str
    model_version: Optional[str] = "v1"

class PredictResponse(BaseModel):
    text: str
    prediction: str
    confidence: float
    model_version: str
    timestamp: str

class BatchPredictRequest(BaseModel):
    texts: List[str]

class BatchPredictResponse(BaseModel):
    results: List[PredictResponse]

class FeedbackRequest(BaseModel):
    text: str
    predicted: str
    actual: str

# Endpoints
@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    if not req.text or len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty text")

    proba = model.predict_proba([req.text])[0]
    pred_idx = int(np.argmax(proba))
    pred = labels[pred_idx] if pred_idx < len(labels) else str(pred_idx)
    conf = float(proba[pred_idx])

    logger.info("Prediction: %s -> %s (%.3f)", req.text[:50], pred, conf)

    return PredictResponse(
        text=req.text,
        prediction=pred,
        confidence=conf,
        model_version=req.model_version,
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/predict/batch", response_model=BatchPredictResponse)
def predict_batch(req: BatchPredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    results = []
    predictions = model.predict(req.texts)
    probabilities = model.predict_proba(req.texts)

    for text, pred_idx, proba in zip(req.texts, predictions, probabilities):
        pred = labels[pred_idx] if isinstance(pred_idx, (int, np.integer)) and pred_idx < len(labels) else str(pred_idx)
        conf = float(np.max(proba))
        results.append(PredictResponse(
            text=text,
            prediction=pred,
            confidence=conf,
            model_version="v1",
            timestamp=datetime.utcnow().isoformat()
        ))

    logger.info("Batch prediction: %d items", len(results))
    return BatchPredictResponse(results=results)

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    # In production: store to DB or S3 for retraining
    with open("logs/feedback.jsonl", "a") as f:
        f.write(json.dumps({
            "text": req.text,
            "predicted": req.predicted,
            "actual": req.actual,
            "timestamp": datetime.utcnow().isoformat()
        }) + "\n")
    logger.info("Feedback recorded for prediction: %s", req.predicted)
    return {"status": "recorded"}

@app.get("/metrics")
def metrics():
    # Basic metrics endpoint (Prometheus-style could be added)
    return {"model_path": MODEL_PATH, "model_loaded": model is not None}
