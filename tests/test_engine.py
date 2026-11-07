from pathlib import Path

import pytest

from zoho_sync import engine
from zoho_sync.config import Partner, Settings

PDF = b"%PDF-1.5 test"


class FakeClient:
    def __init__(self, rows):
        self.rows = rows  # {plural: [raw dicts]}
        self.pdf_calls = 0

    def list_page(self, plural, page=1, per_page=200, **_):
        rows = self.rows.get(plural, [])
        start = (page - 1) * 2  # tiny pages to exercise paging
        return rows[start:start + 2], start + 2 < len(rows)

    def pdf(self, plural, doc_id):
        self.pdf_calls += 1
        return PDF + doc_id.encode()


def inv(i, company="ABC Ltd", status="sent", date="2026-11-01", mod="t1", customer=None):
    return {"invoice_id": str(i), "invoice_number": f"INV{i}", "date": date, "status": status,
            "customer_name": customer or company, "company_name": company, "total": 100,
            "last_modified_time": mod}


@pytest.fixture
def settings(tmp_path):
    return Settings(output_root=str(tmp_path), doc_types=["invoices"])


def docs(rows, **kw):
    return engine.list_documents(FakeClient({"invoices": rows}), ["invoices"], max_pages=None, **kw)


def test_paging_and_normalize():
    d = docs([inv(i) for i in range(5)])
    assert [x.number for x in d] == [f"INV{i}" for i in range(5)]
    assert d[0].company == "ABC Ltd" and d[0].key == "invoices:0"


def test_skip_status_and_partner_only(settings):
    settings.partners = [Partner("Partner A", ["abc  ltd"])]  # case/space-insensitive match
    settings.partner_only = True
    rows = [inv(1), inv(2, status="draft"), inv(3, company="Other Co")]
    jobs = engine.plan(docs(rows), settings, {"docs": {}})
    assert [j.doc.number for j in jobs] == ["INV1"]
    assert jobs[0].dest.parts[-3:] == ("Partner A", "Invoices", "INV1.pdf")


def test_since_date_and_changed(settings):
    settings.since_date = "2026-11-01"
    state = {"docs": {"invoices:2": {"modified": "t1"}}}
    rows = [inv(1, date="2026-10-01"), inv(2, mod="t2"), inv(3)]
    jobs = engine.plan(docs(rows), settings, state)
    assert {(j.doc.number, j.reason) for j in jobs} == {("INV2", "updated"), ("INV3", "new")}
    assert len(engine.plan(docs(rows), settings, state, mode="all")) == 3


def test_template_and_sanitizing(settings):
    settings.path_template = "{company}/{year}/{type}/{number}_{customer}"
    d = docs([inv(1, company="Elite​IT: Ltd.", customer="Ken, Elite")])[0]
    p = engine.dest_path(d, settings)
    assert p.relative_to(settings.output_root).parts == ("EliteIT_ Ltd", "2026", "Invoices", "INV1_Ken, Elite.pdf")


@pytest.mark.parametrize("mode,expected_files,outcome", [
    ("version", {"INV1.pdf", "INV1_v2.pdf"}, engine.NEW_VERSION),
    ("overwrite", {"INV1.pdf"}, engine.OVERWRITTEN),
    ("skip", {"INV1.pdf"}, engine.SKIPPED),
])
def test_conflict_modes(settings, mode, expected_files, outcome):
    settings.conflict = mode
    state = {"docs": {}}
    client = FakeClient({"invoices": [inv(1)]})
    engine.run(client, engine.plan(docs([inv(1)]), settings, state), settings, state)
    folder = Path(settings.output_root, "ABC Ltd", "Invoices")
    (folder / "INV1.pdf").write_bytes(b"%PDF edited by hand")  # partner edits the file
    client.pdf = lambda plural, i: PDF + b"changed"
    jobs = engine.plan(docs([inv(1, mod="t2")]), settings, state)
    res = engine.run(client, jobs, settings, state)
    assert res[0][1] == outcome
    assert {f.name for f in folder.iterdir()} == expected_files
    if mode == "version":
        assert (folder / "INV1.pdf").read_bytes() == b"%PDF edited by hand"


def test_identical_pdf_not_rewritten(settings):
    state = {"docs": {}}
    client = FakeClient({})
    engine.run(client, engine.plan(docs([inv(1)]), settings, state), settings, state)
    res = engine.run(client, engine.plan(docs([inv(1, mod="t2")]), settings, state), settings, state)
    assert res[0][1] == engine.UNCHANGED
    assert len(list(Path(settings.output_root, "ABC Ltd", "Invoices").iterdir())) == 1


def test_baseline_and_selected(settings):
    state = {"docs": {}}
    d = docs([inv(1), inv(2)])
    engine.mark_baseline(d, state)
    assert engine.plan(d, settings, state) == []
    jobs = engine.plan(d, settings, state, mode="selected", selected={"invoices:2"})
    assert [j.doc.number for j in jobs] == ["INV2"]


def test_list_companies_paging_and_cleanup():
    class C:
        def get(self, path, page=1, **_):
            assert path == "contacts"
            pages = {1: [{"company_name": "b Ltd"}, {"company_name": "", "contact_name": "Walk-in"}],
                     2: [{"company_name": "A​Ltd"}, {"company_name": "b Ltd"}]}
            return {"contacts": pages[page], "page_context": {"has_more_page": page == 1}}
    assert engine.list_companies(C()) == ["ALtd", "b Ltd", "Walk-in"]


def test_rate_header_parsing_and_plan_table():
    from zoho_sync import zoho
    h = {"X-Rate-Limit-Limit": "1000", "X-Rate-Limit-Remaining": "790", "X-Rate-Limit-Reset": "2192",
         "X-User-Access-Limit": "150", "X-Other": "x"}
    assert zoho.parse_rate_headers(h) == {"limit": 1000, "remaining": 790, "reset_in": 2192, "per_minute": 150}
    assert zoho.parse_rate_headers({"X-Rate-Limit-Limit": "abc"}) == {}
    assert zoho.parse_rate_headers(None) == {}
    assert zoho.plan_daily_limit("FREE") == 1000 and zoho.plan_daily_limit("Professional") == 5000
    assert zoho.plan_daily_limit("") is None
