"""Servidor MCP de solo lectura para Oracle 10g.

Expone 3 tools:
  - run_query(sql): ejecuta un SELECT arbitrario (validado por sql_guard).
  - list_tables(schema opcional): lista tablas visibles en el catalogo.
  - describe_table(table_name, schema opcional): columnas de una tabla.

Se apoya en el mismo nucleo (config/db/query_runner/schema_inspector) que
usa el CLI en scripts/query.py, para no duplicar logica de conexion,
limites ni auditoria.

Uso (stdio, para registrar en un cliente MCP como Claude Desktop/Code):
    python ruta\completa\a\src\mcp_server.py

Se ejecuta como script (no como "python -m src.mcp_server") a proposito:
un cliente MCP lanza este proceso con un cwd arbitrario (no siempre la raiz
del repo), y "-m src.mcp_server" solo resuelve el paquete "src" si ese cwd
(o PYTHONPATH) lo contiene. Para no depender de eso, este archivo agrega la
raiz del proyecto a sys.path usando su propia ubicacion (__file__, que es
absoluta) antes de importar el resto del paquete, igual que scripts/*.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.mcpserver import MCPServer

from src.config import Settings, load_settings
from src.query_runner import QueryResult, run_query
from src.schema_inspector import describe_table as _describe_table
from src.schema_inspector import list_tables as _list_tables

server = MCPServer(
    "oracle10g",
    instructions=(
        "Herramientas de SOLO LECTURA contra una base Oracle Database 10g. "
        "Nunca intentes generar INSERT/UPDATE/DELETE/DDL: seran rechazados. "
        "Usa list_tables para descubrir tablas, describe_table para ver sus "
        "columnas antes de escribir un SELECT, y run_query para ejecutarlo."
    ),
)

_settings: Settings | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def _to_dict(result: QueryResult) -> dict:
    return {
        "columns": result.columns,
        "rows": [list(row) for row in result.rows],
        "row_count": len(result.rows),
        "truncated": result.truncated,
    }


@server.tool()
def run_query_tool(sql: str) -> dict:
    """Ejecuta una sentencia SELECT (o WITH ... SELECT) de solo lectura contra
    Oracle 10g y devuelve columnas y filas. Cualquier otra sentencia es
    rechazada (error). El resultado se trunca a MAX_ROWS filas."""
    settings = _get_settings()
    result = run_query(settings, sql)
    return _to_dict(result)


@server.tool()
def list_tables(schema: str | None = None) -> dict:
    """Lista tablas del catalogo (all_tables), opcionalmente filtradas por
    schema/owner. Si `schema` se omite, lista tablas de todos los owners
    visibles (puede truncarse a MAX_ROWS)."""
    settings = _get_settings()
    result = _list_tables(settings, schema)
    return _to_dict(result)


@server.tool()
def describe_table(table_name: str, schema: str | None = None) -> dict:
    """Describe las columnas de una tabla (owner, nombre, tipo, longitud,
    precision, escala, nullable), en orden de columna. Si no se indica
    `schema` y el nombre de tabla existe en varios owners, devuelve las
    columnas de todos ellos (revisa la columna OWNER del resultado)."""
    settings = _get_settings()
    result = _describe_table(settings, table_name, schema)
    return _to_dict(result)


if __name__ == "__main__":
    server.run()
