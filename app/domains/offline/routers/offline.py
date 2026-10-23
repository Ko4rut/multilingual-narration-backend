"""Offline HTTP endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/offline", tags=["offline"])
