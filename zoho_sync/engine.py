"""Sync engine: list Zoho documents, decide what to export, write PDFs safely. No GUI code here."""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from .config import Settings


@dataclass(frozen=True)
class DocType:
    key: str        # API plural, also the settings key
    id_field: str
    number_field: str
    folder: str     # {type} folder name (English, so folders don't change with the UI language)


DOC_TYPES = [  # GUI label: i18n key "doctype.<key>"
    DocType("estimates", "estimate_id", "estimate_number", "Quotes"),
    DocType("invoices", "invoice_id", "invoice_number", "Invoices"),
    DocType("creditnotes", "creditnote_id", "creditnote_number", "Credit Notes"),
    DocType("salesorders", "salesorder_id", "salesorder_number", "Sales Orders"),
    DocType("customerpayments", "payment_id", "payment_number", "Payment Receipts"),
]
TYPES_BY_KEY = {t.key: t for t in DOC_TYPES}

# Known Zoho statuses; GUI label: i18n key "status.<code>" (unknown codes are shown as-is)
STATUSES = ("draft", "sent", "accepted", "declined", "expired", "invoiced", "paid", "partially_paid",
            "overdue", "void", "open", "closed", "unpaid", "approved", "pending_approval", "confirmed",
            "fulfilled")

# write_pdf / run outcomes; GUI label: i18n key "outcome.<code>"
CREATED, OVERWRITTEN, NEW_VERSION, SKIPPED, UNCHANGED, FAILED = (
    "created", "overwritten", "new_version", "skipped", "unchanged", "failed")
WRITTEN = (CREATED, OVERWRITTEN, NEW_VERSION)


@dataclass
class Doc:
    type: DocType
    id: str
    number: str
    date: str
    customer: str
    company: str
    status: str
    total: float
    modified: str

    @property
    def key(self) -> str:
        return f"{self.type.key}:{self.id}"


@dataclass
class Job:
    doc: Doc
    dest: Path
    reason: str     # new | updated | selected


def normalize(t: DocType, raw: dict) -> Doc:
    return Doc(
        type=t, id=str(raw[t.id_field]), number=str(raw.get(t.number_field) or raw[t.id_field]),
        date=raw.get("date", ""), customer=raw.get("customer_name", ""),
        company=(raw.get("company_name") or raw.get("customer_name") or "").strip(),
        status=(raw.get("status") or "").lower(), total=float(raw.get("total") or raw.get("amount") or 0),
        modified=raw.get("last_modified_time") or raw.get("updated_time") or raw.get("date", ""),
    )


def list_documents(client, types: Iterable[str], *, max_pages: int | None = 1,
                   cancelled: Callable[[], bool] = lambda: False, **filters) -> list[Doc]:
    """Newest-modified first. max_pages=1 is the cheap routine poll (1 API call per type)."""
    out: list[Doc] = []
    for key in types:
        t = TYPES_BY_KEY[key]
        page = 1
        while not cancelled():
            rows, more = client.list_page(t.key, page=page, **filters)
            out.extend(normalize(t, r) for r in rows)
            if not more or (max_pages and page >= max_pages):
                break
            page += 1
    return out


def list_companies(client, cancelled: Callable[[], bool] = lambda: False) -> list[str]:
    """All customer companies from the Zoho contact list (usually 1 API call)."""
    names: set[str] = set()
    page = 1
    while not cancelled():
        d = client.get("contacts", contact_type="customer", per_page=200, page=page)
        for c in d.get("contacts", []):
            name = _INVISIBLE.sub("", (c.get("company_name") or c.get("contact_name") or "")).strip()
            if name:
                names.add(name)
        if not d.get("page_context", {}).get("has_more_page"):
            break
        page += 1
    return sorted(names, key=str.casefold)


# ---------- naming ----------

_BAD = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_INVISIBLE = re.compile(r"[​-‏ - ﻿]")
_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe(part: str) -> str:
    part = _BAD.sub("_", _INVISIBLE.sub("", part)).strip().rstrip(". ")
    if part.upper() in _WIN_RESERVED:
        part += "_"
    return part[:120] or "untitled"


def norm_company(name: str) -> str:
    return re.sub(r"\s+", " ", _INVISIBLE.sub("", name)).strip().casefold()


def partner_for(doc: Doc, settings: Settings) -> str | None:
    c = norm_company(doc.company)
    for p in settings.partners:
        if any(norm_company(x) == c for x in p.companies):
            return p.name
    return None


def dest_path(doc: Doc, settings: Settings) -> Path:
    partner = partner_for(doc, settings) or doc.company or doc.customer
    d = datetime.strptime(doc.date, "%Y-%m-%d") if re.match(r"\d{4}-\d{2}-\d{2}$", doc.date) else None
    values = {
        "partner": partner, "company": doc.company or doc.customer, "customer": doc.customer,
        "type": doc.type.folder, "number": doc.number, "status": doc.status,
        "year": f"{d:%Y}" if d else "unknown", "month": f"{d:%m}" if d else "unknown", "date": doc.date,
    }
    template = settings.path_template.strip() or "{partner}/{type}/{number}.pdf"
    parts = [safe(seg.format_map(_Missing(values))) for seg in re.split(r"[\\/]+", template) if seg.strip()]
    if not parts[-1].lower().endswith(".pdf"):
        parts[-1] += ".pdf"
    return Path(settings.output_root).joinpath(*parts)


class _Missing(dict):
    def __missing__(self, k):
        return "{" + k + "}"


# ---------- planning ----------

def wanted(doc: Doc, settings: Settings) -> bool:
    if doc.status in settings.skip_statuses:
        return False
    if settings.partner_only and partner_for(doc, settings) is None:
        return False
    return True


def plan(docs: Iterable[Doc], settings: Settings, state: dict, *, mode: str = "new",
         selected: set[str] | None = None) -> list[Job]:
    """mode: new (routine: new + changed), all (whole history), selected (exactly these keys)."""
    seen = state.setdefault("docs", {})
    jobs = []
    for doc in docs:
        rec = seen.get(doc.key)
        if mode == "selected":
            if selected and doc.key in selected:
                jobs.append(Job(doc, dest_path(doc, settings), "selected"))
            continue
        if not wanted(doc, settings):
            continue
        if rec is None:
            if mode == "new" and settings.since_date and doc.date and doc.date < settings.since_date:
                continue
            jobs.append(Job(doc, dest_path(doc, settings), "new"))
        elif rec.get("modified") != doc.modified:
            jobs.append(Job(doc, dest_path(doc, settings), "updated"))
    return jobs


def mark_baseline(docs: Iterable[Doc], state: dict) -> int:
    """Record docs as already handled without exporting (used for 'start from today')."""
    n = 0
    for doc in docs:
        state.setdefault("docs", {}).setdefault(doc.key, {"modified": doc.modified, "path": None})
        n += 1
    return n


# ---------- writing ----------

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _versioned(path: Path) -> Path:
    stem = re.sub(r"_v\d+$", "", path.stem)
    n = 2
    while True:
        cand = path.with_name(f"{stem}_v{n}{path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def write_pdf(job: Job, data: bytes, settings: Settings, state: dict) -> tuple[str, Path | None]:
    """Returns (outcome, path); outcome is one of CREATED/OVERWRITTEN/NEW_VERSION/SKIPPED/UNCHANGED."""
    rec = state.setdefault("docs", {}).get(job.doc.key) or {}
    digest = _sha(data)
    target = job.dest
    outcome = CREATED
    if rec.get("sha") == digest and rec.get("path") and Path(rec["path"]).exists():
        state["docs"][job.doc.key] = {**rec, "modified": job.doc.modified}
        return UNCHANGED, Path(rec["path"])
    if target.exists():
        if settings.conflict == "skip":
            state["docs"][job.doc.key] = {**rec, "modified": job.doc.modified}
            return SKIPPED, None
        if settings.conflict == "version":
            target, outcome = _versioned(target), NEW_VERSION
        else:
            outcome = OVERWRITTEN
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, target)  # atomic: cloud sync clients never see a half-written PDF
    state["docs"][job.doc.key] = {"modified": job.doc.modified, "path": str(target), "sha": digest,
                                  "number": job.doc.number}
    return outcome, target


def run(client, jobs: list[Job], settings: Settings, state: dict, *,
        progress: Callable[[int, int, Job, str], None] = lambda *a: None,
        cancelled: Callable[[], bool] = lambda: False,
        save: Callable[[dict], None] = lambda s: None) -> list[tuple[Job, str, Path | None, str]]:
    """Returns (job, outcome, path, error) per job; error is "" unless outcome == FAILED."""
    results = []
    for i, job in enumerate(jobs, 1):
        if cancelled():
            break
        try:
            data = client.pdf(job.doc.type.key, job.doc.id)
            outcome, path = write_pdf(job, data, settings, state)
            error = ""
        except Exception as e:  # keep going; one bad doc shouldn't stop the batch
            outcome, path, error = FAILED, None, str(e)
        results.append((job, outcome, path, error))
        progress(i, len(jobs), job, outcome)
        save(state)
    return results
