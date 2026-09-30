from sanic import Sanic
from sanic.worker.loader import AppLoader

from tboi_api.app import create_app

if __name__ == "__main__":
    loader = AppLoader(factory=create_app)
    app = loader.load()
    app.prepare(dev=True)
    Sanic.serve(primary=app, app_loader=loader)
