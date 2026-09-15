from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_secret_scanning_gate_is_fail_closed_and_immutably_pinned():
    workflow = (ROOT / ".github/workflows/security-gates.yml").read_text(encoding="utf-8")

    assert "secret-scan:" in workflow
    assert "gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e" in workflow
    assert "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803" in workflow
    assert "continue-on-error" not in workflow
    assert 'GITLEAKS_ENABLE_COMMENTS: "false"' in workflow
    assert 'GITLEAKS_ENABLE_UPLOAD_ARTIFACT: "false"' in workflow
