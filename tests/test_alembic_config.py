from alembic.config import Config

from app.db.alembic_config import escape_config_parser_value


def test_percent_encoded_database_url_round_trips_through_alembic_config():
    database_url = (
        "postgresql+psycopg://holding_app:p%40ss%23word%25value@10.42.0.3:5432/holding"
    )
    config = Config()

    config.set_main_option(
        "sqlalchemy.url",
        escape_config_parser_value(database_url),
    )

    assert config.get_main_option("sqlalchemy.url") == database_url


def test_plain_database_url_is_unchanged():
    database_url = "postgresql+psycopg://holding:holding@localhost:5432/holding_test"

    assert escape_config_parser_value(database_url) == database_url
