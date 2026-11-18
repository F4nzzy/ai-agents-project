"""Stage: the vision step. Replaced in week 9.

Runs only when a request comes with an image (`python -m app.run --image
PATH "<request>"`). Until you wire yours in, it refuses: every read comes
back with `failure` set, so no field reaches the checks.

To replace it, copy your `labs/week09/starter/vision.py` and `perturb.py`
into `app/`, then change the sibling import in `vision.py`:

    from perturb import apply_variant
    from .perturb import apply_variant

Keep these names and signatures, because `pipeline.py` calls them:

    MODEL: str
    VisionResult                      fields, failure, ok, elapsed_s,
                                      prompt_tokens, output_tokens
    read_group(image_path, group, fields, variant="clean", replay=None,
               record=None, system=None, prompt=None) -> VisionResult
"""

from __future__ import annotations

import base64
import io
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

# Copied from labs/week09/starter/vision.py. The application only ever reads
# the image as it arrived, so `perturb.py` is not needed here: `encode`
# sends the clean image and refuses any other variant.
MODEL = "qwen3-vl:4b"
ENDPOINT = "http://127.0.0.1:11434/api/chat"
TIMEOUT_S = 300

SYSTEM = (
    "You read Luxembourg invoices. Return each requested field exactly as it "
    "is printed on the page, as a string, including any spaces used as "
    "thousands separators. If a field is NOT PRESENT on the page, return null "
    "for it. Never guess a value that is not printed."
)


@dataclass
class VisionResult:
    doc: str
    group: str
    variant: str
    fields: dict[str, str | None] = field(default_factory=dict)
    failure: str | None = None
    elapsed_s: float = 0.0
    prompt_tokens: int = 0
    output_tokens: int = 0
    done_reason: str = ""
    raw_content: str = ""

    @property
    def ok(self) -> bool:
        return self.failure is None


def encode(path: Path, variant: str = "clean") -> str:
    """Base64 PNG of the image as it arrived."""
    if variant != "clean":
        raise ValueError("the application reads clean images only; "
                         "degraded variants live in labs/week09/perturb.py")
    from PIL import Image
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def flat_schema(fields: list[str]) -> dict:
    return {"type": "object",
            "properties": {f: {"type": ["string", "null"]} for f in fields},
            "required": list(fields)}


def guard(content: str, thinking: str, done_reason: str,
          fields: list[str]) -> tuple[dict | None, str | None]:
    """Refuse every silent failure: overrun, empty content, not JSON, a
    missing key, and an object whose every value is blank."""
    if done_reason == "length":
        return None, ("done_reason=length: the output hit the context "
                      "ceiling before an answer was written")
    if not content or not content.strip():
        if thinking and thinking.strip():
            return None, ("empty content, and the answer went to `thinking` "
                          "instead (the think=False symptom)")
        return None, "empty content"
    try:
        obj = json.loads(content)
    except json.JSONDecodeError as exc:
        return None, f"content is not valid JSON: {exc.msg} at char {exc.pos}"
    if not isinstance(obj, dict):
        return None, f"content parsed to a {type(obj).__name__}, not an object"
    missing = [f for f in fields if f not in obj]
    if missing:
        return None, f"required keys missing: {missing}"
    values = {f: (None if obj[f] is None or not str(obj[f]).strip()
                  else str(obj[f]).strip()) for f in fields}
    if all(v is None for v in values.values()):
        return None, ("every value is null or blank: the object parsed and "
                      "has every key, and says nothing")
    return values, None


def read_group(image_path: Path, group: str, fields: list[str],
               variant: str = "clean", replay=None, record=None,
               system: str | None = None,
               prompt: str | None = None) -> VisionResult:
    """Read one group of fields from one image. `think` is not passed:
    thinking is what makes this model read correctly."""
    doc = Path(image_path).stem
    if replay is not None:
        hit = replay.get(doc, group, variant)
        if hit is not None:
            return hit
    body = {
        "model": MODEL,
        "stream": False,
        "format": flat_schema(fields),
        "options": {"temperature": 0.0},
        "messages": [
            {"role": "system", "content": system or SYSTEM},
            {"role": "user",
             "content": prompt or (f"Read these fields from this invoice: "
                                   f"{', '.join(fields)}."),
             "images": [encode(Path(image_path), variant)]},
        ],
    }
    started = time.perf_counter()
    try:
        request = urllib.request.Request(
            ENDPOINT, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as resp:
            reply = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, OSError,
            json.JSONDecodeError) as exc:
        return VisionResult(doc=doc, group=group, variant=variant,
                            failure=f"transport: {type(exc).__name__}: "
                                    f"{str(exc)[:120]}",
                            elapsed_s=time.perf_counter() - started)
    message = reply.get("message") or {}
    content = message.get("content") or ""
    done_reason = reply.get("done_reason") or ""
    parsed, failure = guard(content, message.get("thinking") or "",
                            done_reason, fields)
    out = VisionResult(doc=doc, group=group, variant=variant,
                       fields=parsed or {}, failure=failure,
                       elapsed_s=time.perf_counter() - started,
                       prompt_tokens=reply.get("prompt_eval_count") or 0,
                       output_tokens=reply.get("eval_count") or 0,
                       done_reason=done_reason, raw_content=content)
    if record is not None:
        record.put(out)
    return out
