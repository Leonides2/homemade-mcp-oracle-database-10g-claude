"""Validador de solo-lectura: segunda capa de seguridad ademas de los
permisos de solo lectura ya otorgados al usuario de Oracle.

Esto NO reemplaza los grants de la base de datos, es una barrera adicional
para que la utilidad nunca intente mandar algo distinto de un SELECT.
"""

import re

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")

# Palabras que, si aparecen como arranque de sentencia, jamas son de solo lectura.
_WRITE_KEYWORDS = (
    "INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL", "BEGIN",
    "DECLARE", "REPLACE", "COMMIT", "ROLLBACK", "LOCK",
)


class UnsafeSqlError(ValueError):
    """La sentencia SQL no paso la validacion de solo lectura."""


def _strip_comments(sql: str) -> str:
    sql = _BLOCK_COMMENT.sub(" ", sql)
    sql = _LINE_COMMENT.sub(" ", sql)
    return sql


def ensure_read_only(sql: str) -> None:
    """Lanza UnsafeSqlError si `sql` no es una unica sentencia SELECT/WITH."""
    if not sql or not sql.strip():
        raise UnsafeSqlError("La consulta esta vacia.")

    cleaned = _strip_comments(sql).strip()

    # Permitir un unico ';' final, pero no sentencias apiladas.
    body = cleaned[:-1] if cleaned.endswith(";") else cleaned
    if ";" in body:
        raise UnsafeSqlError(
            "No se permiten multiples sentencias separadas por ';'."
        )

    first_word_match = re.match(r"[A-Za-z]+", body.strip())
    first_word = first_word_match.group(0).upper() if first_word_match else ""

    if first_word in _WRITE_KEYWORDS:
        raise UnsafeSqlError(
            f"Sentencia '{first_word}' no permitida: esta utilidad es de solo lectura."
        )

    if first_word not in ("SELECT", "WITH"):
        raise UnsafeSqlError(
            "Solo se permiten sentencias SELECT (o WITH ... SELECT)."
        )
