"""Ejecuta consultas SELECT contra Oracle 10g con limites de seguridad y auditoria."""

from dataclasses import dataclass

from .audit_log import get_audit_logger, one_line
from .config import Settings
from .db import get_connection
from .sql_guard import UnsafeSqlError, ensure_read_only


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[tuple]
    truncated: bool


def _execute(settings: Settings, sql: str, params: dict | None = None) -> QueryResult:
    """Ejecuta cualquier SQL ya validado (o de confianza, generado internamente)
    y registra la ejecucion en el log de auditoria."""
    logger = get_audit_logger()
    logged_sql = one_line(sql)

    with get_connection(settings) as conn:
        cursor = conn.cursor()
        # callTimeout esta en milisegundos.
        cursor.callTimeout = settings.query_timeout_seconds * 1000

        try:
            cursor.execute(sql, params or {})
        except Exception as exc:
            logger.info("user=%s status=ERROR error=%s sql=%s", settings.user, exc, logged_sql)
            raise

        if cursor.description is None:
            logger.info("user=%s status=OK rows=0 sql=%s", settings.user, logged_sql)
            return QueryResult(columns=[], rows=[], truncated=False)

        columns = [col[0] for col in cursor.description]
        # Pedimos una fila extra para saber si el resultado quedo truncado.
        rows = cursor.fetchmany(settings.max_rows + 1)
        truncated = len(rows) > settings.max_rows
        if truncated:
            rows = rows[: settings.max_rows]

        logger.info(
            "user=%s status=OK rows=%d truncated=%s sql=%s",
            settings.user, len(rows), truncated, logged_sql,
        )
        return QueryResult(columns=columns, rows=[tuple(r) for r in rows], truncated=truncated)


def run_query(settings: Settings, sql: str) -> QueryResult:
    """Punto de entrada para SQL arbitrario (CLI / tool MCP run_query).
    Aplica el guard de solo-lectura antes de ejecutar."""
    if settings.read_only:
        try:
            ensure_read_only(sql)
        except UnsafeSqlError as exc:
            get_audit_logger().info(
                "user=%s status=REJECTED error=%s sql=%s",
                settings.user, exc, one_line(sql),
            )
            raise
    return _execute(settings, sql)


def run_internal_query(settings: Settings, sql: str, params: dict | None = None) -> QueryResult:
    """Punto de entrada para SQL fijo generado por esta misma utilidad
    (ej. consultas de catalogo en schema_inspector.py). No pasa por el
    guard de solo-lectura porque el texto SQL no viene del usuario final,
    solo sus parametros (que van como bind variables, no concatenados)."""
    return _execute(settings, sql, params)
