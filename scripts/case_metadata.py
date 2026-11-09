from urllib.parse import urlsplit

CATEGORY = {"acquired": "Acquired", "patched": "Patched", "generated": "Regenerated"}
PREPARATION_ORDER = {
    "Acquisition": 0,
    "Minimal patches": 1,
    "Structural patches": 2,
    "Minimal + structural patches": 3,
    "HTML regeneration": 4,
    "Markdown regeneration": 5,
}


def generator(c):
    return c["generating_model"]


def preparation(c):
    return c["page_preparation"]


def listing_key(c):
    return (
        {"acquired": 0, "patched": 1, "generated": 2}[c["category"]],
        (urlsplit(c["url"]).hostname or "").removeprefix("www."),
        PREPARATION_ORDER[preparation(c)],
        generator(c),
        c["number"],
    )
