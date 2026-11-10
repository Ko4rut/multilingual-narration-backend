from app.domains.poi.routers.poi import content_router


def test_content_and_audio_delete_routes_are_not_exposed() -> None:
    delete_paths = {
        route.path
        for route in content_router.routes
        if "DELETE" in getattr(route, "methods", set())
    }

    assert "/admin/poi-contents/{content_id}" not in delete_paths
    assert "/admin/poi-contents/{content_id}/audio" not in delete_paths


def test_content_version_clone_route_is_not_exposed() -> None:
    paths = {route.path for route in content_router.routes}

    assert "/admin/poi-contents/{content_id}/versions" not in paths


def test_review_replaces_separate_approve_and_reject_routes() -> None:
    paths = {route.path for route in content_router.routes}

    assert "/admin/poi-contents/{content_id}/review" in paths
    assert "/admin/poi-contents/{content_id}/approve" not in paths
    assert "/admin/poi-contents/{content_id}/reject" not in paths
