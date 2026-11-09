"""Category-aware image-group verification and deterministic aggregation."""

import json, math
from core import ROOT, DIMENSIONS


def answers(response, route):
    return (
        response["answers"]
        if route == "decisions"
        else json.loads(response["choices"][0]["message"]["content"])
    )


def judge(response, route, alternatives=("meets", "material_defect", "insufficient")):
    a = answers(response, route)
    assert set(a) == set(DIMENSIONS)
    for value in a.values():
        assert value["choice"] in alternatives
        if route == "decisions":
            assert value["type"] == "choice"
            p = value["probabilities"]
            assert set(p) == set(alternatives)
            assert all(
                type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1
                for x in p.values()
            )
            assert (
                abs(sum(p.values()) - 1) <= 0.001
                and p[value["choice"]] >= max(p.values()) - 1e-8
            )
        else:
            assert isinstance(value["rationale"], str) and value["rationale"].strip()
    if any(v["choice"] == "insufficient" for v in a.values()):
        return a, None
    return a, (
        "rejected"
        if any(v["choice"] == "material_defect" for v in a.values())
        else "admitted"
    )


def impact(response, route):
    a = answers(response, route)
    assert set(a) == {"visual_impact"}
    v = a["visual_impact"]
    assert v["choice"] in ("material", "non_material")
    if route == "decisions":
        p = v["probabilities"]
        assert (
            set(p) == {"material", "non_material"}
            and abs(sum(p.values()) - 1) <= 0.001
            and p[v["choice"]] >= max(p.values()) - 1e-8
        )
    return v


def evaluate_plan(plan, route):
    decisions = []
    dimensions = set()
    cost = seconds = 0.0
    calls = 0

    def read(call):
        nonlocal cost, seconds, calls
        d = ROOT / call["path"]
        response = json.loads((d / "response.json").read_text())
        duration = json.loads((d / "timing.json").read_text())["seconds"]
        assert (
            abs(response["usage"]["cost"] - call["cost_usd"]) < 1e-12
            and abs(duration - call["seconds"]) < 1e-9
        )
        cost += call["cost_usd"]
        seconds += duration
        calls += 1
        return response

    for window in plan["windows"]:
        result = None
        for stage in ("assessments", "context_checks"):
            checks = window[stage]
            if stage == "context_checks":
                assert bool(checks) == (result == "rejected")
            if not checks:
                continue
            assert len(checks) in (1, 2)
            for i, call in enumerate(checks):
                a, result = judge(
                    read(call),
                    route,
                    (
                        ("meets", "material_defect")
                        if i
                        else ("meets", "material_defect", "insufficient")
                    ),
                )
                if result is not None:
                    assert i == len(checks) - 1
            assert result is not None
        decisions.append(result)
        dimensions.update(k for k, v in a.items() if v["choice"] == "material_defect")
    decision = "rejected" if "rejected" in decisions else "admitted"
    if plan["presentation_impact"]:
        assert (
            plan["category"] == "generated"
            and decision == "rejected"
            and dimensions == {"presentation"}
        )
        material = False
        checked = []
        for call in plan["presentation_impact"]:
            checked.append(call["window"])
            v = impact(read(call), route)
            if v["choice"] == "material":
                material = True
                assert call == plan["presentation_impact"][-1]
        if not material:
            assert set(checked) == {
                i for i, d in enumerate(decisions) if d == "rejected"
            }
        decision = "rejected" if material else "admitted"
    assert decision == plan["decision"]
    return {"decision": decision, "calls": calls, "cost_usd": cost, "seconds": seconds}
