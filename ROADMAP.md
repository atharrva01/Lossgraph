# LossGraph Project Roadmap

## Phase 1: Foundation (Current)
✅ Project structure setup
✅ Database models and schemas
✅ Core API endpoints
✅ Frontend scaffolding
✅ Documentation
✅ Deployment configuration

## Phase 2: Core Intelligence Engines
- [x] Transaction Risk Model (LightGBM) -- `ml/risk_model.py`
- [ ] Entity Behavior Models
- [x] Entity Graph Engine (NetworkX connected components + heuristic scoring) -- `ml/graph_engine.py`
- [x] Merchant Anomaly Detection (Poisson-style rolling z-score) -- `ml/anomaly_engine.py`
- [x] Risk Event Detection Algorithm (fusion of the three) -- `ml/loss_events.py`

## Phase 3: Analysis & Explanation
- [x] LLM Integration Layer (Claude Opus 5, evidence-grounded, citation-checked, deterministic fallback) -- `ml/investigator.py`
- [x] Evidence Chain Generation -- `ml/loss_events.py` (evidence IDs E1, E2... per event)
- [x] Counterfactual Simulation Engine -- `ml/counterfactual.py`
- [x] Action Optimizer (argmax net economic benefit over 6 candidate actions) -- `ml/counterfactual.py`
- [x] Risk Event Genome Creation -- `ml/loss_events.py` (fuses risk_model + graph_engine + anomaly_engine)

## Phase 4: Advanced Features
- [ ] Chargeback Response Automation
- [ ] Evidence Contradiction Detection
- [ ] Risk Propagation Algorithm
- [ ] Temporal Pattern Analysis
- [x] Seasonal Baseline Normalization (Poisson-style pooled trailing baseline in the anomaly engine)

## Phase 5: Testing & Evaluation
- [x] Synthetic Data Generator -- `data/generation/`, see `data/README.md`
- [x] Scenario-based Testing (10 injected loss/edge-case scenario types)
- [x] Evaluation Framework (held-out precision/recall/PR-AUC + economic metrics) -- `ml/evaluation.py`
- [ ] Model Benchmarking
- [x] Cold-start Handling (merchant-baseline fallback for new customers in `ml/features.py`)

## Phase 6: Production Ready
- [ ] Authentication & Authorization
- [ ] Rate Limiting
- [ ] Monitoring & Observability
- [ ] Performance Optimization
- [ ] Security Hardening
- [ ] Documentation Updates

## Phase 7: Advanced Deployment
- [ ] Kubernetes Configuration
- [ ] CI/CD Pipeline
- [ ] A/B Testing Framework
- [ ] Multi-tenant Support
- [ ] Real-time Streaming

---

## Implementation Priority

### High Priority (MVP)
1. Transaction risk scoring model
2. Entity graph construction
3. Time-series anomaly detection
4. Risk event clustering
5. Counterfactual simulation UI

### Medium Priority (v1.1)
1. LLM investigation layer
2. Chargeback evidence generator
3. Merchant dashboard
4. API authentication
5. Comprehensive test suite

### Low Priority (v2.0)
1. Neo4j integration
2. Real-time streaming
3. Advanced visualizations
4. ML model retraining pipeline
5. Multi-language support

---

## Milestone Timeline (actual: 5-day buildathon build, not the 12-week plan above)

Applications for this track close 2026-09-05. Built solo; scope was
deliberately cut from the sections above to what's gradeable and
demo-able in that window (see "What NOT to Build" reasoning in the
project's planning history) rather than the full PRD.

**Day 1** -- Synthetic data generator (`data/generation/`): baseline
merchant ecosystem + 10 injected loss/edge-case scenarios, chronological
train/val/test split, ground truth kept physically separate from features.

**Day 2** -- Three intelligence engines, each held-out evaluated:
transaction risk model (LightGBM), entity graph engine (NetworkX), merchant
temporal anomaly engine (Poisson-style rolling z-score). Found and fixed a
real generator bug the graph engine surfaced (baseline population was
percolating into one giant connected component).

**Day 3** -- Risk fusion (noisy-OR across the three engines), Loss Event
Genome construction with evidence chains, counterfactual policy simulator,
economically-optimal action recommendation.

**Day 4** -- FastAPI backend serving the precomputed pipeline output
(`backend/app/data_access.py`), Next.js dashboard: Command Center, incident
drill-down with evidence chain + entity graph (Cytoscape.js) + policy
comparison. Verified end-to-end in a real browser.

**Day 5** -- Evaluation write-up, architecture documentation, 5-minute
pitch video script, repo cleanup.

**Day 6 (stretch, buffer time before the Sep 5 deadline)** -- AI
Investigator (`ml/investigator.py`): Claude Opus 5 turns each Loss Event's
evidence chain into a plain-English narrative (primary hypothesis,
supporting/contradicting evidence, unknowns, confidence commentary),
system-prompted to cite an evidence ID for every claim and never propose an
action other than the one the counterfactual simulator already picked.
Every generated narrative is checked post-hoc for citations before being
accepted. Falls back to a deterministic evidence-chain template -- verified
working, since this repo has no API key configured -- exactly the section
43 "LLM unavailable" failure path, not a hypothetical. Chargeback responder
remains unbuilt; not required for the graded rubric (held-out precision/
recall + honest false-positive cost + strictly defensive).

---

## Known Issues & Technical Debt

### Current Limitations
- No authentication (dev-only)
- SQLite for development only
- Placeholder ML models
- Mock LLM responses
- Single-merchant demo

### Technical Debt
- Need comprehensive error handling
- Missing input validation in many endpoints
- Test coverage minimal
- Documentation needs examples
- No logging framework configured

### Future Improvements
- Add webhook support
- Implement caching layer
- GraphQL API option
- Mobile app
- Real-time notifications

---

## Skills Required

**Backend Development**
- Python, FastAPI, SQLAlchemy
- PostgreSQL/Graph databases
- REST API design

**ML Engineering**
- Feature engineering
- Gradient boosting (XGBoost, LightGBM)
- Time-series analysis
- Graph algorithms

**Frontend Development**
- React, TypeScript, Next.js
- D3.js/Plotly visualization
- State management

**DevOps**
- Docker, docker-compose
- Kubernetes (optional)
- CI/CD pipelines
- Monitoring

---

## Resources & References

### Machine Learning
- SHAP: https://github.com/slundberg/shap
- LightGBM: https://lightgbm.readthedocs.io/
- Scikit-learn: https://scikit-learn.org/

### Graph Processing
- NetworkX: https://networkx.org/
- Neo4j: https://neo4j.com/

### Web Framework
- FastAPI: https://fastapi.tiangolo.com/
- Next.js: https://nextjs.org/

### Time-Series
- Pandas: https://pandas.pydata.org/
- SciPy: https://scipy.org/

### Visualization
- Plotly: https://plotly.com/
- D3.js: https://d3js.org/
- Cytoscape: https://cytoscape.org/

---

## Contribution Guidelines

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit a pull request

### Code Standards
- Python: PEP 8 (enforced by black, isort, flake8)
- JavaScript/TypeScript: ESLint, Prettier
- Documentation: Markdown with clear examples
- Tests: pytest for backend, Jest for frontend

---

## Contact & Support

For questions or issues:
1. Check existing documentation
2. Search GitHub issues
3. Create detailed issue report with:
   - Steps to reproduce
   - Error logs
   - Environment info
   - Expected vs actual behavior

---

## License

[Add appropriate license]

---

## Acknowledgments

Built for the Razorpay AI Buildathon - Track 02: AI Risk Manager
