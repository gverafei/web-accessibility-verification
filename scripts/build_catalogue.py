"""Build a static catalogue of every final case and its supporting observations."""

import html, json, collections
from pathlib import Path
from urllib.parse import urlsplit
from core import ROOT, cases, DIMENSIONS

E = lambda v: html.escape(str(v), quote=True)
OUT = ROOT / "supplementary"
OUT.mkdir(exist_ok=True)
(OUT / "cases").mkdir(exist_ok=True)
CSS = (
    "body{font:15px/1.5 system-ui,sans-serif;color:#243746;background:#f5f7fa;"
    "max-width:1420px;margin:28px auto;padding:0 22px}h1{font-size:27px}"
    "h2{font-size:20px}h3{font-size:16px}a{color:#286da1}section{background:#fff;"
    "border:1px solid #d9e3ec;border-radius:7px;padding:20px;margin:18px 0}"
    "table{border-collapse:collapse;width:100%;font-size:13px}"
    "th,td{text-align:left;padding:8px;border-bottom:1px solid #dce3e9;"
    "vertical-align:top}th{background:#edf3f7}img{max-width:100%;height:auto;"
    "border:1px solid #dce3e9}.pair{display:grid;grid-template-columns:1fr 1fr;"
    "gap:18px}.muted{color:#63788b;font-size:13px}pre{white-space:pre-wrap;"
    "overflow-wrap:anywhere;font-size:12px}summary{cursor:pointer;margin:9px 0}"
    "code{overflow-wrap:anywhere}figure{margin:8px 0}figcaption{font-size:12px;"
    "color:#63788b}@media(max-width:850px){.pair{grid-template-columns:1fr}"
    ".scroll{overflow:auto}}"
)
(OUT / "catalogue.css").write_text(CSS)


def page(title, body, css):
    return (
        (
            '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>'
        )
        + E(title)
        + '</title><link rel="stylesheet" href="'
        + css
        + '"><body>'
        + body
        + "</body></html>"
    )


def table(headers, rows):
    return (
        '<div class="scroll"><table><thead><tr>'
        + "".join("<th>" + E(h) + "</th>" for h in headers)
        + "</tr></thead><tbody>"
        + "".join(
            "<tr>" + "".join("<td>" + E(v) + "</td>" for v in row) + "</tr>"
            for row in rows
        )
        + "</tbody></table></div>"
    )


def caption(v):
    return f"x={v['x']}; y={v['y']}; {v['width']} × {v['height']}" + (
        f"; t={v['sample_ms']} ms" if "sample_ms" in v else ""
    )


rows = cases()
domains = collections.defaultdict(list)
labels = {
    "accepted": "Accepted",
    "not_accepted": "Not accepted",
    "admitted": "Admitted",
    "rejected": "Rejected",
}
cat = {"acquired": "Acquired", "patched": "Patched", "generated": "Regenerated"}
for c in rows:
    n = c["number"]
    domains[urlsplit(c["url"]).hostname.removeprefix("www.")].append(c)
    b = f'<p><a href="../index.html">All domains and cases</a></p><h1>Case {n} · {E(c["url"])}</h1><p>{cat[c["category"]]} · {E(c["review_id"])}</p>'
    b += f'<p>Page preparation: {E(c["page_preparation"])} · Generating model / reasoning: {E(c["generating_model"])}</p>'
    b += (
        "<section><h2>Final judgments</h2>"
        + table(
            ["Luna Decisions", "Conventional Luna", "Reviewer 1", "Reviewer 2"],
            [
                [
                    labels[c["decisions"]["decision"]],
                    labels[c["luna"]["decision"]],
                    labels[c["r1"]],
                    labels[c["r2"]],
                ]
            ],
        )
        + "</section>"
    )
    b += '<section><h2>Reference and target</h2><div class="pair">'
    for role, key in [("Reference", "acquired_view"), ("Target", "prepared_view")]:
        a = c["assets"][key]
        b += f'<div><h3>{role}</h3><a href="../../{a["path"]}"><img src="../../{a["path"]}" alt="{role} capture"></a><p class="muted">SHA-256: <code>{a["sha256"]}</code></p>'
        if role == "Reference":
            b += f'<p><a href="{E(c["url"])}" target="_blank" rel="noopener noreferrer">Open original URL ↗</a></p>'
        b += "</div>"
    b += "</div></section>"
    b += (
        "<section><h2>Category contract</h2><p>"
        + E(c["visual_packet"]["context"]["contract"])
        + "</p></section>"
    )
    for route, title in [
        ("decisions", "Luna Decisions"),
        ("luna", "Conventional Luna"),
    ]:
        r = c[route]
        b += f'<section><h2>{title} · {labels[r["decision"]]}</h2><p>{r["calls"]} method calls · {r["seconds"]:.2f} seconds · US${r["usage"]["cost"]:.7f}</p>'
        b += table(
            ["Dimension", "Page-level finding"],
            [
                [
                    (
                        "Content adequacy"
                        if k == "content_fidelity" and c["category"] == "generated"
                        else k.replace("_", " ").capitalize()
                    ),
                    a["choice"].replace("_", " "),
                ]
                for k, a in r["answers"].items()
            ],
        )
        for w in r["window_results"]:
            b += (
                f'<details {"open"if w["decision"]=="rejected"else""}><summary>Image group {w["index"]} · {w["decision"]}</summary><p class="muted">'
                + E("; ".join(v["role"] + " " + caption(v) for v in w["views"]))
                + "</p>"
            )
            if route == "decisions":
                b += table(
                    [
                        "Dimension",
                        "Choice",
                        "P(meets)",
                        "P(material defect)",
                        "P(insufficient)",
                    ],
                    [
                        [
                            k.replace("_", " "),
                            a["choice"],
                            *[
                                (
                                    f'{a["probabilities"][q]:.4f}'
                                    if q in a["probabilities"]
                                    else "—"
                                )
                                for q in ("meets", "material_defect", "insufficient")
                            ],
                        ]
                        for k, a in w["answers"].items()
                    ],
                )
            else:
                b += table(
                    ["Dimension", "Choice", "Explanation"],
                    [
                        [k.replace("_", " "), a["choice"], a["rationale"]]
                        for k, a in w["answers"].items()
                    ],
                )
            b += "</details>"
        if r.get("contract_materiality"):
            b += "<h3>Presentation impact</h3>"
            for ch in r["contract_materiality"]["checks"]:
                b += (
                    "<pre>"
                    + E(
                        json.dumps(
                            {"group": ch["window"] + 1, **ch["answer"]}, indent=2
                        )
                    )
                    + "</pre>"
                )
        plan = json.loads((ROOT / f"study/decisions/{route}/case-{n}.json").read_text())
        b += "<details><summary>Requests and responses supporting the final decision</summary><ul>"
        for w in plan["windows"]:
            for key, label in [
                ("assessments", "Assessment"),
                ("context_checks", "Context confirmation"),
            ]:
                for i, call in enumerate(w[key], 1):
                    prefix = "../../" + call["path"]
                    b += (
                        f'<li>Group {w["index"]+1} · {label}'
                        + (" · evidence check" if i > 1 else "")
                        + ": "
                        + f'<a href="{prefix}/request.json">Request JSON</a> · <a href="{prefix}/response.json">Response JSON</a> · <a href="{prefix}/views.json">Image bindings</a></li>'
                    )
        for ch in plan.get("presentation_impact") or []:
            prefix = "../../" + ch["path"]
            b += f'<li>Group {ch["window"]+1} · Presentation impact: <a href="{prefix}/request.json">Request JSON</a> · <a href="{prefix}/response.json">Response JSON</a></li>'
        b += "</ul></details></section>"
    b += '<section><h2>Complete visual evidence</h2><div class="pair">'
    for role in ("reference", "target"):
        views = [v for v in c["visual_packet"]["views"] if v["role"] == role]
        b += (
            f"<div><details><summary>{role.capitalize()} · {len(views)} views</summary>"
        )
        for i, v in enumerate(views, 1):
            b += f'<figure><a href="../../{v["path"]}"><img loading="lazy" src="../../{v["path"]}" alt="{role} view {i}"></a><figcaption>View {i} · {E(caption(v))}</figcaption></figure>'
        b += "</details></div>"
    b += "</div></section><section><h2>Saved HTML and component context</h2><ul>"
    for role, a in c["assets"].items():
        if a["media_type"] == "text/html":
            b += f'<li><a href="../../{a["path"]}" download>{E(role)} HTML</a></li>'
    b += (
        "</ul><details><summary>Component context supplied to the method</summary><pre>"
        + E(json.dumps(c["visual_packet"]["context"], ensure_ascii=False, indent=2))
        + "</pre></details></section>"
    )
    (OUT / "cases" / f"{n:03d}.html").write_text(
        page(f"Case {n}", b, "../catalogue.css")
    )
index = (
    "<h1>Complete evidence catalogue</h1><p>534 cases · 69 acquired · 257 "
    "patched · 208 regenerated · 70 source domains · 1,068 human judgments</p><p>"
    '<a href="../README.md">Consultation and reproduction instructions</a> · <a '
    'href="../analysis/case-comparison.csv">All cases CSV</a> · <a '
    'href="instrument.html">Human-review instrument</a></p>'
)
index += (
    "<p>Supplementary material for the MethodsX article <strong>Automated "
    "Verification of Dynamic Web Pages Using Decision Language Models for Web "
    "Accessibility Remediation</strong>.</p>"
)
index += (
    "<section><h2>Final results</h2><p><img "
    'src="../analysis/model-comparison.png" alt="Model and human decision '
    'agreement by category"></p><p><img src="../analysis/method-resources.png" '
    'alt="Method inference cost and duration by category"></p></section>'
)
for domain, cs in sorted(domains.items()):
    index += f'<section><h2>{E(domain)}</h2><div class="scroll"><table><tr><th>Case</th><th>Category</th><th>Page preparation</th><th>Generating model / reasoning</th><th>Decisions</th><th>Conventional Luna</th><th>Reviewer 1</th><th>Reviewer 2</th></tr>'
    for c in sorted(
        cs,
        key=lambda c: (
            {"acquired": 0, "patched": 1, "generated": 2}[c["category"]],
            c["number"],
        ),
    ):
        index += (
            f'<tr><td><a href="cases/{c["number"]:03d}.html">Case {c["number"]}</a></td>'
            + "".join(
                "<td>" + E(v) + "</td>"
                for v in [
                    cat[c["category"]],
                    c["page_preparation"],
                    c["generating_model"],
                    labels[c["decisions"]["decision"]],
                    labels[c["luna"]["decision"]],
                    labels[c["r1"]],
                    labels[c["r2"]],
                ]
            )
            + "</tr>"
        )
    index += "</table></div></section>"
(OUT / "index.html").write_text(
    page("Complete evidence catalogue", index, "catalogue.css")
)
instrument = (
    '<p><a href="index.html">Evidence catalogue</a></p><h1>Human-review '
    "instrument</h1><section><h2>What to review</h2><ol><li>Identify the target "
    "as Acquired, Patched or Regenerated.</li><li>Apply its category contract "
    "below.</li><li>Inspect all reference and target views, including the lower "
    "page. Compare corresponding content rather than identical coordinates.</li>"
    "<li>Check that main information and meaningful images are coherent and "
    "legible, and that important content and controls are not obscured by "
    "overlap or clipping.</li><li>Check that essential visible links, buttons "
    "and form fields are identifiable and their purpose understandable.</li><li>"
    "Allow advertising changes, coherent carousel states and auxiliary "
    "embedded-media differences when they do not obscure or degrade the main "
    "interface. Distinguish an actual page control from a control depicted "
    "inside an illustration or demonstration.</li><li>Consult the saved "
    "component context when interpreting dynamic regions. Judge the recorded "
    "evidence; testing remote interactions is not required.</li></ol></section>"
    "<section><h2>Category contracts</h2><p><strong>Acquired:</strong> the "
    "reproduction preserves the main reference information, organization and "
    "essential visible controls and remains meaningful and usable. Pre-existing "
    "accessibility violations alone do not justify rejection.</p><p><strong>"
    "Patched:</strong> preserve main source content, images and essential "
    "controls, allowing changes necessary to remove accessibility barriers.</p>"
    "<p><strong>Regenerated:</strong> a different design, wording, image "
    "selection and control arrangement are permitted. Target information and "
    "controls must be coherent and usable for the reference purpose.</p>"
    "</section><section><h2>Response</h2><p><strong>Accepted:</strong> the "
    "target meets the applicable category checks.</p><p><strong>Not "
    "accepted:</strong> the target is blank or blocked, its main information is "
    "incoherent or unreadable, or essential visible controls cannot be "
    "understood. Acquired and patched pages additionally fail when required "
    "source information or controls are lost or distorted.</p><p>Each reviewer "
    "supplies one final page judgment. The review form conceals model outcomes, "
    "model annotations, generator identity, audit scores and the other "
    "reviewer's response.</p></section>"
)
(OUT / "instrument.html").write_text(
    page("Human-review instrument", instrument, "catalogue.css")
)
print("Built final catalogue:", len(rows), "cases,", len(domains), "domains")
