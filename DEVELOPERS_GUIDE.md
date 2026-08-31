#!/bin/bash

# LossGraph Development Quick Reference
# Print this guide with: cat DEVELOPERS_GUIDE.md

cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║         LossGraph - Developers Quick Reference Guide          ║
║    AI Risk Manager for Merchant Loss Intelligence             ║
╚═══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 QUICK START (Choose One)

1. Automated Setup:
   $ bash setup.sh

2. Using Make:
   $ make setup
   $ make backend-run  # Terminal 1
   $ make frontend-run # Terminal 2

3. Using Docker:
   $ docker-compose up

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 PROJECT STRUCTURE

lossgraph/
├── backend/          FastAPI backend service
├── frontend/         React/Next.js dashboard
├── docs/             Comprehensive documentation
├── data/             Data generation & ML datasets
├── ml/               Machine learning models
└── tests/            Test suite

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 KEY URLS

Service              | URL
─────────────────────────────────────────────
Frontend Dashboard   | http://localhost:3000
Backend API          | http://localhost:8000
API Documentation    | http://localhost:8000/docs
Database             | localhost:5432

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 DOCUMENTATION

File                          | Purpose
─────────────────────────────────────────────────────────
README.md                     | Project overview
QUICKSTART.md                 | 5-minute guide
docs/SETUP.md                 | Detailed setup
docs/ARCHITECTURE.md          | System design
docs/DATA_MODEL.md            | Database schema
docs/API.md                   | API reference
ROADMAP.md                    | Development plan

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ COMMON DEVELOPMENT COMMANDS

Backend Development:
  $ cd backend
  $ source venv/bin/activate
  $ python -m uvicorn app.main:app --reload

Frontend Development:
  $ cd frontend
  $ npm run dev

Run Tests:
  $ make test                    # All tests
  $ make backend-test            # Backend only
  $ make frontend-test           # Frontend only

Code Quality:
  $ make lint                    # Check all code
  $ make format                  # Format backend code
  $ make backend-lint            # Python linting

Database:
  $ make db-init                 # Initialize DB
  $ make db-reset                # Reset DB
  $ make clean-db                # Clean DB only

Docker:
  $ docker-compose up            # Start services
  $ docker-compose down          # Stop services
  $ docker-compose logs -f       # View logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🛠️ BACKEND GUIDE

Location: backend/
Language: Python 3.9+
Framework: FastAPI
Database: SQLAlchemy ORM

Key Files:
  app/main.py           - Entry point
  app/models.py         - Database models
  app/database.py       - DB configuration
  app/api/*.py          - API endpoints

Adding an Endpoint:
  1. Define models in app/models.py
  2. Create route in app/api/route_name.py
  3. Add to router import in app/main.py
  4. Test with: pytest tests/
  5. Docs auto-generate in /docs

Testing:
  $ cd backend
  $ pytest -v                    # Run tests
  $ pytest --cov=app            # With coverage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 FRONTEND GUIDE

Location: frontend/
Language: TypeScript/React
Framework: Next.js 14
Styling: Tailwind CSS

Key Files:
  src/app/page.tsx              - Dashboard page
  src/components/               - React components
  src/lib/api.ts                - API client

Adding a Component:
  1. Create file in src/components/MyComponent.tsx
  2. Export component
  3. Import and use in pages
  4. Style with Tailwind classes

Running Development Server:
  $ cd frontend
  $ npm run dev                  # http://localhost:3000

Testing:
  $ npm test                     # Run tests
  $ npm run lint                 # Lint code
  $ npm run build                # Build for production

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗄️ DATABASE GUIDE

Type: SQLAlchemy ORM
Dev: SQLite (lossgraph.db)
Prod: PostgreSQL recommended

Models:
  Merchant       - Payment processor accounts
  Customer       - User profiles
  Transaction    - Payment events
  Entity         - Devices, addresses, etc.
  Relationship   - Graph edges
  RiskEvent      - Detected loss events
  Counterfactual - Policy simulations

Initialization:
  $ python -c "from app.database import init_db; init_db()"

Viewing Database:
  $ sqlite3 lossgraph.db
  sqlite> SELECT * FROM transactions LIMIT 5;

Migration (when using Alembic):
  $ alembic upgrade head
  $ alembic revision --autogenerate -m "Add column"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 TESTING GUIDE

Backend Tests:
  $ cd backend
  $ pytest                       # Run all tests
  $ pytest -v -s                 # Verbose output
  $ pytest tests/test_api.py     # Specific file
  $ pytest -k transaction        # Match test name

Frontend Tests:
  $ cd frontend
  $ npm test                     # Run tests
  $ npm test -- --watch         # Watch mode
  $ npm test -- --coverage      # Coverage report

Test Structure:
  tests/
  ├── backend/
  │   ├── test_api.py           # API endpoint tests
  │   ├── test_models.py        # Model tests
  │   └── test_services.py      # Service tests
  └── frontend/
      ├── __tests__/            # Component tests
      └── integration/          # E2E tests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🐛 TROUBLESHOOTING

Issue: Port already in use
  $ lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill

Issue: Module not found
  # Backend
  $ pip install -r requirements.txt
  
  # Frontend
  $ npm install

Issue: Database connection error
  $ rm lossgraph.db
  $ python -c "from app.database import init_db; init_db()"

Issue: CORS errors
  ✓ Check NEXT_PUBLIC_API_URL in frontend/.env.local
  ✓ Check CORS config in backend/app/main.py

Issue: npm/pip frozen
  $ npm cache clean --force
  $ pip cache purge

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 GIT WORKFLOW

Create Feature Branch:
  $ git checkout -b feature/my-feature

Commit Changes:
  $ git commit -am "Add feature description"

Push to Remote:
  $ git push origin feature/my-feature

Create Pull Request:
  Visit GitHub and create PR

Code Review:
  ✓ Pass linting (make lint)
  ✓ Pass tests (make test)
  ✓ Update documentation
  ✓ Add type hints (Python) / types (TypeScript)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚢 DEPLOYMENT

Development:
  $ npm run dev                  # Start dev servers

Production Build:
  Backend:
    $ pip install -r requirements.txt
    $ gunicorn -w 4 app.main:app
  
  Frontend:
    $ npm run build
    $ npm start

Docker Deployment:
  $ docker-compose -f docker-compose.yml up -d

Kubernetes (Optional):
  $ kubectl apply -f k8s/
  $ kubectl port-forward svc/lossgraph-backend 8000:8000

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 LEARNING RESOURCES

Backend:
  - FastAPI: https://fastapi.tiangolo.com/
  - SQLAlchemy: https://docs.sqlalchemy.org/
  - Pydantic: https://docs.pydantic.dev/

Frontend:
  - Next.js: https://nextjs.org/docs
  - React: https://react.dev/
  - TypeScript: https://www.typescriptlang.org/docs/
  - Tailwind: https://tailwindcss.com/docs

ML/Data:
  - LightGBM: https://lightgbm.readthedocs.io/
  - Pandas: https://pandas.pydata.org/docs/
  - NumPy: https://numpy.org/doc/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 DEVELOPMENT TIPS

✓ Use VS Code with extensions:
  - Python
  - Pylance
  - ESLint
  - Prettier
  - Thunder Client (API testing)

✓ Use Git hooks for auto-formatting:
  $ pip install pre-commit
  $ pre-commit install

✓ Document as you code:
  - Type hints in Python
  - JSDoc comments
  - Markdown docs

✓ Keep requirements.txt updated:
  $ pip freeze > requirements.txt

✓ Use environment variables for secrets:
  - Never commit .env files
  - Use .env.example template

✓ Test frequently:
  - Write tests alongside code
  - Aim for >80% coverage

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 NEED HELP?

1. Check documentation:     docs/ folder
2. Read code comments:      Inline in source files
3. Check ROADMAP.md:        Development plan
4. GitHub issues:           Search existing
5. Create new issue:        With details & logs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Happy coding! 🚀

LossGraph Team
EOF
