"""Extract isaacguru.com's embedded dataset into per-category JSON files.

The homepage embeds every entry as `items[`mod`][`id`] = {...}` JS objects.
This script parses those, cleans the HTML descriptions, and writes one JSON
file per category plus lookup tables (pools, tags) that entries reference by id.
It also saves the item and pool icon spritesheets to `<out>/spritesheets/`; items
and pools record their offset into those sheets (`sprite_x`, `sprite_y`).

Usage: uv run scripts/scrape_isaacguru.py [--html saved.html] [--out data/isaacguru]
"""

import argparse
import html
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

URL = "https://isaacguru.com/"
BASE = "https://isaacguru.com"

# main_type -> output file name
CATEGORY_FILES = {
    "item": "items",
    "trinket": "trinkets",
    "consumable": "consumables",
    "pickup": "pickups",
    "machine": "machines",
    "character": "characters",
    "transformation": "transformations",
    "curse": "curses",
    "room": "rooms",
}

ENTRY_RE = re.compile(r"items\[`(\w+)`\]\[`([^`]+)`\]\s*=\s*\{(.*?)\n\s*\};", re.S)
FIELD_RE = re.compile(r"(\w+):\s*`(.*?)`,", re.S)
MARKUP_RE = re.compile(r"\{\{(\w+)\|([^|}]*)(?:\|([^}]*))?\}\}")
# Character stat icons are identified by their x offset in the stat spritesheet.
STAT_ICONS = {"-48": "speed", "-64": "tears", "-80": "damage", "-96": "range", "-112": "shot_speed", "-128": "luck"}

# Homepage grid tile for each entry: a 32px cell of the mod spritesheet (`--x`),
# or an inline base64 image for animated entries.
TILE_RE = re.compile(r'itemid="([^"]+)" name="[^"]*">\s*<span class="item-\w+-container[^"]*" style="([^"]*)"')
# Pool icon next to an entry: a 13px cell of the main spritesheet.
POOL_ICON_RE = re.compile(
    r'pool="(\w+)" href="[^"]*"><span class="[^"]*sprite-block-pool[^"]*".*?style="--x: ?(-?\d+)px; --y: ?(-?\d+)px'
)
# CSS variable -> saved file name, under <out>/spritesheets/.
SPRITESHEETS = {"--ssfile-isaac": "isaac.png", "--main-sprite": "main.webp"}


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (data export script)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def fetch(url: str) -> str:
    return fetch_bytes(url).decode("utf-8")


def item_sprite(style: str) -> dict:
    """Where an item's icon lives: an x offset into isaac.png, or an inline GIF (base64)."""
    x = re.search(r"--x: (-?\d+)px", style)
    gif = re.search(r"base64,([A-Za-z0-9+/=]+)", style)
    return {"sprite_x": int(x.group(1)) if x else None, "sprite_gif": gif.group(1) if gif else None}


def download_spritesheets(page: str, out: Path) -> None:
    """Save the spritesheets the homepage CSS points at, so seeding can crop icons offline."""
    folder = out / "spritesheets"
    folder.mkdir(parents=True, exist_ok=True)
    for var, filename in SPRITESHEETS.items():
        path = re.search(rf"{var}: url\(([^)?]+)", page).group(1)
        (folder / filename).write_bytes(fetch_bytes(BASE + path))
        print(f"spritesheets/{filename}")


def span(html_src: str, cls: str) -> str | None:
    """Inner HTML of the first <span class="cls">, handling nested spans."""
    m = re.search(rf"""<span class=["']{re.escape(cls)}["'][^>]*>""", html_src)
    if not m:
        return None
    depth, i = 1, m.end()
    for tag in re.finditer(r"<(/?)span\b[^>]*>", html_src[i:]):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            return html_src[i : i + tag.start()]
    return html_src[i:]


def to_text(fragment: str | None) -> str | None:
    if not fragment:
        return None
    s = re.sub(r"<br\s*/?>", "\n", fragment)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" ?\n ?", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip() or None


def linked_ids(fragment: str | None) -> list[str]:
    """Ids of other entries linked inline, e.g. <a href='/item/c18' id='c18' class='inline-item-link'>."""
    if not fragment:
        return []
    ids = re.findall(r"""<a [^>]*id=['"]([^'"]+)['"][^>]*class=['"]inline-item-link['"]""", fragment)
    return list(dict.fromkeys(ids))


def num(value: str) -> int | float | None:
    if value == "":
        return None
    f = float(value)
    return int(f) if f.is_integer() else f


def split_list(value: str, sep: str) -> list[str]:
    return [v.strip() for v in value.split(sep) if v.strip()]


def parse(page: str):
    entries = []
    pools: dict[str, dict] = {}
    tags: dict[str, dict] = {}
    tiles = dict(TILE_RE.findall(page))

    for mod, entry_id, body in ENTRY_RE.findall(page):
        raw = dict(FIELD_RE.findall(body))
        h = raw["html"]

        # Pool names/weights come from the tooltip anchors; the `pools` field has the canonical ids.
        for pool_id, title in re.findall(r'pool="([^"]+)"[^>]*>.*?data-bs-title="([^"<]*)', h):
            pools.setdefault(pool_id, {"id": pool_id, "name": html.unescape(title).strip()})

        entry_pools = []
        for chunk in raw["pools"].split("@"):
            chunk = chunk.strip(" ,")
            if "#" in chunk and not chunk.startswith("#"):
                pool_id, weight = chunk.split("#", 1)
                entry_pools.append({"pool_id": pool_id, "weight": num(weight.strip(" ,"))})
                pools.setdefault(pool_id, {"id": pool_id, "name": None})

        # Tag tooltips: <span class='tooltip-tag-name'>name</span><hr ...>description
        for name, desc in re.findall(
            r"tooltip-tag-name'>([^<]+)</span><hr class='quick-hr'>(.*?)\"", h, re.S
        ):
            tags.setdefault(name, {"id": name, "description": to_text(html.unescape(desc))})
        entry_tags = raw["tags"].split()
        for t in entry_tags:
            tags.setdefault(t, {"id": t, "description": None})

        contents = span(h, "item-contents")
        synergies = [
            {"target_id": sid, "description": to_text(html.unescape(desc))}
            for sid, desc in re.findall(
                r'<span id="([^"]+)" class="[^"]*synergy-icon[^"]*".*?tooltip-synergy-name\'>[^<]*</span><hr class=\'quick-hr\'>(.*?)"></span>',
                h,
                re.S,
            )
        ]
        stats = {
            STAT_ICONS.get(x, f"stat_{x}"): num(v)
            for x, v in re.findall(
                r"stat-spritesheet' style='[^']*--x: (-?\d+)px[^']*'></span> <meter class=\"character-stat-bar[^\"]*\" value=\"([^\"]+)\"",
                h,
            )
        }
        wiki = re.search(r'href="(https://bindingofisaacrebirth\.wiki\.gg/wiki/[^"]+)"', h)

        entry = {
            "id": entry_id,
            "mod": mod,
            "category": raw["main_type"],
            "type": raw["type"] or None,
            "name": raw["name"],
            "clean_name": raw["clean_name"],
            "number": to_text(span(h, "item-id")),
            "quality": num(raw["quality"]),
            "pickup_quote": (to_text(span(h, "item-description")) or "").strip('"') or None,
            "type_label": to_text(span(h, "item-type")),
            "description": to_text(contents),
            "unlock": raw["unlock"] or None,
            "base_stats": stats or None,
            "stat_changes": split_list(raw["stat_changes"], ","),
            "keywords": raw["keywords"].split(),
            "added_in": raw["added_in"] or None,
            "animated": raw["animated"] == "1",
            "wti_banned": raw["wti_banned"] == "1",
            "youtube_id": raw["youtube"] or None,
            "costume_url": f"{BASE}/core/assets/img/costumes/{raw['costume']}" if raw["costume"] else None,
            "guru_url": f"{BASE}/wiki/{mod}/{entry_id}",
            "wiki_url": wiki.group(1).replace(" ", "_") if wiki else None,
            # --- foreign keys ---
            "pools": entry_pools,  # -> pools.json
            "tag_ids": entry_tags,  # -> tags.json
            "transformation_ids": [],  # -> transformations.json (filled below)
            "synergies": synergies,  # target_id -> any entry
            "referenced_ids": linked_ids(contents),  # -> any entry
            "unlock_ref_ids": [],  # -> any entry (filled below)
            "_raw_transformations": split_list(raw["transformations"], " "),
        }
        if entry["category"] == "item":
            entry.update(item_sprite(tiles[entry_id]))
        entries.append(entry)

    for p in pools.values():
        p["sprite_x"] = p["sprite_y"] = None
    for pool_id, x, y in POOL_ICON_RE.findall(page):
        if pool_id in pools:
            pools[pool_id].update(sprite_x=int(x), sprite_y=int(y))

    return entries, pools, tags


def link(entries):
    by_name, by_cat_name = {}, {}
    for e in entries:
        by_name.setdefault(e["name"].lower(), e["id"])
        by_name.setdefault(e["clean_name"], e["id"])
        by_cat_name.setdefault((e["category"], e["name"].lower()), e["id"])

    transformations = [e for e in entries if e["category"] == "transformation"]
    tag_to_tr = {}
    for tr in transformations:
        # "Obtained by acquiring any 3 items with the <inline-item>guppy</inline-item> tag."
        m = re.search(r"with the (\w+) tag", tr["description"] or "")
        tr["tag_id"] = m.group(1) if m else None
        if tr["tag_id"]:
            tag_to_tr[tr["tag_id"]] = tr["id"]
        tr["member_ids"] = []
        # Transformations without a tag (e.g. Necromancer) name their exact items inline.
        tr["_explicit"] = [] if tr["tag_id"] else [r for r in tr["referenced_ids"]]

    tr_by_clean = {tr["clean_name"]: tr["id"] for tr in transformations}
    tr_by_id = {tr["id"]: tr for tr in transformations}

    for e in entries:
        ids = [tag_to_tr[t] for t in e["tag_ids"] if t in tag_to_tr]
        ids += [tr_by_clean[t] for t in e.pop("_raw_transformations") if t in tr_by_clean]
        ids += [tr["id"] for tr in transformations if e["id"] in tr["_explicit"]]
        e["transformation_ids"] = list(dict.fromkeys(ids))
        for tid in e["transformation_ids"]:
            tr_by_id[tid]["member_ids"].append(e["id"])

        if e["unlock"]:
            refs, tag_refs, challenges = [], [], []
            for kind, name, hint in MARKUP_RE.findall(e["unlock"]):
                key = name.strip().lower()
                if kind == "tag":
                    tag_refs.append(key)
                elif kind == "chal":
                    challenges.append(name.strip())
                elif kind in ("i", "id"):
                    ref = by_cat_name.get((hint, key)) if hint else None
                    ref = ref or by_name.get(key)
                    if ref:
                        refs.append(ref)
            e["unlock_ref_ids"] = list(dict.fromkeys(refs))
            e["unlock_tag_ids"] = tag_refs
            e["unlock_challenges"] = challenges
            e["unlock_text"] = MARKUP_RE.sub(lambda m: m.group(2), e["unlock"])
        else:
            e["unlock_tag_ids"], e["unlock_challenges"], e["unlock_text"] = [], [], None

    for tr in transformations:
        del tr["_explicit"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="use a saved copy of the homepage instead of fetching")
    ap.add_argument("--out", default="data/isaacguru")
    args = ap.parse_args()

    page = Path(args.html).read_text(encoding="utf-8") if args.html else fetch(URL)
    entries, pools, tags = parse(page)
    link(entries)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    download_spritesheets(page, out)

    grouped = defaultdict(list)
    for e in entries:
        grouped[CATEGORY_FILES.get(e["category"], e["category"] + "s")].append(e)

    # Reverse lookups so lookup tables can list their members too.
    for p in pools.values():
        # Some pools only appear as ids; derive a readable name from the camelCase id.
        p["name"] = p["name"] or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", p["id"]).title()
        p["entry_ids"] = [e["id"] for e in entries if any(x["pool_id"] == p["id"] for x in e["pools"])]
    for t in tags.values():
        t["entry_ids"] = [e["id"] for e in entries if t["id"] in e["tag_ids"]]

    files = {**grouped, "pools": sorted(pools.values(), key=lambda p: p["id"]), "tags": sorted(tags.values(), key=lambda t: t["id"])}
    for name, rows in files.items():
        (out / f"{name}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{name}.json: {len(rows)}")


if __name__ == "__main__":
    main()
