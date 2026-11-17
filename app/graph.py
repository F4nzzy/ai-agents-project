"""Stage: the human approval gate. Replaced in week 8.

Week 8 gates exactly one step, the irreversible one, with a LangGraph
`interrupt` and a checkpoint that a second process resumes. In this
application the irreversible step is submitting a case, and it reaches the
gate through one function:

    request_approval(payload: dict, unattended: bool) -> dict

`payload` has the shape of week 8's interrupt: `action`, `case_id`,
`arguments` (the exact arguments, never a summary a model wrote),
`evidence`, `degraded`, and `missing`. The return value has the shape of
week 8's resume value: `verdict` ("approve", "edit", "reject", or
"timeout"), `by`, and, for an edit, the edited `arguments`.

`unattended` is True in batch mode, which is how week 10 runs the
application. Nobody is there to answer, so your gate must return what week
8 decided an unanswered approval does after its timeout, immediately,
instead of waiting for a human who is not coming.

Until you wire yours in, the gate refuses every submission. That is the
safe default for a stub, and it means nothing irreversible can happen.

This is a stage you write rather than copy, because week 8's graph runs over
its own toy tools. Take your `submit` node from `labs/week08/starter/graph.py`
with its `interrupt` call, give it a small graph and a `SqliteSaver` of its
own, and write `request_approval` around it. Keep week 8's rule: above the
interrupt, read only.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid

from project.trace import repo_root

# How long an attended approval waits for a person before the timeout
# default applies. Week 8's decision: an unanswered approval is a reject,
# nothing is submitted, and the case is left for a person to pick up.
APPROVAL_TIMEOUT_S = 60.0
DB = repo_root() / "artifacts" / "app_approvals.sqlite"


def _submit(state: dict) -> dict:
    """Week 8's gated node. Read only above the interrupt, because
    everything above it runs again on resume."""
    from langgraph.types import interrupt
    decision = interrupt(state["payload"])
    return {"decision": decision}


def _ask_a_person(payload: dict, timeout: float) -> dict | None:
    """Wait up to `timeout` seconds for a verdict typed on the console.
    None means nobody answered in time, or nobody is there to answer."""
    answer: list[str] = []
    print(f"\napprove {payload['action']} {payload['case_id']} with "
          f"{payload['arguments']}? [approve/reject] ", end="", flush=True)

    def read() -> None:
        # os.read rather than input(): a thread still blocked in input()
        # when the timeout fires holds the stdin lock, and the interpreter
        # then crashes on exit trying to take it.
        try:
            answer.append(os.read(sys.stdin.fileno(), 256).decode().strip())
        except (OSError, ValueError):
            pass

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    reader.join(timeout)
    if not answer or answer[0] not in ("approve", "reject"):
        return None
    return {"verdict": answer[0], "by": "console"}


def request_approval(payload: dict, unattended: bool = False,
                     timeout: float = APPROVAL_TIMEOUT_S) -> dict:
    """Pause at the gate, ask a person, and apply the timeout default.

    Unattended (week 10's batch mode) means nobody is coming, so the
    timeout default applies at once instead of after `timeout` seconds.
    """
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command
    from typing_extensions import TypedDict

    class GateState(TypedDict, total=False):
        payload: dict
        decision: dict

    graph = StateGraph(GateState)
    graph.add_node("submit", _submit)
    graph.add_edge(START, "submit")
    graph.add_edge("submit", END)

    DB.parent.mkdir(parents=True, exist_ok=True)
    cfg = {"configurable": {
        "thread_id": f"{payload.get('case_id', 'case')}-{uuid.uuid4().hex[:8]}"}}
    with SqliteSaver.from_conn_string(str(DB)) as saver:
        app = graph.compile(checkpointer=saver)
        app.invoke({"payload": payload}, cfg)            # pauses at the gate
        started = time.monotonic()
        answer = None if unattended else _ask_a_person(payload, timeout)
        if answer is None:
            waited = time.monotonic() - started
            answer = {"verdict": "timeout",
                      "by": "unattended" if unattended
                      else f"no answer after {waited:.1f}s"}
        out = app.invoke(Command(resume=answer), cfg)
    return out["decision"]
