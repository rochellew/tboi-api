import re

from sanic import Blueprint
from sanic.exceptions import BadRequest, NotFound
from sanic.response import json, raw
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from tboi_api.db_models import Item
from tboi_api.db_models.links import EntryPool, Synergy
from tboi_api.serializers import serialize_item, serialize_item_summary

bp = Blueprint("items", url_prefix="/api/items")

MAX_RESULTS = 25  # Discord autocomplete shows at most 25 choices.


def normalize_name(text: str) -> str:
    """Match isaacguru's `clean_name`: lowercase letters, digits and "?", no leading "the"/"a"."""
    text = re.sub(r"^(the|a)\s+", "", text.strip().lower())
    return re.sub(r"[^a-z0-9?]", "", text)


@bp.get("/")
async def search_items(request):
    """Items whose name contains `q`: exact match first, then prefix matches, then the rest."""
    query = normalize_name(request.args.get("q", ""))
    if not query:
        raise BadRequest("Pass a name to search for, e.g. ?q=eye of belial")
    try:
        # Clamp to 1..MAX_RESULTS; SQLite treats a negative LIMIT as "no limit".
        limit = max(1, min(int(request.args.get("limit", 10)), MAX_RESULTS))
    except ValueError:
        raise BadRequest("limit must be a number")

    rank = case(
        (Item.clean_name == query, 0),
        (Item.clean_name.startswith(query), 1),
        else_=2,
    )
    stmt = select(Item).where(Item.clean_name.contains(query)).order_by(rank, Item.name).limit(limit)
    with Session(request.app.ctx.engine) as session:
        items = session.scalars(stmt).all()
        return json([serialize_item_summary(item, request) for item in items])


@bp.get("/<item_id:str>")
async def get_item(request, item_id: str):
    stmt = (
        select(Item)
        .where(Item.id == item_id)
        .options(
            selectinload(Item.pool_links).selectinload(EntryPool.pool),
            selectinload(Item.tags),
            selectinload(Item.transformations),
            selectinload(Item.synergies).selectinload(Synergy.target),
        )
    )
    with Session(request.app.ctx.engine) as session:
        item = session.scalars(stmt).first()
        if item is None:
            raise NotFound(f"No item with id {item_id!r}")
        return json(serialize_item(item, request))


@bp.get("/<item_id:str>/icon")
async def get_item_icon(request, item_id: str):
    """The item's icon image: PNG, or GIF for animated items."""
    stmt = select(Item.icon, Item.icon_mime).where(Item.id == item_id)
    with Session(request.app.ctx.engine) as session:
        row = session.execute(stmt).first()
    if row is None or row.icon is None:
        raise NotFound(f"No icon for item {item_id!r}")
    return raw(row.icon, content_type=row.icon_mime, headers={"Cache-Control": "public, max-age=86400"})
