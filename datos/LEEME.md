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
| `ipc_historico.csv` | cargado (IPC empalmado, 1992-12 a 2026-09; igual al oficial desde 2016-12; **fuente previa a 2016-12 a documentar**) | `fecha,ipc`; `fecha` en `d/m/aaaa` |
| `bcra_<id>_daily.csv` + `metadata_<id>.json` | cargados (descarga 2026-10-22): los 11 IDs de `series.txt` (15, 16, 17, 104, 109, 197, 46, 11, 150, 1189, 44), todos `ok` | `fecha,valor` (ISO) |

Los cargadores leen EMAE e IPC tal como están (meses en español, `sept`/`set`, espacios
finales); no hace falta convertirlos. Las series diarias usan `fecha,valor` con
`fecha` `AAAA-MM-DD` y punto decimal; `descargar_bcra.py` ya las genera así.

**Estado:** completo. Para actualizar, repetir los pasos 3 a 6 y correr
`python correr_reales.py` desde `codigo/`. Pendiente: documentar la fuente de
`ipc_historico.csv` antes de dic-2016.

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

## Pendiente opcional: factores de la base para modelar las cuentas corrientes (Eje 1)

El Anexo A muestra que las cuentas corrientes de las entidades en el BCRA (15 − 16) explican
casi toda la varianza diaria de la base y que el calendario no las predice. Para evaluar con
datos públicos un modelo **por factores** hace falta bajar estas series (no descargadas; bloque
comentado en `codigo/series.txt`). Todas diarias, en millones de ARS; fechas del catálogo
2026-10:

| id | Descripción (catálogo) | Primer dato | Último dato | Factor del informe diario |
|---|---|---|---|---|
| 19 | Depósitos de las entidades financieras en cuenta corriente en el BCRA (saldo) | 2001-06-01 | 2026-10-19 | variable objetivo (control de 15 − 16) |
| 47 | Efecto monetario de las compras netas de divisas al sector privado y otros | 2003-01-02 | 2026-10-16 | compra-venta de USD, privado |
| 48 | Efecto monetario de las compras netas de divisas al Tesoro Nacional | 2003-01-02 | 2026-10-16 | compra-venta de USD, sector público |
| 49 | Efecto monetario de los adelantos transitorios al Tesoro Nacional | 2003-01-02 | 2026-10-16 | adelantos transitorios |
| 50 | Efecto monetario de las transferencias de utilidades al Tesoro Nacional | 2003-01-02 | 2026-10-16 | utilidades |
| 51 | Efecto monetario del resto de operaciones con el Tesoro Nacional | 2003-01-02 | 2026-10-16 | depósitos del Gobierno en el BCRA |
| 52 | Efecto monetario de las operaciones de pases | 2003-01-02 | 2026-10-16 | pases pasivos (REPO) y activos |
| 53 | Efecto monetario de las LELIQ y NOTALIQ | 2003-01-02 | 2026-10-16 | operaciones de mercado abierto |
| 54 | Efecto monetario de los redescuentos y adelantos | 2003-01-02 | 2026-10-16 | otros |
| 55 | Efecto monetario de intereses, primas y remuneración de cuentas corrientes (pases, LELIQ, NOTALIQ, redescuentos) | 2003-01-02 | 2026-10-16 | otros (intereses) |
| 58 | Efecto monetario de las operaciones con letras fiscales de liquidez (LEFI) | 2003-01-02 | 2026-10-16 | LEFI (hasta 2025-07) |
| 59 | Efecto monetario de otras operaciones que explican la variación de la base | 2003-01-02 | 2026-10-16 | otros |

Opcionales: 56 (LEBAC y NOBAC, relevante hasta 2018) y los saldos 152 (pases pasivos),
154 (pases activos), 155 (LELIQ y NOTALIQ) y 196 (LEFI, hasta 2025-07-11) para controlar
flujos contra variaciones de saldos. El 46 (total) ya está descargado. Comando:
```
python descargar_bcra.py --ids 19 47 48 49 50 51 52 53 54 55 58 59 --desde 2003-01-01
```
o, equivalente, `python descargar_bcra.py --series series_factores.txt --desde 2003-01-01`; control: `python verificar_series.py --series series_factores.txt --desde 2003-01-01` (paso 5). Subir los 12 CSV y sus `metadata_<id>.json` como en el paso 6.

**Cómo se usarían sin *look-ahead*.** Por identidad, la variación diaria de la base es la suma
de los factores (= id 46), y la de las cuentas corrientes es esa suma menos la variación de la
circulación (16). Por eso los factores del **mismo día** no pueden usarse como regresores: serían
la respuesta. Hay tres variantes honestas, que se informarían por separado:
1. **Factores rezagados** (t − 1 a t − 5, y su suma en la semana): sólo información ya
   publicada al pronosticar; capta persistencia (p. ej., compras de divisas sostenidas).
2. **Factores programados con su calendario** (no su monto): días de liquidación de
   licitaciones del Tesoro y de vencimientos, pago de intereses y remuneraciones (55), fin del
   período de cómputo del efectivo mínimo. Las fechas son públicas de antemano (cronograma de
   licitaciones de la Secretaría de Finanzas; calendario de vencimientos); entran como variables
   indicadoras junto al calendario actual. Los **montos** programados (p. ej., el uso de los
   depósitos del Tesoro, 51) son información interna: con datos públicos sólo se evalúa una
   **cota superior** ("previsión perfecta" del factor 51 o 55), rotulada como no factible.
3. **Benchmark**: el ingenuo y el ensamble de calendario actuales, con DM-HLN al 10 % y la misma
   muestra (ene-2022 en adelante; tramo desde 11-07-2025 aparte).
La distancia entre (1)–(2) y la cota de previsión perfecta mide cuánto valdría la
programación interna de factores: el argumento del Eje 1.

## Uso de estos archivos en las rutinas

```
python -m monetario_demo.demanda_dinero --dinero 109 --tasa 1189 \
    --precios empalmado --actividad datos/emae_mensual.csv
```
`--actividad` usa `emae_se` (desestacionalizado) por defecto; para la serie original:
`datos/emae_mensual.csv:emae_orig`. Ver `codigo/README.md`.
