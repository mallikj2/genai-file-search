# GenAI File Search API

A production-ready AI-powered file search application using **Gemini 2.5 Pro**, **Vertex AI**, **ChromaDB**, and **FastAPI**.

## Features

- 🚀 **Multi-format support**: PDF, DOCX, XLSX, PPT, TXT, CSV, Images, JSON, XML, SQL
- 🔍 **Semantic search**: AI-powered search across documents
- 📊 **Category management**: Organize files by categories
- ⚡ **Async processing**: Background file processing with Celery
- 💾 **Persistent storage**: ChromaDB for vector embeddings
- 🤖 **Gemini 2.5 Pro**: Advanced Q&A and summarization
- 📈 **Scalable**: Ready for 100K+ requests/day

## Tech Stack

- **FastAPI** - Web framework
- **Gemini 2.5 Pro** - LLM for Q&A and summarization
- **Vertex AI Text Embeddings** - Semantic embeddings
- **ChromaDB** - Vector database
- **Celery + Redis** - Async task processing
- **SQLAlchemy** - Database ORM

## Prerequisites

- Python 3.11+
- Redis server
- Google Cloud Platform account with:
  - Gemini API enabled
  - Vertex AI API enabled
  - Service account with appropriate permissions
- Tesseract OCR (for image processing)

## Installation

### 1. Clone and Setup

```bash
# Create project directory
mkdir genai-file-search
cd genai-file-search

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

### 3. Google Cloud Setup

1. Create a GCP project
2. Enable APIs:
   - Vertex AI API
   - Generative Language API
3. Create a service account:
   ```bash
   gcloud iam service-accounts create genai-file-search
   ```
4. Download service account key JSON
5. Grant permissions:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:genai-file-search@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```

### 4. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 5. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# Ubuntu: sudo apt-get install redis-server
# macOS: brew install redis
```

## Running the Application

### Option 1: Manual Start

**Terminal 1 - API Server:**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Celery Worker:**
```bash
celery -A worker.celery_app worker --loglevel=info --concurrency=4
```

### Option 2: Docker Compose

```bash
docker-compose up --build
```

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Categories

```bash
# Create category
POST /api/categories/create
{
  "name": "Orders",
  "description": "Order documents"
}

# List categories
GET /api/categories/list

# Get category
GET /api/categories/{category_id}

# Delete category
DELETE /api/categories/{category_id}
```

### Files

```bash
# Upload file
POST /api/files/upload
Form Data:
- file: <file>
- category_id: <int>

# List files
GET /api/files/list?category_id=1

# Get file status
GET /api/files/{file_id}

# Get task status
GET /api/files/status/{task_id}

# Delete file
DELETE /api/files/{file_id}
```

### Search

```bash
# Semantic search
POST /api/search/query
{
  "query": "What are the order details?",
  "category_id": 1,
  "top_k": 5
}

# Summarize documents
POST /api/search/summarize
{
  "category_id": 1,
  "max_length": 500
}

# Question & Answer
POST /api/search/qa
{
  "question": "What is the total order amount?",
  "category_id": 1,
  "top_k": 5
}

# Find passages
POST /api/search/find-passages
{
  "query": "customer information",
  "category_id": 1,
  "top_k": 10
}
```

## Usage Example

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Create category
response = requests.post(
    f"{BASE_URL}/api/categories/create",
    json={"name": "Orders", "description": "Order documents"}
)
category_id = response.json()["id"]

# 2. Upload file
with open("order.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/files/upload",
        files={"file": f},
        data={"category_id": category_id}
    )
    task_id = response.json()["task_id"]

# 3. Check processing status
import time
while True:
    response = requests.get(f"{BASE_URL}/api/files/status/{task_id}")
    status = response.json()["status"]
    if status in ["SUCCESS", "FAILURE"]:
        break
    time.sleep(2)

# 4. Search
response = requests.post(
    f"{BASE_URL}/api/search/query",
    json={
        "query": "What are the order details?",
        "category_id": category_id,
        "top_k": 5
    }
)
print(response.json()["answer"])
```

### cURL Examples

```bash
# Create category
curl -X POST http://localhost:8000/api/categories/create \
  -H "Content-Type: application/json" \
  -d '{"name": "Orders", "description": "Order documents"}'

# Upload file
curl -X POST http://localhost:8000/api/files/upload \
  -F "file=@order.pdf" \
  -F "category_id=1"

# Search
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the order details?",
    "category_id": 1,
    "top_k": 5
  }'
```

## Project Structure

```
genai-file-search/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── api/
│   │   ├── categories.py    # Category endpoints
│   │   ├── files.py         # File endpoints
│   │   └── search.py        # Search endpoints
│   ├── services/
│   │   ├── chunking.py      # Text chunking
│   │   ├── embeddings.py    # Vertex AI embeddings
│   │   ├── file_processor.py # File parsing
│   │   ├── gemini_service.py # Gemini API
│   │   └── vector_store.py   # ChromaDB operations
│   └── tasks/
│       └── celery_tasks.py  # Async tasks
├── worker.py                # Celery worker
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Monitoring

### Check Celery Tasks

```bash
# List active tasks
celery -A worker.celery_app inspect active

# List registered tasks
celery -A worker.celery_app inspect registered

# Purge all tasks
celery -A worker.celery_app purge
```

### Logs

```bash
# API logs
tail -f logs/api.log

# Worker logs (if running manually)
celery -A worker.celery_app worker --loglevel=debug
```

## Performance Tuning

### For High Load (100K requests/day)

1. **Increase Celery workers:**
```bash
celery -A worker.celery_app worker --concurrency=10
```

2. **Use Redis Cluster** for better performance

3. **Horizontal scaling:**
   - Deploy multiple API instances
   - Use load balancer (nginx/HAProxy)
   - Scale Celery workers independently

4. **Database optimization:**
   - Switch to PostgreSQL for production
   - Add database indexes
   - Use connection pooling

## Troubleshooting

### Issue: "No module named 'app'"
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}"
```

### Issue: Redis connection failed
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

### Issue: Google Cloud authentication
```bash
# Verify credentials
gcloud auth application-default print-access-token

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

### Issue: Tesseract not found
```bash
# Ubuntu
sudo apt-get install tesseract-ocr

# Verify installation
tesseract --version
```

## Security Considerations

1. **API Keys**: Never commit `.env` files
2. **File uploads**: Implement virus scanning for production
3. **Rate limiting**: Add rate limiting middleware
4. **Authentication**: Implement JWT/OAuth for production
5. **CORS**: Configure specific origins in production

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: [Create Issue]
- Documentation: See `/docs` endpoint
- Email: support@example.com

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

---

Built with ❤️ using Gemini 2.5 Pro and Vertex AI
