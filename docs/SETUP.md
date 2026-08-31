# Setup Guide

## Prerequisites

- Python 3.9+
- Node.js 16+
- PostgreSQL 12+ (or SQLite for development)
- Git

## Project Structure

```
lossgraph/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Entry point
│   │   ├── database.py        # Database config
│   │   ├── models.py          # SQLAlchemy models
│   │   └── api/               # API routers
│   │       ├── health.py
│   │       ├── transaction.py
│   │       ├── entity.py
│   │       ├── incident.py
│   │       ├── simulation.py
│   │       └── chargeback.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/                   # React/Next.js frontend
│   ├── src/
│   │   ├── app/               # Next.js app directory
│   │   ├── components/        # React components
│   │   └── lib/               # Utilities and API client
│   ├── package.json
│   └── tsconfig.json
├── ml/                         # Machine learning models
│   ├── models/
│   ├── training/
│   └── evaluation/
├── data/                       # Data and synthetic datasets
│   ├── scenarios/
│   └── generation/
├── docs/                       # Documentation
└── tests/                      # Test suite
```

## Backend Setup

### 1. Create Python virtual environment

```bash
cd backend
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create .env file

```bash
cp .env.example .env
```

Edit `.env`:
```
# Database
DATABASE_URL=sqlite:///./lossgraph.db
SQL_ECHO=false

# API
API_PORT=8000
API_HOST=0.0.0.0

# ML Models
MODEL_PATH=./models
ENABLE_GPU=false

# Logging
LOG_LEVEL=INFO

# LLM Integration (optional)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4
```

### 4. Initialize database

```bash
python -c "from app.database import init_db; init_db()"
```

### 5. Run the backend

```bash
python -m uvicorn app.main:app --reload
```

The API will be available at: `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

---

## Frontend Setup

### 1. Install dependencies

```bash
cd ../frontend
npm install
# or
yarn install
```

### 2. Create .env.local

```bash
cp .env.example .env.local
```

Edit `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Run development server

```bash
npm run dev
# or
yarn dev
```

The frontend will be available at: `http://localhost:3000`

---

## Full Stack Setup

To run both backend and frontend simultaneously:

```bash
# From project root
npm run setup  # Install all dependencies
npm run dev   # Run both services
```

Or run in separate terminals:

```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

---

## Database Options

### Development: SQLite (Default)

No additional setup required. Uses `./lossgraph.db` file.

### Production: PostgreSQL

1. Create database
```bash
createdb lossgraph
```

2. Update `.env`
```
DATABASE_URL=postgresql://user:password@localhost:5432/lossgraph
```

3. Run migrations (when implemented)
```bash
# Using Alembic (optional)
alembic upgrade head
```

---

## Testing

### Backend Tests

```bash
cd backend
pytest -v
# or with coverage
pytest --cov=app tests/
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Integration Tests

```bash
cd backend
pytest tests/integration/ -v
```

---

## Development Workflow

### 1. Creating a new API endpoint

1. Define request/response schemas in `app/api/routes.py`
2. Implement handler function
3. Add to router
4. Test with: `curl http://localhost:8000/api/v1/endpoint`
5. Update API docs

### 2. Adding database models

1. Define SQLAlchemy model in `app/models.py`
2. Import in `app/database.py`
3. Create migration (when using Alembic)
4. Update data model docs

### 3. Adding frontend components

1. Create component in `src/components/`
2. Use TypeScript for type safety
3. Integrate with API client (`src/lib/api.ts`)
4. Add to page or layout

---

## Configuration

### Backend Configuration

**Environment Variables**:
- `DATABASE_URL`: Database connection string
- `API_PORT`: Server port (default: 8000)
- `API_HOST`: Server host (default: 0.0.0.0)
- `LOG_LEVEL`: Logging level (default: INFO)

**FastAPI Config** (`app/main.py`):
- CORS settings
- Request validation
- Error handling

### Frontend Configuration

**Environment Variables**:
- `NEXT_PUBLIC_API_URL`: Backend API URL

**Next.js Config** (`next.config.js`):
- Tailwind CSS
- Import aliases
- API routes

---

## Deployment

### Docker Deployment

1. Build images
```bash
docker-compose build
```

2. Run services
```bash
docker-compose up
```

### Manual Deployment

**Backend**:
```bash
# Install production dependencies
pip install -r requirements.txt

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
```

**Frontend**:
```bash
# Build for production
npm run build

# Start production server
npm start
```

---

## Troubleshooting

### Backend won't start

Check if port 8000 is in use:
```bash
lsof -i :8000
```

Kill the process and restart.

### Database connection errors

Verify `DATABASE_URL` in `.env`:
```bash
# For SQLite
DATABASE_URL=sqlite:///./lossgraph.db

# For PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/lossgraph
```

### Frontend API requests failing

1. Verify backend is running: `curl http://localhost:8000/api/v1/health`
2. Check `NEXT_PUBLIC_API_URL` in `.env.local`
3. Check browser console for CORS errors

### CORS Errors

Update `app/main.py` with correct frontend URL:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Next Steps

1. Implement ML models for risk scoring
2. Build graph analysis algorithms
3. Create synthetic data generator
4. Implement LLM investigation layer
5. Add comprehensive test suite
6. Create deployment configurations
7. Implement authentication and authorization
8. Add monitoring and observability

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Next.js Documentation](https://nextjs.org/docs)
- [React Query Documentation](https://tanstack.com/query/latest)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Support

For issues or questions:
1. Check the documentation
2. Review existing GitHub issues
3. Create a new issue with detailed description
4. Include error logs and reproduction steps
