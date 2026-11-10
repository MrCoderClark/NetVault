import pytest

from netvault.security.passwords import hash_password, needs_rehash, verify_password


def test_hash_verify_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "correct horse battery staple") is True


def test_verify_rejects_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password(hashed, "wrong password") is False


def test_hash_outputs_differ_due_to_salt() -> None:
    assert hash_password("same password") != hash_password("same password")


def test_hash_rejects_empty_password() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        hash_password("")


def test_verify_handles_empty_and_bogus_inputs() -> None:
    hashed = hash_password("real password")
    assert verify_password(hashed, "") is False
    assert verify_password("", "anything") is False
    assert verify_password("not even a hash", "real password") is False


def test_needs_rehash_is_false_for_fresh_hash() -> None:
    assert needs_rehash(hash_password("password")) is False
