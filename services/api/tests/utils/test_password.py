from nawa_api.utils.password import hash_password, verify_password


def test_hash_password_produces_verifiable_hash():
    hashed = hash_password("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("s3cret-pass")
    assert verify_password("wrong-pass", hashed) is False


def test_hash_password_is_salted_unique_per_call():
    assert hash_password("same") != hash_password("same")


def test_verify_password_returns_false_on_malformed_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False
