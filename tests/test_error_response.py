from __future__ import annotations

from backend.utils.path_utils import error_response


def test_error_response_keeps_frontend_error_field() -> None:
    response = error_response("boom")

    assert response == {"status": "error", "message": "boom", "error": "boom"}
