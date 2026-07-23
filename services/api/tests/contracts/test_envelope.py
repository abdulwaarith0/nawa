from nawa_api.utils.envelope import created, fail, ok


def test_ok_wraps_data_with_200():
    assert ok({"a": 1}) == {"code": 200, "message": "OK", "data": {"a": 1}}


def test_ok_allows_none_data():
    assert ok(None) == {"code": 200, "message": "OK", "data": None}


def test_ok_wraps_list_data():
    assert ok([1, 2, 3]) == {"code": 200, "message": "OK", "data": [1, 2, 3]}


def test_created_uses_201():
    assert created({"id": "x"}) == {"code": 201, "message": "Created", "data": {"id": "x"}}


def test_fail_sets_code_message_and_null_data():
    assert fail(404, "Not found") == {"code": 404, "message": "Not found", "data": None}
