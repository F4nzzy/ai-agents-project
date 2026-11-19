"""Block 3: the gates. This is the file that fails a build.

Everything so far printed tables. A table is a thing you read once. A test
is a thing that stops you shipping, and the difference between an
evaluation and a report is exactly this file.

    pytest -q                    # all gates
    pytest -q -m "not judged"    # the free ones only, no model calls

Note what is asserted and what is not. These gates assert properties that
should hold for ANY healthy version of the system, not the specific numbers
this week produced. A test pinned to 0.42 accuracy fails the moment somebody
improves something, gets deleted in week 12, and protects nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "project_spine"))

import judge as J
from dimensions import report
from loader import condition_of, load_goldset, load_traces, source_of

TRACES = load_traces()


# --------------------------------------------------------------------------
# The free gates. No model calls, so these can run on every commit.
# --------------------------------------------------------------------------

def test_traces_exist():
    assert TRACES, "no traces recorded. Week 10 has nothing to evaluate."


def test_every_trace_carries_its_conditions():
    """A number without its conditions is not evidence.

    This is the gate that would have caught the defect in the course's own
    artifacts, where week 9 recorded its run condition under two different
    keys in the same file.
    """
    missing = [t["trace_id"] for t in TRACES
               if not t.get("conditions", {}).get("model")
               or not t["conditions"].get("run_date")]
    assert not missing, f"{len(missing)} traces without model or run_date"


def test_condition_keys_are_consistent_within_a_week():
    """One fact, one home. Two spellings of one condition is a defect.

    Checked per week AND per writer. Your application and a lab script run
    in the same week are two systems with two sets of conditions, and that
    is not a second spelling of anything.
    """
    by_week: dict[tuple[int, str], set[frozenset]] = {}
    for t in TRACES:
        settings = (t.get("conditions", {}).get("settings") or {})
        keys = frozenset(k for k in settings if k != "replay")
        by_week.setdefault((t["week"], source_of(t)), set()).add(keys)
    for (week, source), shapes in by_week.items():
        assert len(shapes) <= 1, (
            f"week {week} ({source}) records its conditions under more than "
            f"one set of keys: {sorted(tuple(sorted(s)) for s in shapes)}")


def test_failures_flag_themselves():
    """Predictability floor. A failure that looks like a success cannot be
    routed by anything downstream, so a system where most of them are
    invisible is not ready for a gate."""
    dims = {d.name: d for d in report(TRACES)}
    value = dims["predictability"].value
    if value is None:
        pytest.skip("no failed runs recorded")
    assert value >= 0.5, (
        f"only {value:.0%} of failed runs flagged themselves. "
        f"{dims['predictability'].detail}")


def test_goldset_cases_are_unique():
    cases = load_goldset()
    ids = [c["case_id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case_id in the gold set"


def test_goldset_grew_with_the_project():
    """The gold set is the project's memory. A flat one means nobody added
    the cases their own week discovered."""
    weeks = {c.get("week_added") for c in load_goldset()}
    assert len(weeks) >= 3, f"gold set only has cases from weeks {weeks}"


# --------------------------------------------------------------------------
# TODO 5. The judged gates, marked so they can be skipped.
# --------------------------------------------------------------------------

@pytest.mark.judged
def test_judge_agrees_with_human_labels():
    """TODO 5a. The gate that licenses every other judged number.

    Load the recorded judgments, validate them against the labels, and
    assert the agreement rate clears a bar you can defend. Skip, do not
    fail, when no judgments have been recorded yet.

    An unvalidated judge is not a control. If this gate fails, no judged
    metric anywhere in your report means anything, which is why it is a
    test and not a paragraph in a README.
    """
    agreement = _validated()
    assert agreement.n == len(J.LABELS), (
        f"only {agreement.n} of {len(J.LABELS)} labelled cases have a "
        f"judgment. Finish `python 02_judge.py` before trusting any score.")

    # The four controls are cases nobody could disagree on. A judge that
    # misses one of them is not worth validating on the arguable eight.
    missed = [r["case_id"] for r in agreement.rows
              if r["case_id"] in CONTROLS and r["human"] != r["judge"]]
    assert not missed, f"judge got an obvious control case wrong: {missed}"

    # The bar: at most one disagreement in twelve (0.9 lets 11/12 through).
    # Twelve labels cannot support a finer claim than that, and a bar of
    # 1.0 would make the gate fail on the first honest disagreement about
    # an arguable case, which is a reason to argue, not to stop a build.
    assert agreement.rate >= MIN_AGREEMENT, (
        f"judge agrees with the hand labels on {agreement.agreed}/"
        f"{agreement.n} = {agreement.rate:.2f} at threshold {J.THRESHOLD}, "
        f"below {MIN_AGREEMENT}. Disagreements: "
        f"{[r['case_id'] for r in agreement.rows if r['human'] != r['judge']]}")


@pytest.mark.judged
def test_judge_makes_no_false_passes():
    """TODO 5b. The asymmetric gate.

    A false fail costs a human's attention. A false pass means your gate
    went green on an invented answer. Forbid only the second, and say in
    one comment why you are not forbidding both.
    """
    agreement = _validated()
    # False fails are allowed through this gate (5a still bounds them):
    # one costs a reviewer a look at a correct answer. A false pass is an
    # invented fee or deadline reaching a resident with a green tick on
    # it, and there is no downstream step that catches it.
    false_passes = [f"{r['case_id']} (score {r['score']:.2f}: {r['why_human']})"
                    for r in agreement.rows
                    if r["human"] == "fail" and r["judge"] == "pass"]
    assert not false_passes, (
        f"at threshold {J.THRESHOLD} the judge PASSED {len(false_passes)} "
        f"answer(s) a human failed: {false_passes}")


@pytest.mark.judged
def test_threshold_is_not_on_a_cliff():
    """TODO 5c. Would a small change to the threshold change the verdicts?

    Compute agreement at THRESHOLD and at plus and minus 0.05, and assert
    they are close. If nudging the threshold moves agreement, the number you
    are about to report is an artefact of a library default that nobody
    chose, and you should find that out now rather than in week 12.
    """
    judgments = _recorded_or_skip()
    rates = {round(t, 2): J.validate(judgments, threshold=t).rate
             for t in (J.THRESHOLD - NUDGE, J.THRESHOLD, J.THRESHOLD + NUDGE)}
    # "Close" means no more than one case flips per nudge. On twelve labels
    # that is a 0.083 move; anything bigger and the reported agreement is a
    # property of where the default happened to land, not of the judge.
    tolerance = 1 / len(J.LABELS) + 1e-9
    spread = max(rates.values()) - min(rates.values())
    assert spread <= tolerance, (
        f"agreement moves by {spread:.2f} within +/-{NUDGE} of the threshold "
        f"{J.THRESHOLD}: {rates}. The threshold sits on a cliff.")


# --------------------------------------------------------------------------
# Helpers for the judged gates. Nothing here calls a model: the gates read
# the RECORDED scores and recompute every verdict at the live threshold.
# --------------------------------------------------------------------------

CONTROLS = {"L-01", "L-02", "L-03", "L-04"}
MIN_AGREEMENT = 0.9
NUDGE = 0.05


def _recorded_or_skip() -> dict:
    judgments = J.load_recorded()
    if not judgments:
        pytest.skip("no judgments recorded yet. Run `python 02_judge.py`.")
    return judgments


def _validated():
    return J.validate(_recorded_or_skip())
