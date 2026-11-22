"""The FastAPI app: joins the routers and serves the website.

Run it with: uvicorn api:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import auth
import games
import watchlist

app = FastAPI()
app.include_router(games.router)
app.include_router(auth.router)
app.include_router(watchlist.router)

# The website (static/index.html and friends). Mounted last so the API routes above win.
app.mount("/", StaticFiles(directory="static", html=True), name="site")
