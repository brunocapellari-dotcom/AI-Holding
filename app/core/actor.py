from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Annotated, cast

from fastapi import Header, HTTPException
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.core.config import settings

TRUSTED_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
VerifyGoogleToken = Callable[[str, Request, str], Mapping[str, object]]


@dataclass(frozen=True)
class ActorContext:
    name: str
    actor_type: str
    subject: str | None = None
    issuer: str | None = None
    authenticated: bool = False


@dataclass(frozen=True)
class VerifiedGoogleIdentity:
    email: str
    subject: str
    issuer: str


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def _verified_claims(token: str) -> Mapping[str, object]:
    verifier = cast(VerifyGoogleToken, id_token.verify_oauth2_token)
    return verifier(token, Request(), settings.verified_identity_audience)


def _verify_google_identity(token: str) -> VerifiedGoogleIdentity:
    try:
        claims = _verified_claims(token)
    except (GoogleAuthError, ValueError) as exc:
        raise _unauthorized("invalid Google identity token") from exc

    issuer = claims.get("iss")
    email = claims.get("email")
    subject = claims.get("sub")
    email_verified = claims.get("email_verified")

    if not isinstance(issuer, str) or issuer not in TRUSTED_GOOGLE_ISSUERS:
        raise _unauthorized("untrusted identity token issuer")
    if not isinstance(email, str) or not email:
        raise _unauthorized("identity token does not contain an email")
    if email_verified is not True:
        raise _unauthorized("identity token email is not verified")
    if not isinstance(subject, str) or not subject:
        raise _unauthorized("identity token does not contain a subject")

    return VerifiedGoogleIdentity(email=email, subject=subject, issuer=issuer)


def _actor_type_for_email(email: str) -> str:
    if email.endswith(".gserviceaccount.com"):
        return "service-account"
    return "human"


def _local_actor(x_actor: str | None, x_actor_type: str | None) -> ActorContext:
    return ActorContext(
        name=x_actor or "local-user",
        actor_type=x_actor_type or "human",
        authenticated=False,
    )


def get_actor(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_actor: Annotated[str | None, Header(alias="X-Actor")] = None,
    x_actor_type: Annotated[str | None, Header(alias="X-Actor-Type")] = None,
) -> ActorContext:
    if settings.environment in {"development", "test"}:
        return _local_actor(x_actor, x_actor_type)

    if not settings.require_verified_identity:
        raise HTTPException(status_code=503, detail="verified identity is not enabled")

    if not authorization:
        raise _unauthorized("Google identity token is required")

    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("Authorization must use Bearer authentication")

    identity = _verify_google_identity(token.strip())
    return ActorContext(
        name=identity.email,
        actor_type=_actor_type_for_email(identity.email),
        subject=identity.subject,
        issuer=identity.issuer,
        authenticated=True,
    )
