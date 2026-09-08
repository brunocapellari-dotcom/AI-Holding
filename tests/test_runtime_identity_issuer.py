from app.core import actor


def test_google_identity_issuer_is_canonicalized(monkeypatch):
    monkeypatch.setattr(
        actor,
        "_verified_claims",
        lambda token: {
            "iss": "accounts.google.com",
            "email": "holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
            "email_verified": True,
            "sub": "868946857614000000001",
        },
    )

    identity = actor._verify_google_identity("signed-token")

    assert identity.issuer == actor.CANONICAL_GOOGLE_ISSUER
