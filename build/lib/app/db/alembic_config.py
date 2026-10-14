def escape_config_parser_value(value: str) -> str:
    """Escape percent signs before storing runtime values in ConfigParser."""
    return value.replace("%", "%%")
