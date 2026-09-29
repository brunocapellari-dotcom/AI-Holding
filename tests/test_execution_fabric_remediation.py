from app.services.holding import _cloud_build_remediation


def test_cloud_build_remediation_prioritizes_security_findings() -> None:
    category, owner, action, retry_safe = _cloud_build_remediation(
        "secret-scan",
        "Gitleaks",
        "USER_BUILD_STEP",
    )
    assert category == "security-secret"
    assert owner == "security"
    assert "before any rerun" in action
    assert retry_safe is False


def test_cloud_build_remediation_allows_only_bounded_transient_retry() -> None:
    category, owner, action, retry_safe = _cloud_build_remediation(
        None,
        None,
        "INTERNAL_ERROR",
    )
    assert category == "transient-platform"
    assert owner == "platform"
    assert "bounded rerun" in action
    assert retry_safe is True


def test_cloud_build_remediation_does_not_guess_unknown_failures() -> None:
    category, owner, action, retry_safe = _cloud_build_remediation(
        "custom-step",
        "custom-image",
        "USER_BUILD_STEP",
    )
    assert category == "unknown"
    assert owner == "pmo"
    assert "Inspect sanitized" in action
    assert retry_safe is False
