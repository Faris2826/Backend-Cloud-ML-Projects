# ML Text Classification API

A production-ready machine learning API for text classification/sentiment analysis.

## Features

- FastAPI-based REST API
- Scikit-learn model pipeline (TF-IDF + Logistic Regression)
- Request logging & performance timing
- Batch prediction support
- Feedback collection for model improvement
- Docker & Docker Compose ready
- Health checks & metrics endpoints

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Train the model
python app/train.py

# Run the API
uvicorn app.main:app --reload
```

### Docker

```bash
# Build and run
docker-compose up --build

# API will be available at http://localhost:8000
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/predict` | POST | Single text prediction |
| `/predict/batch` | POST | Batch prediction |
| `/feedback` | POST | Submit feedback for retraining |
| `/metrics` | GET | Basic model metrics |

## Example Request

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is absolutely amazing!"}'
```

## Project Structure

```
.
├── app/
│   ├── main.py       # FastAPI application
│   └── train.py      # Model training script
├── models/           # Saved model artifacts
├── logs/             # Request & feedback logs
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Deployment

This project is containerized and ready for deployment on:
- AWS ECS / Fargate
- Google Cloud Run
- Azure Container Apps
- Railway / Render / Fly.io

## Future Improvements

- [ ] Add Prometheus metrics export
- [ ] Model versioning & A/B testing
- [ ] Automated retraining pipeline
- [ ] PostgreSQL for feedback storage
- [ ] Async model inference with Celery
