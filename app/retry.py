"""Stage: retries, fallback, and the degrade path. Replaced in week 8.

Until you wire yours in, there is no policy: every step is called exactly
once, nothing is retried, no fallback is tried, and an exception propagates.
That is the week 8 baseline, the run you recorded before fixing anything.

To replace it, copy your `labs/week08/starter/retry.py` and `faults.py`
into `app/`, then change the sibling import in `retry.py`:

    from faults import ContractDrift, RateLimited, ServerError, ToolTimeout
    from .faults import ContractDrift, RateLimited, ServerError, ToolTimeout

Keep these names and signatures, because `pipeline.py` calls them:

    StepPolicy, Attempt, StepResult
    is_retryable(exc) -> bool
    call_with_policy(fn, *args, policy, fallback=None, validate=None,
                     **kwargs) -> StepResult

The policies themselves live in `pipeline.py`, one per step, because the
lecture's rule is to choose them per step, in advance, by consequence.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

# Retryable errors, matched by class name so this file needs neither the
# week 8 `faults.py` nor the `openai` package. The first three are week 8's
# transient faults; the rest are the same three conditions as the `openai`
# client raises them against the real endpoint. `ContractDrift` is
# deliberately absent: the call succeeded, so a retry returns the same
# wrong response again.
RETRYABLE = {"ToolTimeout", "RateLimited", "ServerError",
             "APITimeoutError", "APIConnectionError", "RateLimitError",
             "InternalServerError"}


@dataclass
class StepPolicy:
    attempts: int = 3
    base_delay: float = 0.05
    jitter: bool = True
    max_elapsed: float = 5.0
    on_exhausted: str = "degrade"       # or "escalate"


@dataclass
class Attempt:
    n: int
    error: str | None
    slept: float = 0.0


@dataclass
class StepResult:
    value: object = None
    ok: bool = False
    attempts: list[Attempt] = field(default_factory=list)
    used_fallback: bool = False
    outcome: str = "ok"                 # ok | fallback | degraded | escalated

    @property
    def tries(self) -> int:
        return len(self.attempts)


def is_retryable(exc: BaseException) -> bool:
    return type(exc).__name__ in RETRYABLE


def call_with_policy(fn, *args, policy: StepPolicy, fallback=None,
                     validate=None, **kwargs) -> StepResult:
    """Week 8's ladder: retry with capped, jittered backoff, then fall
    back, then degrade or escalate. Copied from labs/week08/starter."""
    result = StepResult()
    started = time.monotonic()

    for n in range(1, policy.attempts + 1):
        if time.monotonic() - started >= policy.max_elapsed:
            break
        try:
            value = fn(*args, **kwargs)
            if validate is not None:
                validate(value)
            result.attempts.append(Attempt(n=n, error=None))
            result.value = value
            result.ok = True
            result.outcome = "ok"
            return result
        except Exception as exc:                          # noqa: BLE001
            attempt = Attempt(n=n, error=type(exc).__name__)
            result.attempts.append(attempt)
            if not is_retryable(exc) or n == policy.attempts:
                break
            remaining = policy.max_elapsed - (time.monotonic() - started)
            if remaining <= 0:
                break
            delay = policy.base_delay * (2 ** (n - 1))
            if policy.jitter:
                delay *= random.uniform(0.5, 1.5)
            delay = min(delay, remaining)
            if delay > 0:
                time.sleep(delay)
                attempt.slept = delay

    if fallback is not None and time.monotonic() - started < policy.max_elapsed:
        result.used_fallback = True
        try:
            value = fallback(*args, **kwargs)
            if validate is not None:
                validate(value)
            result.value = value
            result.ok = True
            result.outcome = "fallback"
            return result
        except Exception:                                 # noqa: BLE001
            pass

    result.outcome = ("escalated" if policy.on_exhausted == "escalate"
                      else "degraded")
    return result
