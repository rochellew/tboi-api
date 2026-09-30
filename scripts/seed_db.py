"""Seed a SQLite database from the JSON files written by scrape_isaacguru.py.

The database file is deleted and rebuilt on every run, so the result depends
only on the JSON input and the spritesheets saved next to it. Item and pool
icons are cropped out of those sheets here and stored as PNG bytes.

Usage: uv run scripts/seed_db.py [--data data/isaacguru] [--db data/isaacguru.db]
"""

import argparse
import base64
import io
import json
from pathlib import Path

from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tboi_api.db_models import (
    ENTRY_CLASSES,
    Base,
    Challenge,
    Character,
    Entry,
    EntryPool,
    Item,
    EntryReference,
    EntryTag,
    EntryTransformation,
    Pool,
    Synergy,
    Tag,
    Transformation,
    UnlockChallenge,
    UnlockReference,
    UnlockTag,
    create_sqlite_engine,
)

LOOKUP_FILES = {"pools", "tags"}

# Icon cell sizes in the spritesheets, in px.
ITEM_ICON_SIZE = 32
POOL_ICON_SIZE = 13

# JSON keys copied straight onto Entry columns.
ENTRY_FIELDS = [
    "id", "mod", "type", "name", "clean_name", "number", "quality", "pickup_quote",
    "type_label", "description", "unlock", "unlock_text", "stat_changes", "keywords",
    "added_in", "animated", "wti_banned", "youtube_id", "costume_url", "guru_url", "wiki_url",
]  # fmt: skip


def load_json(data_dir: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Read every category file plus the pool and tag lookups."""
    entries = []
    for path in sorted(data_dir.glob("*.json")):
        if path.stem not in LOOKUP_FILES:
            entries.extend(json.loads(path.read_text(encoding="utf-8")))
    pools = json.loads((data_dir / "pools.json").read_text(encoding="utf-8"))
    tags = json.loads((data_dir / "tags.json").read_text(encoding="utf-8"))
    return entries, pools, tags


def load_spritesheets(data_dir: Path) -> dict[str, Image.Image]:
    """Open the sheets scrape_isaacguru.py saved: item icons and pool icons."""
    folder = data_dir / "spritesheets"
    return {"item": Image.open(folder / "isaac.png"), "pool": Image.open(folder / "main.webp")}


def crop_png(sheet: Image.Image, x: int, y: int, size: int) -> bytes:
    """Crop one icon out of a sheet. x and y are CSS offsets, so they're negative."""
    buf = io.BytesIO()
    sheet.crop((-x, -y, -x + size, -y + size)).save(buf, format="PNG")
    return buf.getvalue()


def item_icon(row: dict, sheet: Image.Image) -> dict:
    """Icon columns for an item: a crop of the sheet, or the inline GIF for animated items."""
    if row["sprite_gif"]:
        icon, mime = base64.b64decode(row["sprite_gif"]), "image/gif"
    else:
        icon, mime = crop_png(sheet, row["sprite_x"], 0, ITEM_ICON_SIZE), "image/png"
    return {"sprite_x": row["sprite_x"], "icon": icon, "icon_mime": mime}


def build_pool(row: dict, sheet: Image.Image) -> Pool:
    """A pool row, with its icon cropped from the sheet when the site has one."""
    has_icon = row["sprite_x"] is not None
    return Pool(
        id=row["id"],
        name=row["name"],
        sprite_x=row["sprite_x"],
        sprite_y=row["sprite_y"],
        icon=crop_png(sheet, row["sprite_x"], row["sprite_y"], POOL_ICON_SIZE) if has_icon else None,
    )


def build_entry(row: dict, sheets: dict[str, Image.Image]) -> Entry:
    """Turn one JSON record into the model class for its category."""
    fields = {k: row[k] for k in ENTRY_FIELDS}
    cls = ENTRY_CLASSES[row["category"]]
    if cls is Character:
        fields.update(row["base_stats"] or {})
    elif cls is Transformation:
        fields["tag_id"] = row["tag_id"]
    elif cls is Item:
        fields.update(item_icon(row, sheets["item"]))
    return cls(**fields)


def build_links(row: dict, challenge_ids: dict[str, int]) -> list[Base]:
    """Create the join-table rows (foreign keys) for one JSON record."""
    eid = row["id"]
    return [
        *(EntryPool(entry_id=eid, pool_id=p["pool_id"], weight=p["weight"]) for p in row["pools"]),
        *(EntryTag(entry_id=eid, tag_id=t) for t in row["tag_ids"]),
        *(EntryTransformation(entry_id=eid, transformation_id=t) for t in row["transformation_ids"]),
        *(Synergy(source_id=eid, target_id=s["target_id"], description=s["description"]) for s in row["synergies"]),
        *(EntryReference(source_id=eid, target_id=t) for t in row["referenced_ids"]),
        *(UnlockReference(entry_id=eid, target_id=t) for t in row["unlock_ref_ids"]),
        *(UnlockTag(entry_id=eid, tag_id=t) for t in row["unlock_tag_ids"]),
        *(UnlockChallenge(entry_id=eid, challenge_id=challenge_ids[c]) for c in dict.fromkeys(row["unlock_challenges"])),
    ]


def seed(
    session: Session, entries: list[dict], pools: list[dict], tags: list[dict], sheets: dict[str, Image.Image]
) -> None:
    """Insert lookups, then entries, then the links between them."""
    session.add_all(build_pool(p, sheets["pool"]) for p in pools)
    session.add_all(Tag(id=t["id"], description=t["description"]) for t in tags)

    # Challenges only exist as names in unlock text; sort so ids are stable across runs.
    challenge_names = sorted({c for row in entries for c in row["unlock_challenges"]})
    challenge_ids = {name: i for i, name in enumerate(challenge_names, start=1)}
    session.add_all(Challenge(id=i, name=name) for name, i in challenge_ids.items())
    session.flush()

    session.add_all(build_entry(row, sheets) for row in entries)
    session.flush()

    session.add_all(link for row in entries for link in build_links(row, challenge_ids))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/isaacguru", help="folder of JSON files from scrape_isaacguru.py")
    ap.add_argument("--db", default="data/isaacguru.db", help="SQLite file to (re)create")
    args = ap.parse_args()

    entries, pools, tags = load_json(Path(args.data))
    sheets = load_spritesheets(Path(args.data))

    db_path = Path(args.db)
    db_path.unlink(missing_ok=True)
    engine = create_sqlite_engine(str(db_path))
    Base.metadata.create_all(engine)

    with Session(engine) as session, session.begin():
        seed(session, entries, pools, tags, sheets)

    with Session(engine) as session:
        for table in Base.metadata.sorted_tables:
            count = session.scalar(select(func.count()).select_from(table))
            print(f"{table.name}: {count}")
    print(f"Wrote {db_path}")


if __name__ == "__main__":
    main()
