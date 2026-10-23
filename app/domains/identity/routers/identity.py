"""Identity HTTP endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/identity", tags=["identity"])
