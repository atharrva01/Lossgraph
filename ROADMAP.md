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
- [x] LLM Integration Layer (Gemini, evidence-grounded, citation-checked, deterministic fallback) -- `ml/investigator.py`
- [x] Evidence Chain Generation -- `ml/loss_events.py` (evidence IDs E1, E2... per event)
- [x] Counterfactual Simulation Engine -- `ml/counterfactual.py`
- [x] Action Optimizer (argmax net economic benefit over 6 candidate actions) -- `ml/counterfactual.py`
- [x] Risk Event Genome Creation -- `ml/loss_events.py` (fuses risk_model + graph_engine + anomaly_engine)

## Phase 4: Advanced Features
- [x] Chargeback Response Automation (evidence checklist + CONTEST/ACCEPT/ESCALATE recommendation, linked back to Loss Event detection) -- `ml/chargeback_responder.py`
- [x] Evidence Contradiction Detection (refund-before-dispute, independently-flagged-as-loss) -- `ml/chargeback_responder.py`
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
Investigator (`ml/investigator.py`): an LLM turns each Loss Event's
evidence chain into a plain-English narrative (primary hypothesis,
supporting/contradicting evidence, unknowns, confidence commentary),
system-prompted to cite an evidence ID for every claim and never propose an
action other than the one the counterfactual simulator already picked.
Every generated narrative is checked post-hoc for citations before being
accepted. Falls back to a deterministic evidence-chain template -- the
section 43 "LLM unavailable" failure path.

**Day 7 (stretch)** -- Chargeback Responder (`ml/chargeback_responder.py`):
evidence checklist scoped to what a reason code actually requires,
contradiction detection (refund already issued; transaction independently
flagged by this system's own detection), and a CONTEST/ACCEPT/ESCALATE
recommendation. The 74 ACCEPT recommendations were 100% correct against
ground truth (every one really was a detected loss pattern) -- see
`docs/EVALUATION.md`. Each case links back to its Loss Event where one
exists (51 of the 74 ACCEPT cases trace to a single `chargeback_wave`
event), and each incident page shows every chargeback that traces back to
it -- the dispute-to-detection connection the product spec's demo script
describes, working end to end rather than narrated.

**Day 8 (stretch)** -- Switched the LLM provider from Claude Opus 5 to
Gemini (free tier, no credit card) after weighing the actual cost of the
Claude path against just not needing to pay for a hackathon demo -- the
product spec never asks for a specific model, only "any reliable
structured-output model" (section 38), so this is a config change to the
grounding discipline, not a redesign of it. Verified the live LLM path
end to end with a real key (not just mocked, unlike the Day 6/7 build):
- `gemini-3.6-flash`'s free tier is capped at 20 requests/*day* --
  unusable for 189 calls. `gemini-2.5-flash`/`-flash-lite` are retired for
  new API keys. Landed on `gemini-3.5-flash-lite`, whose free tier is
  15 requests/*minute* -- workable with pacing.
- The first live run silently produced malformed JSON on the flagship
  model: `finish_reason=MAX_TOKENS` because a reasoning-heavy model spends
  most of its token budget on internal thinking before writing the answer
  (1,917 of a 2,000-token budget on one call). Fixed by switching to the
  non-reasoning `-lite` model and raising the budget as a safety margin,
  not by suppressing the symptom.
- Added preemptive pacing (4.2s between calls) instead of reactive
  retry-after-429 -- simpler and avoids wasting the "did the grounding
  check actually fail" fallback path on requests that just needed to
  wait.

The `.env` holding the real key is gitignored -- a fresh clone of this
repo has no key configured anywhere, so it genuinely exercises the
deterministic fallback path by default, exactly as documented. This run
was the first time the LLM path was verified against a real API rather
than a mocked client.

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
