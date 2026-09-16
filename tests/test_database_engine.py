from app.core.config import Settings
from app.db.engine import build_database_engine


def test_password_mode_preserves_local_and_rollback_path() -> None:
    settings = Settings(
        _env_file=None,
        environment="test",
        database_auth_mode="password",
        database_url="sqlite+pysqlite:///:memory:",
    )

    engine, connector = build_database_engine(settings)

    assert connector is None
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT 1").scalar_one() == 1


def test_cloud_sql_iam_mode_uses_psycopg_private_ip_and_lazy_refresh() -> None:
    created: list[object] = []

    class FakeConnector:
        def __init__(self, **kwargs):
            self.init_kwargs = kwargs
            self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
            self.closed = False
            created.append(self)

        def connect(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return object()

        def close(self) -> None:
            self.closed = True

    settings = Settings(
        _env_file=None,
        environment="production",
        database_auth_mode="cloud_sql_iam",
        cloud_sql_instance_connection_name="project:region:instance",
        cloud_sql_iam_user="holding-control-plane@project.iam",
        cloud_sql_database="holding",
        cloud_sql_ip_type="private",
    )

    engine, connector = build_database_engine(settings, connector_factory=FakeConnector)

    assert connector is created[0]
    assert connector.init_kwargs == {"refresh_strategy": "lazy"}
    assert engine.url.drivername == "postgresql+psycopg"

    # Exercise the SQLAlchemy creator directly without needing a real Cloud SQL socket.
    engine.pool._creator()  # noqa: SLF001
    args, kwargs = connector.calls[0]
    assert args == ("project:region:instance", "psycopg")
    assert kwargs == {
        "user": "holding-control-plane@project.iam",
        "db": "holding",
        "ip_type": "private",
        "enable_iam_auth": True,
    }


def test_cloud_sql_iam_mode_fails_closed_when_required_identity_is_missing() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        database_auth_mode="cloud_sql_iam",
        cloud_sql_instance_connection_name="project:region:instance",
        cloud_sql_iam_user=None,
    )

    try:
        build_database_engine(settings)
    except RuntimeError as exc:
        assert "CLOUD_SQL_IAM_USER" in str(exc)
    else:
        raise AssertionError("IAM engine must fail closed without a database IAM user")
