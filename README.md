# homemade-mcp-oracle-database-10g-claude

Utilidad de solo lectura para consultar una base de datos **Oracle Database
10g** desde un servidor MCP y/o directamente desde la terminal via una skill
de Claude Code. Ver el requerimiento original en
[`requeriments.txt`](requeriments.txt).

## Por que existe esto

Oracle 10g quedo fuera de soporte extendido hace mas de una decada. Los
drivers modernos de Oracle (`python-oracledb`, `node-oracledb`) usan por
defecto un modo "thin" que solo habla el protocolo de red de Oracle 12c en
adelante. Para hablar con un 10g hace falta forzar el **modo "thick"**,
apoyandose en un Oracle Instant Client instalado localmente. La mayoria de
los MCP de Oracle genericos no exponen esa opcion, de ahi esta utilidad a
medida.

Confirmado en este proyecto: un Oracle Instant Client 19.x en modo thick
**si logra conectar** contra un Oracle Database 10g Release 10.2.0.3.0 (no
hizo falta bajar a Instant Client 11.2 como se anticipaba).

## Arquitectura

```
src/
  config.py           Carga y valida .env (conexion, Instant Client, politica)
  db.py                Conexion Oracle en modo thick (oracledb.init_oracle_client)
  sql_guard.py         Guard de solo-lectura: solo permite SELECT / WITH
  audit_log.py         Logging de auditoria (logs/query_audit.log)
  query_runner.py      Ejecuta SQL con limite de filas (MAX_ROWS), timeout y auditoria
  schema_inspector.py  Consultas de catalogo (list_tables / describe_table), SQL 10g-safe
  mcp_server.py        Servidor MCP (tools: run_query_tool, list_tables, describe_table)

scripts/
  install.py           Instalador automatico (venv, deps, .env, mcp-config.json, registro en Claude Code)
  test_connection.py   Prueba minima de conectividad (Fase 0)
  query.py             CLI de consultas (Fase 1) usado tambien por la skill

install.sh / install.bat   Wrappers de un solo paso que llaman a scripts/install.py

.claude/skills/oracle10g-query/SKILL.md   Skill de Claude Code (usa scripts/query.py)
```

Tanto el CLI como el servidor MCP reutilizan el mismo nucleo
(`config` -> `db` -> `sql_guard`/`query_runner`), asi que la politica de
seguridad y los limites se aplican una sola vez, en un solo lugar.

## Modelo de seguridad (defensa en profundidad)

1. **A nivel de base de datos**: el usuario Oracle configurado ya tiene
   permisos de solo lectura otorgados por el DBA. Esta es la barrera
   principal y real.
2. **A nivel de software** (`src/sql_guard.py`): antes de mandar cualquier
   SQL "libre" (el que llega por `run_query`/`run_query_tool`) se valida
   que sea una unica sentencia `SELECT` o `WITH ... SELECT`. Se rechaza
   cualquier `INSERT/UPDATE/DELETE/MERGE`, DDL, `GRANT/REVOKE`,
   PL/SQL (`BEGIN`, `EXEC`, ...) o sentencias apiladas con `;`.
   Las consultas de catalogo (`list_tables`/`describe_table`) no pasan por
   este guard porque su SQL es fijo y escrito por esta misma utilidad; solo
   sus parametros (schema/table_name) van como bind variables.
3. **Limites de ejecucion**: `MAX_ROWS` limita filas devueltas (via
   `fetchmany`, el resultado indica `truncated: true` si aplico) y
   `QUERY_TIMEOUT_SECONDS` corta la consulta si se cuelga (`cursor.callTimeout`).
4. **Auditoria**: toda ejecucion (exitosa, con error de Oracle, o
   rechazada por el guard) queda registrada en `logs/query_audit.log` con
   usuario, SQL y resultado.

## Instalacion

### Automatica (recomendado)

Justo despues de clonar el repo, corre el instalador para tu sistema:

```
# Linux/macOS
./install.sh

# Windows
install.bat
```

(equivalente en cualquier SO: `python scripts/install.py`)

Esto hace todo el setup sin pasos manuales:

1. Crea el entorno virtual en `.venv` (si no existe).
2. Instala las dependencias de `requirements.txt` dentro de ese venv.
3. Copia `.env.example` a `.env` si `.env` todavia no existe (las
   credenciales reales las tenes que llenar vos a mano, eso nunca se
   automatiza).
4. Genera `mcp-config.json` (gitignored) con las rutas absolutas ya
   resueltas **para esta maquina** — al python del venv y a
   `src/mcp_server.py` — listo para pegar en la config de un cliente MCP
   como Claude Desktop.
5. Si el CLI `claude` esta instalado, registra el servidor MCP
   automaticamente con `claude mcp add` (scope `user`), sin que tengas que
   armar el comando a mano.

Es seguro volver a correrlo: no pisa un `.env` existente ni duplica el
registro en Claude Code, salvo que le pases `--force`. Usa `--no-register`
si no queres tocar la config de Claude Code.

Al final falta solo un paso manual, imposible de automatizar: editar `.env`
con tus datos reales (ver comentarios en `.env.example`): host/puerto/
service_name o SID, usuario y password del usuario de solo lectura, y la
ruta de tu Oracle Instant Client (`ORACLE_INSTANT_CLIENT_DIR`). **Nunca
subas `.env` a un repositorio.**

### Manual

Si preferis armar el entorno vos mismo en vez de usar el instalador:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
```

(en Linux/macOS: `.venv/bin/python -m pip install -r requirements.txt` y
`cp .env.example .env`)

Edita `.env` con tus datos reales igual que en la instalacion automatica.

## Uso

### 1. Probar conectividad

```
.venv\Scripts\python scripts\test_connection.py
```

### 2. CLI de consultas

```
.venv\Scripts\python scripts\query.py "SELECT * FROM alguna_tabla WHERE ROWNUM <= 10" --format json
.venv\Scripts\python scripts\query.py --file consulta.sql --format table
```

### 3. Servidor MCP

Correrlo manualmente (stdio), invocando el archivo directamente (no con
`-m`, ver nota abajo):

```
.venv\Scripts\python src\mcp_server.py
```

Si corriste el [instalador automatico](#automatica-recomendado), esto ya
esta hecho: el registro en Claude Code se hizo solo, y el archivo
`mcp-config.json` (gitignored) ya tiene las rutas de tu maquina resueltas
para pegarlo en otro cliente MCP (Claude Desktop, etc.).

Para registrarlo a mano en Claude Code:

```
claude mcp add oracle10g -s user -- "<ruta>\.venv\Scripts\python.exe" "<ruta>\src\mcp_server.py"
```

o para otro cliente MCP, ver [`mcp-config.example.json`](mcp-config.example.json)
como plantilla — ajusta las rutas a tu maquina y agrega ese bloque a la
config de `mcpServers` del cliente (o copia directo el `mcp-config.json` que
genera el instalador).

**Nota:** el comando usa la ruta absoluta a `src\mcp_server.py` en vez de
`python -m src.mcp_server`. Un cliente MCP lanza este proceso con un `cwd`
que no controlas (y el formato estandar de `mcpServers` no soporta una
clave `cwd`), asi que `-m src.mcp_server` puede fallar con
`ModuleNotFoundError: No module named 'src'` si ese cwd no es la raiz del
repo. `mcp_server.py` se agrega a si mismo al `sys.path` usando su propia
ubicacion (`__file__`, siempre absoluta) antes de importar el resto del
paquete, igual que hacen `scripts/*.py`, para no depender del cwd.

Tools expuestos:
- `run_query_tool(sql)` — ejecuta un SELECT (guard de solo-lectura aplica).
- `list_tables(schema?)` — lista tablas del catalogo (`all_tables`).
- `describe_table(table_name, schema?)` — columnas de una tabla (`all_tab_columns`).

### 4. Skill de Claude Code

Ver [`.claude/skills/oracle10g-query/SKILL.md`](.claude/skills/oracle10g-query/SKILL.md).
Se activa cuando le pides a Claude Code consultar o verificar datos de esta
base; internamente usa el mismo `scripts/query.py`.

## Particularidad de Oracle 10g a tener en cuenta

Oracle 10g no soporta `FETCH FIRST n ROWS ONLY` / `OFFSET` (sintaxis 12c+).
Para limitar filas en una consulta usa `ROWNUM`:

```sql
SELECT * FROM (
  SELECT col1, col2 FROM tabla ORDER BY col1
) WHERE ROWNUM <= 20
```


