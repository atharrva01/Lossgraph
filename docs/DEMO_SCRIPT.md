# 5-Minute Pitch Video Script

Written against the actual running dashboard and real numbers from this
repo (seed 42, `make pipeline`) -- every figure here is what you'll
actually see on screen, not a mockup. Re-run `make pipeline` before
recording if any code changed since; the numbers are deterministic but
will drift if the generator or engines are edited.

**Setup before recording:** `make pipeline`, then start backend + frontend
(`QUICKSTART.md`), confirm http://localhost:3000 loads. Screen-record at
1080p+, browser zoomed so table text is legible.

---

## 0:00-0:30 -- The reframe

**Say:** "Most risk systems ask whether a transaction is risky. LossGraph
asks whether the merchant is entering a loss event -- and what
intervention stops it with the least collateral damage. A fraud model
scores one transaction in isolation. But a fraud ring looks fine
transaction-by-transaction, and a chargeback wave has zero warning signal
at the moment the order is placed. Both are invisible to a single model,
and both showed up in my own held-out evaluation."

**Screen:** title card or the Command Center already loaded, static.

## 0:30-1:15 -- Command Center

**Do:** Load http://localhost:3000. Point at the four stat tiles, then the
table.

**Say:** "This is real output from a held-out test split the model never
trained on -- ₹12L in current exposure, ₹6L preventable by the
recommended actions, 9 active incidents out of 17 detected. Every row here
is a Loss Event, not a transaction -- a cluster of accounts, or a spike in
a merchant's chargeback rate."

**Do:** Use the merchant filter dropdown once to show it recomputes live.

## 1:15-2:30 -- Investigate a real ring

**Do:** Click the highest-confidence `Coordinated Return Ring` row
(RE-2026-00002, 99% confidence).

**Say:** "Here's why this was flagged -- not a black box." Click through
2-3 evidence items (E1: shared device, E2: 22x return rate vs baseline,
E4: 15 transactions in 1.7 days). "Every claim traces back to a real
number, not an LLM guessing."

**Do:** Point at the entity graph -- the single red device node with blue
customer nodes fanned around it.

**Say:** "And here's the actual shared-infrastructure pattern -- one
device, seven accounts, each with its own delivery address. This is
built with NetworkX, not a black-box graph neural net -- connected
components and a transparent scoring heuristic."

## 2:30-3:30 -- The differentiator: shared device isn't the crime

**Do:** Go back, open the lower-confidence ring event (RE-2026-00009, 54%
confidence, `Hold` recommended) -- or reference it verbally with the
number on screen from the table.

**Say:** "This cluster also shares a device -- eight accounts, similar
structure. But its confidence is 54%, not 99%, and the recommended action
is Hold, not Block. That's because this one turned out to be a legitimate
high-value customer segment I deliberately built to look like a ring in
my synthetic data -- same shared device, but normal return rates and
steady 14-day activity instead of a 48-hour burst. The system tells them
apart on outcome and burstiness, not on the presence of a shared device --
which is the naive rule every simplistic fraud check gets wrong."

**Do:** Scroll to the policy comparison table on the true ring
(RE-2026-00002). Point at Block winning with the highest net benefit,
and Allow at ₹0.

**Say:** "For the confirmed ring, Block wins economically -- ₹1.86L net
benefit. For the ambiguous cluster, the same optimizer picks Hold, not
Block, because a wrongly-blocked legitimate order costs the full sale, not
a flat fee. That distinction alone changed the recommendation."

## 3:30-4:15 -- Why three engines, not one

**Do:** Click the `Chargeback Wave` event (RE-2026-00013, 51 transactions,
100% confidence).

**Say:** "This event has no entity graph at all -- these 51 transactions
looked completely ordinary when they happened. They only became visible
weeks later, as a spike in the merchant's daily dispute rate. My
transaction-time risk model catches zero percent of these by construction
-- there's no signal at authorization time. Only a temporal anomaly engine
watching the outcome stream catches it at all. That's why this system
fuses three engines instead of building one better model."

## 4:15-4:45 -- Honest numbers

**Say (over the evaluation doc, or narrate directly):** "On the held-out
test split: the fused model gets 0.61 PR-AUC, beating any single engine.
The economically-tuned policy prevents 79% of gross loss. And critically
-- the system's own confidence tracks ground truth without ever seeing the
label: events that turn out to be real loss get an average action
aggressiveness of 4.7 out of 5 -- close to Block. Events that turn out to
be false alarms average 0.7 -- close to Allow. That gap is the actual
proof this isn't just pattern-matching to a synthetic dataset."

## 4:45-5:00 -- Close

**Say:** "Built solo in five days: a synthetic merchant ecosystem with ten
injected scenarios, three independently-evaluated intelligence engines,
risk fusion, a counterfactual policy simulator, and this dashboard, all
running end to end. Repo link and full evaluation writeup in the
description."

**Screen:** Command Center, wide shot, hold for 3 seconds.

---

## Cut list if running long

Drop in this order: the merchant-filter demo (1:00), the second evidence
item click-through (1:45), the closing repeat of the architecture list
(4:45). Keep the ring-vs-trap comparison (2:30-3:30) and the
chargeback-wave no-graph moment (3:30-4:15) no matter what -- those two
are the actual differentiators.
