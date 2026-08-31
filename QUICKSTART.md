# Quick Start Guide

Get LossGraph running in 5 minutes!

## Prerequisites

- Python 3.9+
- Node.js 16+
- Git

## Option 1: Fastest Setup (Recommended)

### 1. Clone and Setup

```bash
cd lossgraph
bash setup.sh
```

This will:
- Create Python virtual environment
- Install all backend dependencies
- Install all frontend dependencies
- Create configuration files

### 2. Start Development Servers

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 3. Open in Browser

Navigate to: **http://localhost:3000**

---

## Option 2: Using Docker

### 1. Start All Services

```bash
docker-compose up
```

### 2. Wait for Services

```
✓ Database ready
✓ Redis ready
✓ Backend running on http://localhost:8000
✓ Frontend running on http://localhost:3000
```

### 3. Open in Browser

Navigate to: **http://localhost:3000**

---

## Option 3: Using Make

```bash
# View all available commands
make help

# Setup everything
make setup

# Run backend
make backend-run

# Run frontend (in another terminal)
make frontend-run

# Or both with Docker
make docker-up
```

---

## Verify Installation

### Check Backend

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "LossGraph"
}
```

### Check Frontend

Open browser to: http://localhost:3000

You should see the LossGraph dashboard with demo data.

### API Documentation

Interactive docs available at: http://localhost:8000/docs

---

## Next Steps

1. **Explore the Dashboard**
   - View active incidents
   - Check risk metrics
   - Investigate entities

2. **Review Documentation**
   - Architecture: `docs/ARCHITECTURE.md`
   - API Reference: `docs/API.md`
   - Data Model: `docs/DATA_MODEL.md`

3. **Try the API**
   - Score a transaction: `curl -X POST http://localhost:8000/api/v1/risk/transaction/score`
   - Get incidents: `curl http://localhost:8000/api/v1/risk/incidents?merchant_id=DEMO_MERCHANT_001`

4. **Run Tests**
   ```bash
   # Backend tests
   cd backend
   pytest -v
   
   # Frontend tests
   cd frontend
   npm test
   ```

---

## Configuration

### Backend Configuration (backend/.env)

```env
# Database
DATABASE_URL=sqlite:///./lossgraph.db

# API
API_PORT=8000
API_HOST=0.0.0.0

# Logging
LOG_LEVEL=INFO
```

### Frontend Configuration (frontend/.env.local)

```env
# API
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find and kill process using port 8000 (backend)
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill

# Find and kill process using port 3000 (frontend)
lsof -i :3000 | grep LISTEN | awk '{print $2}' | xargs kill
```

### Database Connection Error

```bash
# Reset database
make clean-db
make db-init

# Or manually
rm -f backend/lossgraph.db
```

### Module Not Found

```bash
# Reinstall dependencies
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

### CORS Errors

Verify `NEXT_PUBLIC_API_URL` is set correctly in `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

---

## Project Structure

```
lossgraph/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Entry point
│   │   ├── models.py          # Database models
│   │   ├── database.py        # DB configuration
│   │   └── api/               # API endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # React/Next.js frontend
│   ├── src/
│   │   ├── app/               # Next.js app
│   │   ├── components/        # React components
│   │   └── lib/               # Utilities
│   ├── package.json
│   └── Dockerfile
├── docs/                       # Documentation
├── Makefile                    # Development commands
├── docker-compose.yml          # Docker setup
└── README.md
```

---

## Key URLs

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Database (Postgres) | localhost:5432 |
| Redis Cache | localhost:6379 |
| Neo4j Graph | http://localhost:7474 |

---

## Development Workflow

### Adding a Feature

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes in backend or frontend
3. Test: `pytest` (backend) or `npm test` (frontend)
4. Commit: `git commit -am "Add feature"`
5. Push: `git push origin feature/my-feature`
6. Open pull request

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Run tests
make test
```

---

## Common Commands

```bash
# Install dependencies
make install

# Start development servers
make backend-run      # Terminal 1
make frontend-run     # Terminal 2

# Run with Docker
make docker-up
make docker-down

# Run tests
make test

# Clean up
make clean

# View all commands
make help
```

---

## Getting Help

1. **Documentation**: Check `docs/` folder
2. **API Docs**: http://localhost:8000/docs
3. **Code Comments**: Read inline documentation
4. **Issues**: Search GitHub issues
5. **Roadmap**: See `ROADMAP.md` for development plan

---

## Next Milestones

- [ ] Implement transaction risk model
- [ ] Build entity graph engine
- [ ] Add time-series anomaly detection
- [ ] Create LLM investigation layer
- [ ] Generate synthetic test data
- [ ] Deploy to production

---

## Quick API Testing

### Score a Transaction

```bash
curl -X POST http://localhost:8000/api/v1/risk/transaction/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN_123",
    "merchant_id": "MERCH_001",
    "customer_id": "CUST_789",
    "amount": 4500,
    "payment_method": "card",
    "device_id": "DEVICE_XYZ",
    "address_id": "ADDR_ABC"
  }'
```

### Get Incidents

```bash
curl http://localhost:8000/api/v1/risk/incidents?merchant_id=DEMO_MERCHANT_001
```

### Compare Policies

```bash
curl http://localhost:8000/api/v1/risk/simulate/RE-2026-00871/compare
```

---

## Performance Tips

1. Use PostgreSQL for production (not SQLite)
2. Enable Redis caching for frequently accessed data
3. Implement database indexing on high-query tables
4. Use connection pooling for database connections
5. Enable query result caching in API

---

## Security Notes

⚠️ **Development Mode**: No authentication enabled
- Configure authentication before production
- Use environment variables for secrets
- Enable HTTPS for production
- Implement rate limiting
- Add input validation

---

Happy coding! 🚀
