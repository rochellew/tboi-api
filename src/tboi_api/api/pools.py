from sanic import Blueprint
from sanic.exceptions import NotFound
from sanic.response import json, raw
from sqlalchemy import select
from sqlalchemy.orm import Session

from tboi_api.db_models import Pool

from tboi_api.serializers import serialize_pool_summary

bp = Blueprint("pools", url_prefix="/api/pools")

@bp.get("/")
async def list_pools(request):
    with Session(request.app.ctx.engine) as session:
        pools = session.scalars(select(Pool)).all()
        return json([serialize_pool_summary(pool, request) for pool in pools])
    
@bp.get("/<pool_id:str>/icon")
async def get_pool_icon(request, pool_id: str):
    """The pool's 13x13 PNG icon. 13 pools have none on isaacguru, so they 404."""
    stmt = select(Pool.icon).where(Pool.id == pool_id)
    with Session(request.app.ctx.engine) as session:
        icon = session.scalar(stmt)
    if icon is None:
        raise NotFound(f"No icon for pool {pool_id!r}")
    return raw(icon, content_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
