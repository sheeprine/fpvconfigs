import time

import pytest

from app.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    def test_hash_returns_string(self):
        hashed = get_password_hash("mypassword")
        assert isinstance(hashed, str)

    def test_hash_is_not_plaintext(self):
        hashed = get_password_hash("mypassword")
        assert hashed != "mypassword"

    def test_hash_starts_with_bcrypt_prefix(self):
        hashed = get_password_hash("mypassword")
        assert hashed.startswith("$2b$")

    def test_verify_correct_password_returns_true(self):
        hashed = get_password_hash("correct")
        assert verify_password("correct", hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = get_password_hash("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_hashes_for_same_password(self):
        h1 = get_password_hash("samepassword")
        h2 = get_password_hash("samepassword")
        assert h1 != h2  # bcrypt uses random salt

    def test_verify_empty_password(self):
        hashed = get_password_hash("notempty")
        assert verify_password("", hashed) is False


class TestAccessToken:
    def test_create_returns_string(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_returns_subject(self):
        user_id = "user-abc-123"
        token = create_access_token(user_id)
        result = verify_token(token, TOKEN_TYPE_ACCESS)
        assert result == user_id

    def test_verify_wrong_type_returns_none(self):
        token = create_access_token("user-123")
        assert verify_token(token, TOKEN_TYPE_REFRESH) is None

    def test_verify_invalid_token_returns_none(self):
        assert verify_token("not.a.jwt", TOKEN_TYPE_ACCESS) is None

    def test_verify_empty_string_returns_none(self):
        assert verify_token("", TOKEN_TYPE_ACCESS) is None

    def test_verify_tampered_token_returns_none(self):
        token = create_access_token("user-123")
        tampered = token[:-5] + "AAAAA"
        assert verify_token(tampered, TOKEN_TYPE_ACCESS) is None


class TestRefreshToken:
    def test_create_returns_string(self):
        token = create_refresh_token("user-456")
        assert isinstance(token, str)

    def test_verify_returns_subject(self):
        user_id = "user-xyz"
        token = create_refresh_token(user_id)
        result = verify_token(token, TOKEN_TYPE_REFRESH)
        assert result == user_id

    def test_refresh_token_rejected_as_access_token(self):
        token = create_refresh_token("user-456")
        assert verify_token(token, TOKEN_TYPE_ACCESS) is None

    def test_access_token_rejected_as_refresh_token(self):
        token = create_access_token("user-456")
        assert verify_token(token, TOKEN_TYPE_REFRESH) is None


class TestTokenWithAdditionalClaims:
    def test_token_with_additional_claims(self):
        token = create_access_token("user-111", additional_claims={"role": "editor"})
        result = verify_token(token, TOKEN_TYPE_ACCESS)
        assert result == "user-111"
