"""Consultas de catalogo (tablas / columnas) compatibles con Oracle 10g.

Nota: Oracle 10g no soporta la sintaxis "FETCH FIRST n ROWS ONLY" (eso es
12c+), por lo que el limite de filas se aplica del lado del cliente via
Settings.max_rows / fetchmany, igual que en query_runner.
"""

from .config import Settings
from .query_runner import QueryResult, run_internal_query

_LIST_TABLES_SQL = """
SELECT owner, table_name
FROM all_tables
WHERE (:schema IS NULL OR owner = UPPER(:schema))
ORDER BY owner, table_name
"""

_DESCRIBE_TABLE_SQL = """
SELECT owner, column_name, data_type, data_length, data_precision, data_scale, nullable, column_id
FROM all_tab_columns
WHERE table_name = UPPER(:table_name)
  AND (:schema IS NULL OR owner = UPPER(:schema))
ORDER BY owner, column_id
"""


def list_tables(settings: Settings, schema: str | None = None) -> QueryResult:
    return run_internal_query(settings, _LIST_TABLES_SQL, {"schema": schema})


def describe_table(settings: Settings, table_name: str, schema: str | None = None) -> QueryResult:
    return run_internal_query(
        settings, _DESCRIBE_TABLE_SQL, {"table_name": table_name, "schema": schema}
    )
