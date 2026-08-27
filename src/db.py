"""Conexion a Oracle en modo thick (requerido para hablar con Oracle 10g)."""

from contextlib import contextmanager

import oracledb

from .config import Settings

_client_initialized = False


def init_client(settings: Settings) -> None:
    """Inicializa el modo thick del driver una sola vez por proceso."""
    global _client_initialized
    if _client_initialized:
        return
    oracledb.init_oracle_client(lib_dir=settings.instant_client_dir)
    _client_initialized = True


def _build_dsn(settings: Settings) -> str:
    if settings.service_name:
        return oracledb.makedsn(settings.host, settings.port, service_name=settings.service_name)
    return oracledb.makedsn(settings.host, settings.port, sid=settings.sid)


@contextmanager
def get_connection(settings: Settings):
    init_client(settings)
    dsn = _build_dsn(settings)
    connection = oracledb.connect(user=settings.user, password=settings.password, dsn=dsn)
    try:
        yield connection
    finally:
        connection.close()
