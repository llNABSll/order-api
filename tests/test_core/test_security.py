import pytest
from unittest.mock import MagicMock
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException

import app.security.security as sec


# ----- _roles_from_claims -----
def test_roles_from_claims():
    payload = {
        "realm_access": {"roles": ["r_realm"]},
        "resource_access": {"client1": {"roles": ["r_client"]}},
        "roles": ["r_top"]
    }

    roles = sec._roles_from_claims(payload)
    assert roles == {"r_realm", "r_client", "r_top"}


# ----- require_user : gateway mode -----
def test_require_user_gateway_mode():
    auth = sec.require_user(
        x_auth_request_user="alice",
        x_auth_request_email="alice@example.com",
        x_auth_request_groups="group1,group2",
        creds=None,
    )

    assert auth.user == "alice"
    assert auth.email == "alice@example.com"
    assert set(auth.roles) == {"group1", "group2"}


# ----- require_user : JWT success -----
def test_require_user_jwt_success(monkeypatch):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    fake_verifier = MagicMock()
    payload = {
        "preferred_username": "bob",
        "email": "bob@example.com",
        "realm_access": {"roles": [sec._ROLE_READ]},
    }
    fake_verifier.decode.return_value = payload

    monkeypatch.setattr(sec, "_get_verifier", lambda: fake_verifier)

    auth = sec.require_user(
        x_auth_request_user=None,
        x_auth_request_email=None,
        x_auth_request_groups=None,
        creds=creds,
    )

    assert auth.user == "bob"
    assert auth.email == "bob@example.com"
    assert sec._ROLE_READ in auth.roles


# ----- require_user : JWT invalide (raise 401) -----
def test_require_user_jwt_invalid(monkeypatch):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="badtoken")
    fake_verifier = MagicMock()
    fake_verifier.decode.side_effect = Exception("invalid")
    monkeypatch.setattr(sec, "_get_verifier", lambda: fake_verifier)

    with pytest.raises(HTTPException) as excinfo:
        sec.require_user(
            x_auth_request_user=None,
            x_auth_request_email=None,
            x_auth_request_groups=None,
            creds=creds,
        )

    assert excinfo.value.status_code == 401


# ----- require_user : aucun credentials -----
def test_require_user_no_credentials():
    with pytest.raises(HTTPException) as excinfo:
        sec.require_user(
            x_auth_request_user=None,
            x_auth_request_email=None,
            x_auth_request_groups=None,
            creds=None,
        )

    assert excinfo.value.status_code == 401


# ----- require_read / require_write -----
def test_require_read_and_write_role_checks():
    # missing read
    auth = sec.AuthContext(user="u", email=None, roles=["other:role"])
    with pytest.raises(HTTPException) as e:
        sec.require_read(auth)
    assert e.value.status_code == 403

    # has read
    auth_r = sec.AuthContext(user="u", email=None, roles=[sec._ROLE_READ])
    assert sec.require_read(auth_r) is auth_r

    # missing write
    auth_w = sec.AuthContext(user="u", email=None, roles=["other:role"])
    with pytest.raises(HTTPException) as e2:
        sec.require_write(auth_w)
    assert e2.value.status_code == 403

    # has write
    auth_w2 = sec.AuthContext(user="u", email=None, roles=[sec._ROLE_WRITE])
    assert sec.require_write(auth_w2) is auth_w2


# ----- _Verifier init -----
def test_verifier_init_missing_config():
    # jwks_url ou issuer absent => RuntimeError
    with pytest.raises(RuntimeError):
        sec._Verifier(jwks_url="", issuer="issuer")
    with pytest.raises(RuntimeError):
        sec._Verifier(jwks_url="https://jwks", issuer="")


# ----- _get_verifier -----
def test_get_verifier_creates_and_reuses(monkeypatch):
    sec._verifier = None
    fake_verifier = MagicMock()
    monkeypatch.setattr(sec, "_Verifier", lambda jwks, iss: fake_verifier)
    monkeypatch.setattr(sec, "settings", MagicMock(
        KEYCLOAK_JWKS_URL="https://jwks", KEYCLOAK_ISSUER="issuer"
    ))

    v1 = sec._get_verifier()
    v2 = sec._get_verifier()
    assert v1 is fake_verifier
    assert v2 is fake_verifier


def test_get_verifier_settings_missing(monkeypatch):
    sec._verifier = None
    fake_settings = MagicMock(KEYCLOAK_JWKS_URL=None, KEYCLOAK_ISSUER=None)
    monkeypatch.setattr(sec, "settings", fake_settings)

    with pytest.raises(RuntimeError):
        sec._get_verifier()


# ----- require_user : JWT invalide avec logs -----
def test_require_user_jwt_invalid_logs(monkeypatch, caplog):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="badtoken")
    fake_verifier = MagicMock()
    fake_verifier.decode.side_effect = Exception("invalid jwt")
    monkeypatch.setattr(sec, "_get_verifier", lambda: fake_verifier)

    with caplog.at_level("WARNING"):
        with pytest.raises(HTTPException) as excinfo:
            sec.require_user(
                x_auth_request_user=None,
                x_auth_request_email=None,
                x_auth_request_groups=None,
                creds=creds,
            )
    assert excinfo.value.status_code == 401
    assert "JWT invalide" in caplog.text
    assert "invalid jwt" in caplog.text or "Traceback" in caplog.text
