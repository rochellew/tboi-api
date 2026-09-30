"""Entry -> dict functions for JSON responses."""

from sanic import Request

from tboi_api.db_models import Item, Pool


def base_url(request: Request) -> str:
    return f"{request.scheme}://{request.host}"


def serialize_item(item: Item, request: Request) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "number": item.number,
        "type": item.type,
        "quality": item.quality,
        "pickup_quote": item.pickup_quote,
        "description": item.description,
        "unlock": item.unlock_text,
        "stat_changes": item.stat_changes,
        "pools": [
            {
                "id": link.pool.id,
                "name": link.pool.name,
                "weight": link.weight,
                # Check sprite_x, not icon: icon is deferred, so touching it would query once per pool.
                "icon_url": f"{base_url(request)}/api/pools/{link.pool.id}/icon"
                if link.pool.sprite_x is not None
                else None,
            }
            for link in item.pool_links
        ],
        "tags": [tag.id for tag in item.tags],
        "transformations": [{"id": t.id, "name": t.name} for t in item.transformations],
        "synergies": [
            {"id": s.target.id, "name": s.target.name, "description": s.description}
            for s in item.synergies
        ],
        "image_url": f"{base_url(request)}/api/items/{item.id}/icon",
        "links": {"guru": item.guru_url, "wiki": item.wiki_url},
    }


def serialize_item_summary(item: Item, request: Request) -> dict:
    """Just enough to list an item in search results or autocomplete."""
    return {
        "id": item.id,
        "name": item.name,
        "image_url": f"{base_url(request)}/api/items/{item.id}/icon",
    }

def serialize_pool_summary(pool: Pool, request: Request) -> dict:
    return {
        "id": pool.id,
        "name": pool.name,
        "icon_url": f"{base_url(request)}/api/pools/{pool.id}/icon" if pool.sprite_x is not None else None
    }
