"""Entry point: python -m gateway"""

import uvicorn

from .config import Settings

if __name__ == "__main__":
    settings = Settings.from_env()
    uvicorn.run("gateway.main:app", host=settings.http_host, port=settings.http_port)
