"""Repeat the recorded category-aware method using the supplied request templates."""

import argparse, base64, copy, json, os, time
from core import ROOT, cases, digest, DIMENSIONS
from method import judge, impact

p = argparse.ArgumentParser(description=__doc__)
selection = p.add_mutually_exclusive_group(required=True)
selection.add_argument(
    "--cases",
    nargs="+",
    type=int,
    help="Case numbers in the evidence catalogue and case-comparison.csv",
)
selection.add_argument(
    "--all", action="store_true", help="Select all 534 recorded cases"
)
p.add_argument("--route", choices=["decisions", "luna"], default="decisions")
p.add_argument("--execute", action="store_true")
p.add_argument("--max-usd", type=float)
p.add_argument("--output", default="runtime/replication")
args = p.parse_args()
rows = {c["number"]: c for c in cases()}
args.cases = sorted(rows) if args.all else args.cases
if not set(args.cases) <= set(rows):
    p.error(
        "Unknown case number; consult supplementary/index.html or analysis/case-comparison.csv."
    )
if args.execute:
    assert (
        args.max_usd and args.max_usd > 0 and os.getenv("OPENROUTER_API_KEY")
    ), "Set OPENROUTER_API_KEY and a positive --max-usd."
spent = 0.0
calls = 0
RECOVERY = {
    "round": 1,
    "maximum_rounds": 1,
    "instruction": (
        "Evidence files and available DOM context have been checked. Make a final "
        "judgment of the observed requirements only. Use meets when the observed "
        "interface satisfies them; use material_defect for an observable material "
        "violation. Missing optional widgets, differences allowed by the category, "
        "untested interactions and unseen reference regions are not material "
        "violations. Do not invent a defect to express uncertainty."
    ),
}
protocol = json.loads((ROOT / "contracts/protocol.json").read_text())


def payload(template, recovery=False, visual=False):
    b = copy.deepcopy(template["request"])
    parts = b["state"] if args.route == "decisions" else b["messages"][1]["content"]
    context = json.loads(
        parts[0]
        if args.route == "decisions"
        else parts[0]["text"].split("\nQuestions: ", 1)[0]
    )
    qs = (
        b["questions"]
        if args.route == "decisions"
        else json.loads(parts[0]["text"].split("\nQuestions: ", 1)[1])
    )
    if recovery:
        context["evidence_recovery"] = RECOVERY
        for q in qs.values():
            q["criteria"].pop("insufficient", None)
        if args.route == "luna":
            for q in b["response_format"]["json_schema"]["schema"][
                "properties"
            ].values():
                q["properties"]["choice"]["enum"] = ["meets", "material_defect"]
    if visual:
        qs = {
            "visual_impact": {
                "type": "choice",
                "instructions": protocol["presentation_impact_question"],
                "criteria": {
                    "non_material": "Essential information remains understandable and essential visible controls usable.",
                    "material": "Presentation makes essential information unintelligible or essential visible controls unusable.",
                },
            }
        }
        if args.route == "luna":
            schema = b["response_format"]["json_schema"]["schema"]
            v = copy.deepcopy(next(iter(schema["properties"].values())))
            v["properties"]["choice"]["enum"] = ["non_material", "material"]
            schema["properties"] = {"visual_impact": v}
            schema["required"] = ["visual_impact"]
    if args.route == "decisions":
        parts[0] = json.dumps(context)
        b["questions"] = qs
    else:
        parts[0]["text"] = json.dumps(context) + "\nQuestions: " + json.dumps(qs)
    images = [v for v in parts if isinstance(v, dict) and v.get("type") == "image_url"]
    assert len(images) == len(template["views"])
    for im, v in zip(images, template["views"]):
        data = ROOT / v["path"]
        assert digest(data) == v["sha256"]
        im["image_url"]["url"] = (
            "data:"
            + v["media_type"]
            + ";base64,"
            + base64.b64encode(data.read_bytes()).decode()
        )
    return b


def call(template, label, recovery=False, visual=False):
    global spent, calls
    b = payload(template, recovery, visual)
    if not args.execute:
        return None
    assert (
        spent + 0.05 <= args.max_usd
    ), "Budget reserve reached; choose a smaller case set or increase the explicit limit."
    import requests

    endpoint = (
        "https://openrouter.ai/api/alpha/decisions"
        if args.route == "decisions"
        else "https://openrouter.ai/api/v1/chat/completions"
    )
    t = time.perf_counter()
    response = requests.post(
        endpoint,
        headers={"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"]},
        json=b,
        timeout=180,
    )
    response.raise_for_status()
    r = response.json()
    duration = time.perf_counter() - t
    spent += r["usage"]["cost"]
    calls += 1
    out = ROOT / args.output / args.route / label
    out.mkdir(parents=True, exist_ok=True)
    (out / "response.json").write_text(json.dumps(r, indent=2))
    (out / "timing.json").write_text(
        json.dumps({"seconds": duration, "cost_usd": r["usage"]["cost"]})
    )
    return r


for number in args.cases:
    c = rows[number]
    plan = json.loads(
        (ROOT / f"contracts/requests/{args.route}/case-{number}.json").read_text()
    )
    groups = plan["groups"]
    if not args.execute:
        for g in groups:
            for k in ("assessment", "context_check"):
                payload(g[k])
        print(
            "Validated templates:",
            number,
            c["category"],
            len(groups),
            "groups; no network request",
        )
        continue
    final = []
    dimensions = set()
    for g in groups:
        i = g["index"]
        r = call(g["assessment"], f"case-{number}/group-{i+1}/assessment")
        a, decision = judge(r, args.route)
        if decision is None:
            a, decision = judge(
                call(
                    g["assessment"], f"case-{number}/group-{i+1}/evidence-check", True
                ),
                args.route,
                ("meets", "material_defect"),
            )
        if decision == "rejected":
            a, decision = judge(
                call(g["context_check"], f"case-{number}/group-{i+1}/context"),
                args.route,
            )
            if decision is None:
                a, decision = judge(
                    call(
                        g["context_check"],
                        f"case-{number}/group-{i+1}/context-evidence-check",
                        True,
                    ),
                    args.route,
                    ("meets", "material_defect"),
                )
        assert decision is not None
        final.append(decision)
        dimensions.update(k for k, v in a.items() if v["choice"] == "material_defect")
    decision = "rejected" if "rejected" in final else "admitted"
    if (
        c["category"] == "generated"
        and decision == "rejected"
        and dimensions == {"presentation"}
    ):
        material = False
        for i, d in enumerate(final):
            if (
                d == "rejected"
                and impact(
                    call(
                        groups[i]["context_check"],
                        f"case-{number}/group-{i+1}/presentation-impact",
                        visual=True,
                    ),
                    args.route,
                )["choice"]
                == "material"
            ):
                material = True
                break
        decision = "rejected" if material else "admitted"
    print(number, decision, "calls", calls, "cost USD", spent)
