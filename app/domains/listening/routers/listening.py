"""Listening HTTP endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/listening", tags=["listening"])
