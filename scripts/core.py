"""Final-study data and deterministic paired-decision statistics."""

import json, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = (
    "content_fidelity",
    "presentation",
    "controls",
    "evidence_coherence",
    "semantic_adequacy",
)


def cases():
    return json.loads((ROOT / "study/cases.json").read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def statistics(rows):
    result = {}
    for label, rs in [
        ("all", rows),
        ("acquired", [r for r in rows if r["category"] == "acquired"]),
        ("remediated", [r for r in rows if r["category"] != "acquired"]),
    ]:
        pairs = {}
        for a, b in [("automatic", "r1"), ("automatic", "r2"), ("r1", "r2")]:
            valid = [
                r
                for r in rs
                if r.get(a) in ("accepted", "not_accepted")
                and r.get(b) in ("accepted", "not_accepted")
            ]
            matrix = [
                [
                    sum((r[a] == x and r[b] == y for r in valid))
                    for y in ("accepted", "not_accepted")
                ]
                for x in ("accepted", "not_accepted")
            ]
            n = len(valid)
            equal = sum((matrix[i][i] for i in (0, 1)))
            pe = (
                sum((sum(matrix[i]) * sum((row[i] for row in matrix)) for i in (0, 1)))
                / (n * n)
                if n
                else 0
            )
            pairs[a + "_" + b] = {
                "n": n,
                "equal": equal,
                "agreement": equal / n if n else None,
                "matrix": matrix,
                "kappa": (equal / n - pe) / (1 - pe) if n and pe < 1 else None,
            }
        result[label] = {"n": len(rs), "pairs": pairs}
    return result
