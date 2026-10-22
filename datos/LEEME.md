# Carpeta `datos/`: cómo cargar series reales

Las rutinas de `codigo/` leen archivos CSV de esta carpeta. Mientras falten, usan datos
sintéticos de demostración (`--demo`). **Subí sólo series públicas.** No subas datos por
entidad, información interna ni nada de liquidez que no esté publicado.

## Qué hay y qué falta (2026-10)

| Archivo | Estado | Formato |
|---|---|---|
| `catalogo_monetarias.csv` | cargado (1610 series de la API v4.0) | catálogo de la API |
| `emae_mensual.csv` | cargado (INDEC, 2004-01 a 2026-08) | `mes,emae_orig,emae_se`; `mes` en `d/m/aaaa` |
| `ipc_mensual.csv` | cargado (INDEC, base dic-16 = 100, 2016-12 a 2026-09) | `mes,ipc_ng`; `mes` tipo `dic-16`, `sept-26` |
| `bcra_<id>_daily.csv` + `metadata_<id>.json` | **faltan**: se bajan dentro del BCRA (pasos 1–7) | `fecha,valor` (ISO) |

Los cargadores leen EMAE e IPC tal como están (meses en español, `sept`/`set`, espacios
finales); no hace falta convertirlos. Las series diarias usan `fecha,valor` con
`fecha` `AAAA-MM-DD` y punto decimal; `descargar_bcra.py` ya las genera así.

## Paso a paso en la PC del BCRA (sin git)

**1. Python y dependencias.** Python 3.10 o superior. En una consola (`cmd`):
```
python -m pip install requests pandas
```
Si `pip` no sale a internet, usá el repositorio de paquetes interno
(`pip install --index-url <url_interna> requests pandas`) o bajá los *wheels* (`.whl`) en otra
PC y corré `pip install --no-index --find-links <carpeta_wheels> requests pandas`.
Para la descarga alcanza con `requests`; `pandas` sirve para revisar los CSV.

**2. Copiar tres archivos.** Creá `C:\monetario\codigo\` y `C:\monetario\datos\`. En
github.com/msangia/monetario, rama `claude/affectionate-brown-oqk41w` (selector de ramas),
abrí cada archivo de `codigo/`, hacé clic en **Raw** y *Guardar como...* (Ctrl+S) en
`C:\monetario\codigo\` con el mismo nombre:
- `descargar_bcra.py`
- `series.txt` (los 11 IDs, ya verificados contra el catálogo)
- `verificar_series.py` (control posterior; sólo usa la biblioteca estándar)

Copiá también `datos/catalogo_monetarias.csv` (Raw > Guardar como) a `C:\monetario\datos\`.
Revisá que el navegador no agregue `.txt` al nombre (`descargar_bcra.py.txt`).

**3. Descargar.** Desde `C:\monetario\codigo\`:
```
python descargar_bcra.py --series series.txt --desde 2003-01-01
```
Si da error de conexión o *timeout*, la red exige proxy. No lo escribas en ningún archivo:
```
set HTTPS_PROXY=http://<proxy>:<puerto>
python descargar_bcra.py --series series.txt --desde 2003-01-01
```
o bien `--proxy http://<proxy>:<puerto>`. Si el proxy pide usuario, preguntá a Sistemas el
formato admitido; **no** dejes la contraseña en scripts ni en el log que vayas a compartir.

**4. Qué aparece.**
- `C:\monetario\datos\bcra_<id>_daily.csv`, uno por ID (`fecha,valor`).
- `C:\monetario\datos\metadata_<id>.json`: fila del catálogo, metodología y control
  (`"validacion": "ok"` si las filas bajadas coinciden con el `count` de la API).
- `C:\monetario\codigo\descarga_bcra.log`: registro de la corrida. **No se sube** (puede
  mostrar datos de la red interna).

**5. Controlar que estén completos.** Desde `C:\monetario\codigo\`:
```
python verificar_series.py --series series.txt --desde 2003-01-01
```
Muestra, por ID: descripción, periodicidad, primer y último dato del catálogo, filas y
primer y último dato del CSV, y un estado. Todo debe decir `ok`:
- `ok`: el CSV empieza en 2003 (o en el primer dato del catálogo, si es posterior: 197 en
  2021, 150 en 2008, 44 en 2024), termina a lo sumo 7 días antes que el catálogo y el
  metadata dice `ok`;
- `revisar`: falta un tramo o hubo diferencia con el `count`: volvé a correr el paso 3 sólo
  para ese ID (`python descargar_bcra.py --ids 109 --desde 2003-01-01`);
- `falta`: no se bajó (mirá el error en pantalla o en el log).

Como referencia, una serie diaria completa desde 2003 tiene unas 5.700–5.900 filas
(días hábiles).

**6. Subir a GitHub por la web.** En el repositorio, rama
`claude/affectionate-brown-oqk41w` (o `main`, si ya se mergeó):
1. entrá a la carpeta `datos/`;
2. *Add file > Upload files*;
3. arrastrá los 11 `bcra_<id>_daily.csv` y los 11 `metadata_<id>.json` (**no** el `.log`);
4. mensaje: "Series diarias BCRA (API v4.0) al AAAA-MM-DD";
5. *Commit directly to the ... branch* > *Commit changes*.

Antes de subir, abrí un `metadata_<id>.json` y verificá que no mencione servidores, usuarios
ni rutas internas.

**7. Errores típicos y qué pegarle al asistente.**

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `ModuleNotFoundError: requests` | falta la dependencia | paso 1 |
| `ConnectionError`, `ProxyError`, *timeout* | proxy | paso 3 con `HTTPS_PROXY` o `--proxy` |
| `SSLError` / `CERTIFICATE_VERIFY_FAILED` | inspección TLS del proxy institucional | pedir a Sistemas el certificado raíz y usar `set REQUESTS_CA_BUNDLE=<ruta_al_.pem>`; **no** desactivar la verificación |
| `429` o `5xx` repetidos | límite de la API | esperar unos minutos y repetir (el script ya reintenta) |
| `revisar` en el paso 5 | descarga parcial | repetir ese ID con `--ids` |
| `python` no se reconoce | Python no está en el PATH | usar `py` en lugar de `python` |

Para pedir ayuda, pegá: (a) el comando exacto, (b) las últimas 20 líneas de la pantalla o del
log **sin** nombres de servidores, usuarios ni contraseñas (reemplazalos por `<proxy>`), y
(c) la salida de `python verificar_series.py --series series.txt`.

## Uso de estos archivos en las rutinas

```
python -m monetario_demo.demanda_dinero --dinero 109 --tasa 1189 \
    --precios datos/ipc_mensual.csv --actividad datos/emae_mensual.csv
```
`--actividad` usa `emae_se` (desestacionalizado) por defecto; para la serie original:
`datos/emae_mensual.csv:emae_orig`. Ver `codigo/README.md`.
