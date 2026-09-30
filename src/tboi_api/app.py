from pathlib import Path
from sanic import Sanic

from tboi_api.db_models import create_sqlite_engine
from tboi_api.api.items import bp as items_bp
from tboi_api.api.pools import bp as pools_bp

DB_PATH = Path("data/isaacguru.db")

def create_app() -> Sanic:
    app = Sanic("tboi_api")

    app.blueprint(items_bp)
    app.blueprint(pools_bp)

    @app.before_server_start
    async def setup_db(app):
        app.ctx.engine = create_sqlite_engine(str(DB_PATH))

    @app.after_server_stop
    async def teardown_db(app):
        app.ctx.engine.dispose()

    return app
