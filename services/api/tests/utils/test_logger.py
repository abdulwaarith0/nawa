from nawa_api.utils.logger import get_logger


def test_get_logger_returns_a_bound_logger_with_kwargs():
    logger = get_logger(request_id="abc-123")
    assert logger is not None


def test_get_logger_is_idempotent_across_calls():
    first = get_logger()
    second = get_logger()
    assert first is not None and second is not None


def test_get_logger_does_not_raise_when_called_repeatedly():
    for _ in range(3):
        get_logger(component="test").warning("smoke_test_event", detail="value")
