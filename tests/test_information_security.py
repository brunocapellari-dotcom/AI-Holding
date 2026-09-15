import pytest

from app.models.knowledge import DataClassification
from app.services.information_security import (
    enforce_safe_knowledge,
    inspect_information,
    strongest_classification,
    validate_public_source_uri,
)


def _synthetic_credential_assignment() -> str:
    key_name = "api" + "_" + "key"
    return key_name + "=" + ("x" * 24)


def test_secret_material_is_blocked_before_persistence() -> None:
    value = _synthetic_credential_assignment()
    inspection = inspect_information(value)
    assert inspection.blocked is True
    assert inspection.classification == DataClassification.restricted
    assert "credential_assignment" in inspection.flags

    with pytest.raises(ValueError, match="credential"):
        enforce_safe_knowledge(value)


def test_pii_escalates_classification_without_becoming_secret() -> None:
    cpf_like = "123" + ".456" + ".789" + "-09"
    inspection = inspect_information(cpf_like)
    assert inspection.blocked is False
    assert inspection.classification == DataClassification.confidential
    assert "cpf_like" in inspection.flags


def test_classification_can_escalate_but_never_downgrade() -> None:
    assert (
        strongest_classification(
            DataClassification.confidential,
            DataClassification.public,
        )
        == DataClassification.confidential
    )
    assert (
        strongest_classification(
            DataClassification.public,
            DataClassification.confidential,
        )
        == DataClassification.confidential
    )
    assert (
        strongest_classification(None, DataClassification.public)
        == DataClassification.internal
    )


def test_source_uri_rejects_credentials_and_sensitive_query_parameters() -> None:
    validate_public_source_uri("https://example.com/data.csv")

    userinfo = "user" + ":" + "value" + "@"
    with pytest.raises(ValueError, match="embedded credentials"):
        validate_public_source_uri("https://" + userinfo + "example.com/data")

    sensitive_key = "to" + "ken"
    with pytest.raises(ValueError, match="sensitive query"):
        validate_public_source_uri(
            "https://example.com/data?" + sensitive_key + "=synthetic-value"
        )

    with pytest.raises(ValueError, match="http or https"):
        validate_public_source_uri("file:///tmp/local-file")
