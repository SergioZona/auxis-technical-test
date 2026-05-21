from app.infrastructure.adapters.inbound.http.jsend import error, fail, success


def test_jsend_success() -> None:
    res = success({"id": 123})
    assert res == {"status": "success", "data": {"id": 123}}


def test_jsend_fail() -> None:
    res = fail({"field": "Required field"})
    assert res == {"status": "fail", "data": {"field": "Required field"}}


def test_jsend_error_without_code() -> None:
    res = error("An error occurred")
    assert res == {"status": "error", "message": "An error occurred"}


def test_jsend_error_with_code() -> None:
    res = error("An error occurred", code=500)
    assert res == {"status": "error", "message": "An error occurred", "code": 500}
