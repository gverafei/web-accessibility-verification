"""Verify the complete final release and reconstruct every recorded decision offline."""

import json, collections, math
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
from build_manifest import files
from core import ROOT, cases, digest
from method import evaluate_plan

rows = cases()
assert len(rows) == 534 and len({c["number"] for c in rows}) == 534
assert collections.Counter(c["category"] for c in rows) == {
    "acquired": 69,
    "patched": 257,
    "generated": 208,
}
manifest = ROOT / "MANIFEST.sha256.json"
if manifest.exists():
    manifest_records = json.loads(manifest.read_text())
    assert set(manifest_records) == {
        path.relative_to(ROOT).as_posix() for path in files()
    }, "Manifest file selection differs from the delivered files"
    for name, sha in manifest_records.items():
        assert (ROOT / name).resolve().is_relative_to(ROOT), name
        assert digest(ROOT / name) == sha, name
calls = 0
costs = collections.Counter()
for c in rows:
    assert c["r1"] in ("accepted", "not_accepted") and c["r2"] in (
        "accepted",
        "not_accepted",
    )
    assert "P0" not in c["page_preparation"]
    for v in c["visual_packet"]["views"]:
        assert digest(ROOT / v["path"]) == v["sha256"]
    for route in ("decisions", "luna"):
        plan = json.loads(
            (ROOT / f'study/decisions/{route}/case-{c["number"]}.json').read_text()
        )
        result = evaluate_plan(plan, route)
        assert (
            result["decision"] == c[route]["decision"]
            and result["calls"] == c[route]["calls"]
        )
        assert math.isclose(
            result["cost_usd"], c[route]["usage"]["cost"], abs_tol=1e-10
        )
        assert math.isclose(result["seconds"], c[route]["seconds"], abs_tol=1e-6)
        costs[route] += result["cost_usd"]
        calls += result["calls"]


class CatalogueLinks(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.checked = 0

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key not in {"href", "src"} or not value:
                continue
            target = urlsplit(value)
            if target.scheme or target.netloc or not target.path:
                continue
            path = (self.path.parent / unquote(target.path)).resolve()
            assert (
                path.is_relative_to(ROOT) and path.exists()
            ), f"Broken catalogue link: {self.path.relative_to(ROOT)} -> {value}"
            self.checked += 1


links = 0
catalogue = sorted((ROOT / "supplementary").rglob("*.html"))
assert (
    len(catalogue) == 536
), "The catalogue must contain all 534 cases and both entry pages"
for path in catalogue:
    parser = CatalogueLinks(path)
    parser.feed(path.read_text())
    links += parser.checked
print(
    json.dumps(
        {
            "cases": 534,
            "human_responses": 1068,
            "model_decisions": 1068,
            "requests": calls,
            "verification_cost_usd": dict(costs),
            "catalogue_pages": len(catalogue),
            "local_evidence_links": links,
            "all_checks": "passed",
        },
        indent=2,
    )
)
