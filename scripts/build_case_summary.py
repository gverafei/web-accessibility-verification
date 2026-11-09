"""Create the compact all-case manuscript supplement from frozen records.

Paired reference and target miniatures show every initial image group.
Full-resolution evidence and complete conditional judgments accompany the HTML catalogue.
"""

import argparse
import collections
import io
import json
import math
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit, urljoin

from PIL import Image
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from publication_data import records
from case_metadata import CATEGORY, generator, preparation
from core import ROOT, DIMENSIONS

NAVY = HexColor("#24384c")
BLUE = HexColor("#286da1")
MUTED = HexColor("#62778a")
LINE = HexColor("#d7e2ea")
PALE = HexColor("#f1f5f8")
W, H = A4
MARGIN = 36
CARD_HEIGHT = 240
CLASSES = ("meets", "material_defect", "insufficient")
REPOSITORY_URL = "https://github.com/gverafei/web-accessibility-verification"
CATALOGUE_BASE_URL = REPOSITORY_URL + "/blob/main/supplementary/"


def payload(case):
    """Compact valid JSON, preserving choices and unrounded probabilities."""
    decision, luna = case["decisions"], case["luna"]
    obj = {"decisions": decision["decision"]}
    for dimension in DIMENSIONS:
        answer = decision["answers"][dimension]
        windows = decision["window_results"]
        candidates = [
            w for w in windows if w["answers"][dimension]["choice"] == answer["choice"]
        ]
        selected = (candidates or windows)[0]
        observed = selected["answers"][dimension]
        obj[dimension] = [answer["choice"], selected["index"]] + [
            observed["probabilities"].get(k, 0.0) for k in CLASSES
        ]
    plan = json.loads(
        (ROOT / f'study/decisions/decisions/case-{case["number"]}.json').read_text()
    )
    if plan.get("presentation_impact"):
        obj["visual_impact"] = [
            json.loads((ROOT / call["path"] / "response.json").read_text())["answers"][
                "visual_impact"
            ]["choice"]
            for call in plan["presentation_impact"]
        ]
    obj["luna"] = luna["decision"]
    obj["reviewers"] = [case["r1"], case["r2"]]
    obj["seconds"] = [round(decision["seconds"], 3), round(luna["seconds"], 3)]
    obj["usd"] = [round(decision["usage"]["cost"], 8), round(luna["usage"]["cost"], 8)]
    return obj


def json_lines(obj):
    lines = ["{"]
    for n, (key, value) in enumerate(obj.items()):
        lines.append(
            "  "
            + json.dumps(key)
            + ": "
            + json.dumps(value, separators=(",", ":"))
            + ("," if n < len(obj) - 1 else "")
        )
    return lines + ["}"]


def wrap(text, width, font="Helvetica", size=8):
    """Wrap even long URLs, without truncating source identifiers."""
    lines = []
    line = ""
    for char in text:
        if stringWidth(line + char, font, size) > width:
            cut = line.rfind(" ")
            if cut > len(line) // 2:
                lines.append(line[:cut])
                line = line[cut + 1 :] + char
            else:
                lines.append(line)
                line = char
        else:
            line += char
    if line:
        lines.append(line)
    return lines


def text_block(
    c, text, x, top, width, size=8, leading=11, font="Helvetica", color=NAVY
):
    c.setFont(font, size)
    c.setFillColor(color)
    for line in wrap(text, width, font, size):
        c.drawString(x, top, line)
        top -= leading
    return top


@lru_cache(maxsize=1100)
def thumbnail(path):
    with Image.open(ROOT / path) as im:
        im = im.convert("RGB")
        im.thumbnail((260, 200), Image.Resampling.LANCZOS)
        data = io.BytesIO()
        im.save(data, format="JPEG", quality=72, optimize=True)
    data.seek(0)
    return ImageReader(data)


def frame(c, page, pages):
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN, H - 27, "SUPPLEMENTARY VISUAL EVIDENCE")
    c.drawRightString(
        W - MARGIN, H - 27, "Luna Decisions / conventional Luna / human review"
    )
    c.setStrokeColor(LINE)
    c.line(MARGIN, H - 35, W - MARGIN, H - 35)
    c.setFont("Helvetica", 8)
    c.drawString(
        MARGIN,
        22,
        "Complete evidence: github.com/gverafei/web-accessibility-verification",
    )
    c.drawRightString(W - MARGIN, 22, f"{page} / {pages}")


def index(c, rows, pages, catalogue_url, index_groups):
    frame(c, 1, pages)
    c.bookmarkPage("index")
    c.addOutlineEntry("Case index", "index", 0)
    y = text_block(
        c,
        "Supplementary case summaries",
        MARGIN,
        H - 66,
        W - 2 * MARGIN,
        size=20,
        leading=24,
        font="Helvetica-Bold",
    )
    counts = collections.Counter(r["category"] for r in rows)
    domains = collections.defaultdict(list)
    for r in rows:
        domains[urlsplit(r["url"]).hostname.removeprefix("www.")].append(r)
    summary = (
        f"{len(rows)} cases | {counts['acquired']} acquired | {counts['patched']} patched | "
        f"{counts['generated']} regenerated\n"
    )
    y = text_block(
        c, summary.strip(), MARGIN, y - 6, W - 2 * MARGIN, size=10, leading=14
    )
    y = text_block(
        c,
        f"{len(domains)} source domains | {2*len(rows):,} human responses",
        MARGIN,
        y,
        W - 2 * MARGIN,
        size=10,
    )
    y = text_block(
        c,
        "Each case pairs all reference and target image groups with the recorded results. "
        "Case links open their evidence files on GitHub. Download the repository to browse its HTML catalogue and full-resolution images.",
        MARGIN,
        y - 9,
        W - 2 * MARGIN,
        size=9,
        leading=12,
    )
    c.setFillColor(BLUE)
    c.setFont("Helvetica", 9)
    c.drawString(
        MARGIN, y - 3, "Open GitHub evidence repository and consultation instructions"
    )
    c.linkURL(catalogue_url, (MARGIN, y - 6, MARGIN + 180, y + 7), relative=0)
    y -= 26
    y = text_block(
        c, "JSON key", MARGIN, y, W - 2 * MARGIN, size=10, font="Helvetica-Bold"
    )
    y = text_block(
        c,
        "Dimension arrays: [page finding, image group, P(meets), P(material_defect), P(insufficient)]. Probabilities identify a supporting group; full group and conditional presentation-impact results accompany the HTML case. "
        "Reviewers: [Reviewer 1, Reviewer 2]. Seconds and USD: [Luna Decisions, conventional Luna]. "
        "The content_fidelity field denotes content adequacy for regenerated pages.",
        MARGIN,
        y - 2,
        W - 2 * MARGIN,
        size=8.5,
        leading=12,
    )
    y -= 15
    widths = [34, 149, 85, 85, 85, 85]
    headings = ["Case", "Domain", "Decisions", "Luna", "Reviewer 1", "Reviewer 2"]
    labels = {
        "admitted": "Accepted",
        "rejected": "Not accepted",
        "accepted": "Accepted",
        "not_accepted": "Not accepted",
    }
    for sheet, selected in enumerate(index_groups):
        if sheet:
            frame(c, sheet + 1, pages)
            y = (
                text_block(
                    c,
                    "Case index",
                    MARGIN,
                    H - 65,
                    W - 2 * MARGIN,
                    size=16,
                    leading=22,
                    font="Helvetica-Bold",
                )
                - 12
            )
        c.setFillColor(PALE)
        c.rect(MARGIN, y - 7, sum(widths), 20, fill=1, stroke=0)
        x = MARGIN
        for heading, width in zip(headings, widths):
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(x + 4, y, heading)
            x += width
        for offset, row in enumerate(selected):
            row_y = y - 23 - offset * 12.5
            assert row_y > 45, "Case index overflow"
            values = [
                str(row["number"]),
                urlsplit(row["url"]).hostname.removeprefix("www."),
                labels[row["decisions"]["decision"]],
                labels[row["luna"]["decision"]],
                labels[row["r1"]],
                labels[row["r2"]],
            ]
            x = MARGIN
            for column, (value, width) in enumerate(zip(values, widths)):
                assert stringWidth(value, "Helvetica", 8) < width - 7, (
                    row["number"],
                    value,
                )
                c.setFillColor(BLUE if column == 0 else NAVY)
                c.setFont("Helvetica", 8)
                c.drawString(x + 4, row_y, value)
                x += width
            c.linkRect(
                "",
                f"case{row['number']}",
                (MARGIN, row_y - 3, MARGIN + sum(widths), row_y + 9),
                thickness=0,
            )
        c.showPage()


def plans(row):
    data = json.loads(
        (ROOT / f'contracts/requests/decisions/case-{row["number"]}.json').read_text()
    )
    return data["groups"]


def group_height(g):
    counts = collections.Counter(v["role"] for v in g["assessment"]["views"])
    return 20 + 90 * math.ceil(max(counts.values()) / 2) + 12


def chunks(groups):
    pages = []
    page = []
    height = 0
    for group in groups:
        h = group_height(group)
        if height + h > 550 and page:
            pages.append(page)
            page = []
            height = 0
        assert h <= 550, "Image group exceeds page capacity"
        page.append(group)
        height += h
    if page:
        pages.append(page)
    return pages


def case_page(c, row, groups, page, pages, part, total_parts, base):
    frame(c, page, pages)
    n = row["number"]
    if part == 1:
        c.bookmarkPage(f"case{n}")
        c.addOutlineEntry(f'Case {n} - {urlsplit(row["url"]).hostname}', f"case{n}", 1)
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(BLUE)
    title = f"Case {n}" + (f" | {part}/{total_parts}" if total_parts > 1 else "")
    c.drawString(MARGIN, H - 59, title)
    case_url = base + f"cases/{n:03d}.html"
    c.linkURL(case_url, (MARGIN, H - 65, MARGIN + 145, H - 43), relative=0)
    text_block(
        c, row["url"], MARGIN + 145, H - 57, W - 2 * MARGIN - 145, size=8, leading=10
    )
    y = H - 88
    width = 190
    y = text_block(
        c,
        CATEGORY[row["category"]],
        MARGIN,
        y,
        width,
        size=9,
        leading=12,
        font="Helvetica-Bold",
    )
    y = text_block(c, preparation(row), MARGIN, y - 3, width, size=8, leading=10)
    y = text_block(
        c, "Generator: " + generator(row), MARGIN, y - 3, width, size=7.5, leading=9
    )
    y = text_block(
        c, row["review_id"], MARGIN, y - 3, width, size=7, leading=9, color=MUTED
    )
    labels = {
        "accepted": "Accepted",
        "not_accepted": "Not accepted",
        "admitted": "Admitted",
        "rejected": "Rejected",
    }
    for title, val in [
        ("Luna Decisions", row["decisions"]["decision"]),
        ("Conventional Luna", row["luna"]["decision"]),
        ("Reviewer 1", row["r1"]),
        ("Reviewer 2", row["r2"]),
    ]:
        y = text_block(
            c,
            title + ": " + labels[val],
            MARGIN,
            y - 3,
            width,
            size=7.5,
            leading=9,
            color=MUTED,
        )
    assert y > H - 240, (n, "case metadata overflow")
    code = payload(row)
    x = MARGIN + 202
    size = 6.6
    lines = json_lines(code)
    while max(stringWidth(line, "Courier", size) for line in lines) > W - MARGIN - x:
        size -= 0.1
    assert size >= 6.0, (n, "small JSON")
    c.setFont("Courier", size)
    c.setFillColor(NAVY)
    y = H - 88
    for line in lines:
        c.drawString(x, y, line)
        y -= 9.3
    c.setStrokeColor(LINE)
    c.line(MARGIN, H - 232, W - MARGIN, H - 232)
    top = H - 247
    for group in groups:
        gi = group["index"] + 1
        dwin = next(w for w in row["decisions"]["window_results"] if w["index"] == gi)
        lwin = next(w for w in row["luna"]["window_results"] if w["index"] == gi)
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN, top, f"Image group {gi}")
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawRightString(
            W - MARGIN,
            top,
            f'Decisions: {labels[dwin["decision"]]} | Luna: {labels[lwin["decision"]]}',
        )
        views = group["assessment"]["views"]
        for role, rx in [("reference", MARGIN), ("target", MARGIN + 270)]:
            role_views = [v for v in views if v["role"] == role]
            assert len(role_views) >= 1, (n, gi, role)
            for j, view in enumerate(role_views):
                vx = rx + (j % 2) * 128
                vy = top - 82 - (j // 2) * 90
                c.setFillColor(HexColor("#ffffff"))
                c.setStrokeColor(LINE)
                c.rect(vx, vy, 122, 72, fill=1, stroke=1)
                c.drawImage(
                    thumbnail(view["path"]),
                    vx + 1,
                    vy + 1,
                    120,
                    70,
                    preserveAspectRatio=True,
                    anchor="c",
                )
                c.linkURL(
                    urljoin(base, f'../{view["path"]}'),
                    (vx, vy, vx + 122, vy + 72),
                    relative=0,
                )
                c.setFont("Helvetica", 6.5)
                c.setFillColor(MUTED)
                c.drawString(
                    vx,
                    vy - 9,
                    f'{role.title()} | y={view.get("y",0)}'
                    + (f' | t={view["sample_ms"]} ms' if "sample_ms" in view else "")
                    + f' | {view["width"]} x {view["height"]}',
                )
        confirmed = []
        if dwin.get("confirmed_with_context"):
            confirmed.append("Decisions")
        if lwin.get("confirmed_with_context"):
            confirmed.append("Luna")
        if confirmed:
            c.setFont("Helvetica", 6.5)
            c.setFillColor(MUTED)
            c.drawString(
                MARGIN,
                top - group_height(group) + 10,
                "Neighboring-image confirmation: "
                + ", ".join(confirmed)
                + ". Complete request and answers: linked HTML case.",
            )
        top -= group_height(group)
    c.showPage()


def main():
    global CASE_PAGES
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "runtime/supplementary-cases.pdf",
    )
    parser.add_argument("--catalogue-base-url", default=CATALOGUE_BASE_URL)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(records(), key=lambda row: row["number"])
    index_groups = [rows[:24]] + [
        rows[start : start + 50] for start in range(24, len(rows), 50)
    ]
    all_groups = {r["number"]: plans(r) for r in rows}
    case_chunks = {n: chunks(g) for n, g in all_groups.items()}
    CASE_PAGES = {}
    page = len(index_groups) + 1
    for row in rows:
        CASE_PAGES[row["number"]] = page
        page += len(case_chunks[row["number"]])
    pages = page - 1
    base = args.catalogue_base_url.rstrip("/") + "/"
    if not base.startswith("https://github.com/"):
        raise ValueError("The submission PDF requires a GitHub evidence URL.")
    c = canvas.Canvas(str(output), pagesize=A4, pageCompression=1, invariant=1)
    c.setTitle("Supplementary visual evidence and final case judgments")
    c.setAuthor("A11y Verification study")
    c.setSubject(
        "534 cases, paired reference and target thumbnails, complete initial image groups and final human judgments"
    )
    index(c, rows, pages, REPOSITORY_URL, index_groups)
    shown = 0
    for row in rows:
        parts = case_chunks[row["number"]]
        for offset, chunk in enumerate(parts):
            shown += sum(len(g["assessment"]["views"]) for g in chunk)
            case_page(
                c,
                row,
                chunk,
                CASE_PAGES[row["number"]] + offset,
                pages,
                offset + 1,
                len(parts),
                base,
            )
    c.save()
    print(
        json.dumps(
            {
                "pdf": str(output),
                "pages": pages,
                "cases": len(rows),
                "initial_image_groups": sum(map(len, all_groups.values())),
                "displayed_image_bindings": shown,
                "bytes": output.stat().st_size,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
