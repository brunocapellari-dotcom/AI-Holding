import pytest
from fastapi import HTTPException

from app.core import actor
from app.core.actor import VerifiedGoogleIdentity
from app.core.config import settings


def test_production_actor_uses_verified_google_identity(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "require_verified_identity", True)
    monkeypatch.setattr(
        actor,
        "_verify_google_identity",
        lambda token: VerifiedGoogleIdentity(
            email="pmo@holding.example.gserviceaccount.com",
            subject="123456789",
            issuer="https://accounts.google.com",
        ),
    )

    context = actor.get_actor(
        authorization="Bearer signed-google-token",
        x_actor="forged-user",
        x_actor_type="human",
    )

    assert context.name == "pmo@holding.example.gserviceaccount.com"
    assert context.actor_type == "service-account"
    assert context.subject == "123456789"
    assert context.authenticated is True


def test_google_verifier_receives_pinned_audience(monkeypatch):
    captured: dict[str, str] = {}

    def fake_verify(token, request, audience):
        captured["token"] = token
        captured["audience"] = audience
        return {
            "iss": "https://accounts.google.com",
            "email": "pmo@example.com",
            "email_verified": True,
            "sub": "123",
        }

    monkeypatch.setattr(settings, "verified_identity_audience", "holding-control-plane")
    monkeypatch.setattr(actor.id_token, "verify_oauth2_token", fake_verify)

    claims = actor._verified_claims("signed-token")

    assert claims["sub"] == "123"
    assert captured == {
        "token": "signed-token",
        "audience": "holding-control-plane",
    }


def test_production_actor_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "require_verified_identity", True)

    with pytest.raises(HTTPException) as exc_info:
        actor.get_actor(authorization=None, x_actor="forged-user", x_actor_type="agent")

    assert exc_info.value.status_code == 401


def test_production_actor_rejects_non_bearer_token(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "require_verified_identity", True)

    with pytest.raises(HTTPException) as exc_info:
        actor.get_actor(authorization="Basic abc", x_actor=None, x_actor_type=None)

    assert exc_info.value.status_code == 401


def test_production_identity_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "require_verified_identity", False)

    with pytest.raises(HTTPException) as exc_info:
        actor.get_actor(authorization="Bearer ignored", x_actor=None, x_actor_type=None)

    assert exc_info.value.status_code == 503


def test_local_actor_headers_are_advisory_only_outside_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "require_verified_identity", True)

    context = actor.get_actor(
        authorization=None,
        x_actor="test-agent",
        x_actor_type="agent",
    )

    assert context.name == "test-agent"
    assert context.actor_type == "agent"
    assert context.authenticated is False


def test_actor_type_detects_human_identity():
    assert actor._actor_type_for_email("user@example.com") == "human"


@pytest.mark.parametrize(
    ("claims", "detail"),
    [
        (
            {
                "iss": "https://evil.example",
                "email": "user@example.com",
                "email_verified": True,
                "sub": "123",
            },
            "untrusted identity token issuer",
        ),
        (
            {
                "iss": "https://accounts.google.com",
                "email_verified": True,
                "sub": "123",
            },
            "identity token does not contain an email",
        ),
        (
            {
                "iss": "https://accounts.google.com",
                "email": "user@example.com",
                "email_verified": False,
                "sub": "123",
            },
            "identity token email is not verified",
        ),
        (
            {
                "iss": "https://accounts.google.com",
                "email": "user@example.com",
                "email_verified": True,
            },
            "identity token does not contain a subject",
        ),
    ],
)
def test_verified_identity_rejects_invalid_claims(monkeypatch, claims, detail):
    monkeypatch.setattr(actor, "_verified_claims", lambda token: claims)

    with pytest.raises(HTTPException) as exc_info:
        actor._verify_google_identity("signed-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == detail


def test_verified_identity_rejects_invalid_signature(monkeypatch):
    def invalid_claims(token):
        raise ValueError("invalid signature")

    monkeypatch.setattr(actor, "_verified_claims", invalid_claims)

    with pytest.raises(HTTPException) as exc_info:
        actor._verify_google_identity("bad-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "invalid Google identity token"
