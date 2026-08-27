---
name: oracle10g-query
description: Ejecuta consultas SELECT de solo lectura contra la base de datos Oracle 10g de este proyecto (o revisa la estructura de sus tablas) directamente desde la terminal. Usar cuando el usuario pida consultar, verificar, revisar o explorar datos/tablas de la base de datos Oracle, cuando pida "correr una query", o cuando se necesite confirmar el valor real de algo en la BD antes de responder.
---

# Consultas a Oracle 10g (solo lectura)

Esta skill envuelve el CLI de este repo (`scripts/query.py`) para consultar la
base de datos Oracle 10g del proyecto desde la terminal, sin necesidad de un
MCP client. Usa el mismo nucleo de conexion/seguridad que el servidor MCP
(`src/mcp_server.py`).

## Regla no negociable: SOLO LECTURA

Esta base es un sistema legacy en produccion. La utilidad **solo permite
sentencias `SELECT` (o `WITH ... SELECT`)**. Cualquier `INSERT`, `UPDATE`,
`DELETE`, `MERGE`, DDL (`CREATE`/`ALTER`/`DROP`/`TRUNCATE`), `GRANT`/`REVOKE`,
bloques PL/SQL o multiples sentencias separadas por `;` son rechazados antes
de tocar la base (ver `src/sql_guard.py`). No intentes rodear esta
restriccion (por ejemplo con `EXECUTE IMMEDIATE` dentro de un SELECT, DB
links a otra sesion con permisos de escritura, etc.) — si el usuario
necesita escribir datos, dile que esta utilidad no lo soporta y que se
requiere un cambio explicito de alcance.

## Requisito previo

Debe existir un archivo `.env` en la raiz del repo con las credenciales
(ver `.env.example`). Si no existe o falta una variable, el CLI lo reporta
claramente — no adivines valores de conexion.

## Como ejecutar una consulta

Desde la raiz del repo, usando el interprete del entorno virtual del
proyecto:

```
.venv\Scripts\python scripts\query.py "SELECT columnas FROM tabla WHERE ..."
```

Salida en JSON (mas facil de parsear para ti):

```
.venv\Scripts\python scripts\query.py "SELECT ..." --format json
```

Consulta desde un archivo `.sql` (util si la consulta es larga o multilinea):

```
.venv\Scripts\python scripts\query.py --file ruta\a\consulta.sql --format json
```

## Antes de escribir un SELECT contra una tabla que no conoces

1. Ver que tablas existen (opcionalmente filtrando por owner/schema):
   ```
   .venv\Scripts\python scripts\query.py "SELECT owner, table_name FROM all_tables WHERE owner = 'ALGUN_SCHEMA' ORDER BY table_name" --format json
   ```
2. Ver las columnas de una tabla puntual antes de asumir su estructura:
   ```
   .venv\Scripts\python scripts\query.py "SELECT column_name, data_type, data_length, nullable FROM all_tab_columns WHERE table_name = 'ALGUNA_TABLA' ORDER BY column_id" --format json
   ```

No inventes nombres de columnas: si una consulta falla con
`ORA-00904: invalid identifier` u similar, describe la tabla primero.

## Particularidades de Oracle 10g a tener en cuenta al escribir SQL

- No existe `FETCH FIRST n ROWS ONLY` ni `OFFSET` (sintaxis de 12c+). Para
  limitar filas usa `ROWNUM` en una subconsulta:
  ```sql
  SELECT * FROM (
    SELECT col1, col2 FROM tabla ORDER BY col1
  ) WHERE ROWNUM <= 20
  ```
- No hay soporte de funciones analiticas/JSON modernas que dependan de
  versiones posteriores; si algo falla por sintaxis, asume que es una
  limitacion de 10g antes de asumir un typo.
- El CLI ya limita el numero de filas devueltas segun `MAX_ROWS` del
  `.env` y aplica un timeout (`QUERY_TIMEOUT_SECONDS`); si el resultado
  viene con `truncated: true`, dile al usuario que hay mas filas de las
  mostradas y ofrece acotar la consulta (WHERE/ROWNUM) en vez de asumir que
  es todo el resultado.

## Interpretando errores

- `[RECHAZADO] ...` (exit code 2): la consulta no paso el guard de solo
  lectura. No reintentes reformulando para evadirlo; explica la
  restriccion al usuario.
- `[ERROR] Configuracion invalida: ...`: falta o esta mal el `.env`. Pide
  al usuario que lo revise, no lo edites tu mismo con datos inventados.
- `[ERROR] Fallo al ejecutar la consulta: ...`: normalmente un error de
  Oracle (ORA-xxxxx). Lee el mensaje, ajusta la consulta (nombre de
  tabla/columna, sintaxis 10g) y reintenta una vez; si persiste, muestra
  el error tal cual al usuario en vez de especular.

## Auditoria

Toda consulta ejecutada (exitosa o no) queda registrada en
`logs/query_audit.log` con usuario, SQL y resultado. No hace falta hacer
nada especial para esto, es automatico.
