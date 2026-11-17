# Week 8: retries, recovery, and a human approval gate

## Week 8

**Run conditions.** Fault seed: 42 | baseline attempts: 1 | hardened attempts: 3 | hardened base delay: 0.02 s in `01_survive.py` (0.05 s in graph policies) | max elapsed: 3.0 s for hardened and graph policies | LangGraph version: not verified in this standalone archive | date: 2026-11-17.

**Scope of evidence.** The fault matrix and node behavior below were verified using the packaged offline fault harness with temporary import shims, because the ZIP does not include the shared `project.trace` package or an installed LangGraph runtime. This is not a claim that the two-process gate was executed. Verify that demonstration from the complete project.

### 1. Which errors are retryable

Retryable: `ToolTimeout`, `RateLimited` (HTTP 429), and `ServerError` (HTTP 500). These represent transient conditions for which another call may succeed.

Deliberately **not** retryable: `ContractDrift`, because a successful response with a renamed field is systematically incompatible with our expected contract; repeating it only wastes calls and can hide the real failure. A 401 authentication error is also not retryable: the credential must be repaired, and repeated attempts may lock an account.

### 2. The fault matrix (TODO 6)

| Run | correct | WRONG | degraded | failed |
| --- | ---: | ---: | ---: | ---: |
| baseline (1 attempt, no validation/fallback) | 1 | 0 | 2 | 5 |
| hardened (3 attempts, validation/fallback) | 2 | 0 | 5 | 1 |

Per-fault observations from the local offline harness:

| Fault | Baseline verdict | Hardened verdict | Hardened search / fees attempts |
| --- | --- | --- | --- |
| timeout | failed | degraded | 3 / 3 |
| rate_limit | failed | degraded | 3 / 3 |
| server_error | failed | degraded | 3 / 3 |
| malformed | degraded | degraded | 1 / 1 |
| empty | failed | failed | 1 / 1 |
| slow | correct | correct | 1 / 1 |
| drift | degraded | degraded | 1 / 1 |
| flaky | failed | correct | 2 / 2 |

Hardening bought **fewer outright failures (5 to 1)** and more explicit partial results (2 to 5), not a dramatic increase in correct answers. The flaky case recovers with retries; repeatable errors degrade instead of being silently accepted. In particular, drift is caught on the successful fee response via validation, and the fees step makes exactly **one** attempt. The `WRONG` count is zero in this fixture for both modes; this does not establish that all incorrect answers would be detected in production.

### 3. The empty result

An empty result is not a transport error. My pipeline treats a successful empty search as **insufficient coverage**, marking `search evidence unavailable` and making the draft explicitly incomplete. It does not retry a 200 response merely because no passages were found, and does not invent evidence. An empty fee response is rejected by `validate_fee`, which prevents the draft from claiming a fee that was not supplied. In the matrix, the case with both search and fee empty is still `failed` (nothing useful was recovered).

### 4. The gate (TODO 7)

Gated step: **`submit`** only, because it is an externally visible case submission with consequences that cannot be undone just by revising an answer. `gather`, `price`, and `draft` are read-only/preparatory; stopping them for approval creates unnecessary review fatigue.

An unanswered approval after a timeout should **default to reject / not submitted** and mark the request pending for human review. This protects the resident, the municipality, and the approver from an unauthorized or mistaken submission. **Not yet implemented:** the standalone `02_gate.py` demo waits for explicit resume; no timeout handler exists in this ZIP. The timeout is therefore a design decision and deferred homework, **not a tested behavior**.

The approval payload carries the intended action, case ID, exact tool arguments (`topic` and structured `fee`), retrieved evidence, degradation flag, and missing-data names. It deliberately does **not** substitute a model-written summary for the arguments being approved. Approval, rejection, and editing are supported by the existing `submit` logic; the edit path uses the approver's replacement fee. The existing runner writes a decision record containing the verdict and reviewer identity.

### 5. The duplicate the state does not show

As documented by the supplied `WEEK08_FINDINGS.md` and `interrupt_smoke_test.py`, placing a side effect above the interrupt makes it execute **twice** (once before pause and once on resume), but recorded state shows it **once**, because the interrupted first execution does not return its state update. **This was not independently rerun in this standalone ZIP.**

Consequently, the gated node must be **read-only above `interrupt()`**; external writes belong after approval and should be protected by idempotency controls as appropriate. The existing `submit()` has no external write before the interrupt, and its `side_effects` list is a demonstration record, not an actual database or network submission.

### Deferred / verification on the full repository

- Run `python labs/week08/starter/02_gate.py start` and then **in a separate process** `python labs/week08/starter/02_gate.py resume approve`; repeat for `reject` and `edit`. The two-process checkpoint requires installed `langgraph` and `langgraph-checkpoint-sqlite`, plus the shared `project` package, which were not present in the uploaded ZIP.
- Demonstrate the deliberate external side effect above an interrupt in a controlled test (see `interrupt_smoke_test.py`) and compare execution count with recorded state. Do not add such a write to the normal production gate.
- Implement and prove the unattended approval timeout in the larger `app/` integration, where `request_approval(payload, unattended)` belongs. This week-only ZIP does not include `app/`.
- Add an OpenTelemetry trace showing retry, fallback, and gate; run `python -m project.verify` from the full repository.
- The offline harness cannot emulate real network timing, authentication failures, third-party outages, or irreversible external side effects.
