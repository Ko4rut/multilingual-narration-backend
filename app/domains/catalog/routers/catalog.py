"""Catalog HTTP endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/catalog", tags=["catalog"])
