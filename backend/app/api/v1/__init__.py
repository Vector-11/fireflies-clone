"""Version 1 of the API.

Every router is mounted here so ``main.py`` includes exactly one thing, and
adding an endpoint group never touches the application factory.
"""

from fastapi import APIRouter

from app.api.v1 import action_items, meetings, search, summaries, transcript, workspace

api_router = APIRouter()
api_router.include_router(workspace.router)
api_router.include_router(meetings.router)
api_router.include_router(transcript.router)
api_router.include_router(summaries.router)
api_router.include_router(action_items.router)
api_router.include_router(search.router)
