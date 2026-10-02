"""Catalog: HTTP endpoints; register implemented routes here."""
from fastapi import APIRouter

router = APIRouter(prefix="/catalog", tags=["catalog"])
