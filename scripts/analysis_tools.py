"""Case-bound statistics for frozen judgments; no inference or label changes."""

import json, collections, statistics as st
from urllib.parse import urlsplit
import numpy as np
from case_metadata import preparation, generator, PREPARATION_ORDER
from core import ROOT, cases, statistics, DIMENSIONS


def records():
    return cases()


def group(rows, route):
    rs = (
        [{**r, "automatic": r[route + "_label"]} for r in rows]
        if route != "historical"
        else rows
    )
    result = statistics(rs)["all"]
    result["outcomes"] = dict(collections.Counter(r["automatic"] for r in rs))
    result["domains"] = len(
        {urlsplit(r["url"]).hostname.removeprefix("www.") for r in rs}
    )
    result["triplets"] = dict(
        collections.Counter(
            (
                "unresolved"
                if r["automatic"] == "unresolved"
                else (
                    "all_agree"
                    if r["automatic"] == r["r1"] == r["r2"]
                    else "humans_differ" if r["r1"] != r["r2"] else "humans_oppose"
                )
            )
            for r in rs
        )
    )
    for key, pair in result["pairs"].items():
        a, b = {
            "automatic_r1": ("automatic", "r1"),
            "automatic_r2": ("automatic", "r2"),
            "r1_r2": ("r1", "r2"),
        }[key]
        valid = [
            r
            for r in rs
            if r[a] in ("accepted", "not_accepted")
            and r[b] in ("accepted", "not_accepted")
        ]
        domains = sorted(
            {urlsplit(r["url"]).hostname.removeprefix("www.") for r in valid}
        )
        matrix = pair["matrix"]
        admitted = sum(row[0] for row in matrix)
        rejected = sum(row[1] for row in matrix)
        accept_rate = matrix[0][0] / admitted if admitted else None
        reject_rate = matrix[1][1] / rejected if rejected else None
        pair["reference_classes"] = {
            "accepted_n": admitted,
            "rejected_n": rejected,
            "accept_agreement": accept_rate,
            "reject_agreement": reject_rate,
            "balanced_agreement": (
                (accept_rate + reject_rate) / 2
                if accept_rate is not None and reject_rate is not None
                else None
            ),
            "always_accept_agreement": admitted / len(valid) if valid else None,
        }
        if not domains:
            pair["ci95"] = None
            continue
        counts = np.array(
            [
                [
                    sum(
                        r[a] == r[b]
                        for r in valid
                        if urlsplit(r["url"]).hostname.removeprefix("www.") == d
                    ),
                    sum(
                        urlsplit(r["url"]).hostname.removeprefix("www.") == d
                        for r in valid
                    ),
                ]
                for d in domains
            ]
        )
        rng = np.random.default_rng(20261031)
        s = counts[rng.integers(0, len(domains), (10000, len(domains)))].sum(axis=1)
        pair["ci95"] = np.percentile(100 * s[:, 0] / s[:, 1], [2.5, 97.5]).tolist()
    if route != "historical":
        calls = [r[route] for r in rows if r[route].get("status") == "completed"]
        times = [x["seconds"] for x in calls]
        costs = [x["usage"]["cost"] for x in calls]
        result["resources"] = {
            "completed_cases": len(calls),
            "completed_calls": sum(x.get("calls", 1) for x in calls),
            "recovery_calls": sum(x.get("calls", 1) - 1 for x in calls),
            "cost_usd": sum(costs),
            "mean_cost_usd": st.mean(costs) if costs else None,
            "request_seconds_sum": sum(times),
            "seconds_median": st.median(times) if times else None,
            "seconds_p95": float(np.percentile(times, 95)) if times else None,
        }
    return result


def report(rows):
    groups = {
        "all": rows,
        "acquired": [r for r in rows if r["category"] == "acquired"],
        "remediated": [r for r in rows if r["category"] != "acquired"],
    }
    groups.update(
        {c: [r for r in rows if r["category"] == c] for c in ["patched", "generated"]}
    )
    out = {
        "case_count": len(rows),
        "bootstrap": {"unit": "source domain", "replicates": 10000, "seed": 20261031},
        "routes": {
            route: {name: group(rs, route) for name, rs in groups.items()}
            for route in ["decisions", "luna"]
        },
    }
    out["strategies"] = {
        name: {
            route: group([r for r in rows if preparation(r) == name], route)
            for route in ["decisions", "luna"]
        }
        for name in PREPARATION_ORDER
        if name != "Acquisition" and any(preparation(r) == name for r in rows)
    }
    out["generators"] = {
        name: {
            route: group(
                [
                    r
                    for r in rows
                    if r["category"] != "acquired" and generator(r) == name
                ],
                route,
            )
            for route in ["decisions", "luna"]
        }
        for name in dict.fromkeys(
            generator(r) for r in rows if r["category"] != "acquired"
        )
    }
    out["audit_groups"] = {}
    for key, selected in [
        (
            "audit_target",
            [
                r
                for r in rows
                if r["category"] != "acquired"
                and r.get("metrics", {}).get("axe", 999) <= 5
                and r.get("metrics", {}).get("lighthouse", 0) >= 95
            ],
        ),
        (
            "low_word_target",
            [
                r
                for r in rows
                if r["category"] != "acquired"
                and r.get("metrics", {}).get("axe", 999) <= 5
                and r.get("metrics", {}).get("lighthouse", 0) >= 95
                and r.get("metrics", {}).get("text_percent", 100) < 80
            ],
        ),
    ]:
        out["audit_groups"][key] = {
            route: group(selected, route) for route in ["decisions", "luna"]
        }
    out["dimensions"] = {
        d: dict(
            collections.Counter(
                r["decisions"].get("answers", {}).get(d, {}).get("choice", "unresolved")
                for r in rows
            )
        )
        for d in DIMENSIONS
    }
    # Matched route comparisons use the same conclusive cases and preserved human labels.
    out["matched_routes"] = {}
    for name, rs in groups.items():
        by_reviewer = {}
        for reviewer in ["r1", "r2"]:
            valid = [
                r
                for r in rs
                if r["decisions_label"] != "unresolved"
                and r["luna_label"] != "unresolved"
            ]
            better = sum(
                r["decisions_label"] == r[reviewer] and r["luna_label"] != r[reviewer]
                for r in valid
            )
            worse = sum(
                r["decisions_label"] != r[reviewer] and r["luna_label"] == r[reviewer]
                for r in valid
            )
            import math

            n = better + worse
            pvalue = (
                min(
                    1.0,
                    2
                    * sum(math.comb(n, k) for k in range(min(better, worse) + 1))
                    / 2**n,
                )
                if n
                else 1.0
            )
            domains = sorted(
                {urlsplit(r["url"]).hostname.removeprefix("www.") for r in valid}
            )
            delta_ci = None
            if domains:
                grouped = np.array(
                    [
                        [
                            sum(
                                int(r["decisions_label"] == r[reviewer])
                                - int(r["luna_label"] == r[reviewer])
                                for r in valid
                                if urlsplit(r["url"]).hostname.removeprefix("www.")
                                == domain
                            ),
                            sum(
                                urlsplit(r["url"]).hostname.removeprefix("www.")
                                == domain
                                for r in valid
                            ),
                        ]
                        for domain in domains
                    ]
                )
                rng = np.random.default_rng(20261031)
                draw = grouped[
                    rng.integers(0, len(domains), (10000, len(domains)))
                ].sum(axis=1)
                delta_ci = np.percentile(
                    100 * draw[:, 0] / draw[:, 1], [2.5, 97.5]
                ).tolist()
            by_reviewer[reviewer] = {
                "difference_ci95_pp": delta_ci,
                "n": len(valid),
                "decisions_only_correct": better,
                "luna_only_correct": worse,
                "exact_mcnemar_p": pvalue,
                "agreement_difference_pp": (
                    100 * (better - worse) / len(valid) if valid else None
                ),
            }
        out["matched_routes"][name] = by_reviewer
    return out
