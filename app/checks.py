"""Stage: the deterministic checks and the triage. Replaced in week 9.

Until you wire yours in, there are no checks, and the stub says so by
firing: a missing check must never look like a passed one. The triage
therefore never lets an invoice skip the approval gate.

To replace it, copy your `labs/week09/starter/checks.py` over this file (it
has no sibling imports), then move your `code_triage` and its
`AUTO_APPROVE_LIMIT_EUR` across from `labs/week09/starter/03_untrusted.py`.
Week 9's homework was to send a failed check to the week 8 gate, and that
is exactly what `pipeline.py` does with the triage's answer.

Keep these names and signatures, because `pipeline.py` calls them:

    GROUPS: dict[str, list[str]]
    CheckReport                       fired, parsed, clean
    run_checks(fields) -> CheckReport
    code_triage(fields, report) -> tuple[bool, str]
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Copied from labs/week09/starter/checks.py and 03_untrusted.py.
VAT_RATE = 0.17
INVOICE_RE = re.compile(r"^INV-\d{3}-LU$")
PO_RE = re.compile(r"^PO-\d{4}-\d{4}$")
CURRENCIES = {"EUR"}
AUTO_APPROVE_LIMIT_EUR = 1000.0

GROUPS = {
    "identity": ["invoice_number", "purchase_order", "currency"],
    "amounts": ["net_amount", "vat_amount", "total_amount"],
}
ALL_FIELDS = [f for g in GROUPS.values() for f in g]


def parse_amount(text: str | None) -> float | None:
    """`1 129.23` as Luxembourg prints it. A space is removed only where it
    separates a digit from a group of exactly three."""
    if text is None:
        return None
    s = str(text).replace(" ", " ").replace("EUR", "").strip()
    s = re.sub(r"(?<=\d) (?=\d{3}\b)", "", s)
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif re.fullmatch(r"-?\d+,\d{1,2}", s):
        s = s.replace(",", ".")
    if not re.fullmatch(r"-?\d+(\.\d{1,2})?", s):
        return None
    return round(float(s), 2)


@dataclass
class CheckReport:
    fired: list[str]
    parsed: dict[str, float | None]

    @property
    def clean(self) -> bool:
        return not self.fired


def run_checks(fields: dict[str, str | None]) -> CheckReport:
    """Four deterministic checks, none of them a model."""
    parsed = {"net": parse_amount(fields.get("net_amount")),
              "vat": parse_amount(fields.get("vat_amount")),
              "total": parse_amount(fields.get("total_amount"))}
    net, vat, total = parsed["net"], parsed["vat"], parsed["total"]
    fired: list[str] = []

    missing = [k for k, v in parsed.items() if v is None]
    if missing:
        fired.append(f"arithmetic: no readable {', '.join(missing)}")
    elif abs(net + vat - total) >= 0.01:
        fired.append(f"arithmetic: net {net:.2f} + vat {vat:.2f} is not "
                     f"total {total:.2f}")

    if net is not None and vat is not None and net > 0:
        if abs(vat - round(net * VAT_RATE, 2)) > 0.01:
            fired.append(f"vat rate: {vat / net:.4f} is not {VAT_RATE}")

    if not INVOICE_RE.match(fields.get("invoice_number") or ""):
        fired.append("format: invoice_number is not INV-NNN-LU")
    po = fields.get("purchase_order")
    if po is not None and not PO_RE.match(po):
        fired.append("format: purchase_order is not PO-NNNN-NNNN")
    if fields.get("currency") not in CURRENCIES:
        fired.append("format: currency is not EUR")

    if total is not None and not (10.0 <= total <= 10_000.0):
        fired.append(f"plausibility: total {total:.2f} outside 10-10000 EUR")

    return CheckReport(fired=fired, parsed=parsed)


def code_triage(fields: dict, report) -> tuple[bool, str]:
    """May this invoice skip the approval gate? `fields` is never read:
    only a boolean and the parsed total reach the decision, so no sentence
    printed on the page can move it. A False here sends the invoice to the
    week 8 gate in `pipeline._image`."""
    total = report.parsed.get("total")
    if not report.clean:
        return False, f"{len(report.fired)} check(s) fired, so a person decides"
    if total is None:
        return False, "no readable total, so a person decides"
    if total > AUTO_APPROVE_LIMIT_EUR:
        return False, (f"total {total:.2f} EUR is over the "
                       f"{AUTO_APPROVE_LIMIT_EUR:.0f} EUR limit")
    return True, f"checks clean and total {total:.2f} EUR within the limit"
