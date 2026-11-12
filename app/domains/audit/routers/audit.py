"""Audit HTTP endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/audit", tags=["Audit Log"])
