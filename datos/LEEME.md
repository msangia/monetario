# Carpeta `datos/`: cómo cargar series reales

Las rutinas de `codigo/` leen archivos CSV de esta carpeta. Mientras no haya CSV, usan
datos sintéticos de demostración (`--demo`). **Subí sólo series públicas.** No subas datos
por entidad, información interna ni nada de liquidez que no esté publicado.

## Formato

Un archivo por serie, con dos columnas:

```
fecha,valor
2024-01-02,123456.7
2024-01-03,124001.2
```

`fecha` va en formato `AAAA-MM-DD`. `valor` va con punto decimal y sin separador de miles.
`descargar_bcra.py` ya los genera así.

## Paso a paso (en la PC del BCRA, sin git)

1. **Bajar el script.** En GitHub, abrí el repositorio `msangia/monetario` y elegí la rama
   `claude/affectionate-brown-oqk41w` en el selector de ramas. Hay dos opciones:
   - **Repositorio completo:** *Code > Download ZIP* y descomprimilo.
   - **Sólo el descargador:** bajá `codigo/descargar_bcra.py` y `codigo/series.txt` (botón
     *Download raw file* de cada archivo) a una carpeta `codigo/`, y creá una carpeta `datos/`
     al lado.
2. **Requisitos.** Python 3.10 o superior y `requests`. Para correr las rutinas, además:
   `pip install -r codigo/requirements.txt`.
3. **Proxy (si la red lo exige).** No lo escribas en ningún archivo. Usá una de estas dos formas:
   - una variable de entorno, sólo en tu sesión: `set HTTPS_PROXY=http://<proxy>:<puerto>` en
     Windows o `export HTTPS_PROXY=...` en Linux;
   - el argumento `--proxy http://<proxy>:<puerto>`.
4. **Encontrar los IDs.** Desde la carpeta `codigo/`:
   ```
   python descargar_bcra.py --buscar "base monetaria" --buscar circulacion --buscar M2
   python descargar_bcra.py --buscar depositos --buscar call --buscar caucion --buscar tamar
   ```
   Esto guarda `datos/catalogo_monetarias.csv` (catálogo completo) y lista en pantalla `ID`,
   periodicidad, última fecha y descripción. Verificá la descripción de cada ID en el catálogo.
5. **Anotar los IDs** en `codigo/series.txt`, uno por línea. Lo que sigue a `#` es comentario.
6. **Descargar:**
   ```
   python descargar_bcra.py --series series.txt --desde 2003-01-01
   ```
   Por cada ID se generan:
   - `datos/bcra_<id>_daily.csv`: la serie (`fecha,valor`). El nombre dice `daily`, pero
     respeta la periodicidad de la serie.
   - `datos/metadata_<id>.json`: la fila del catálogo, la metodología y el control de la descarga.
     Si `"validacion"` no es `"ok"`, las filas bajadas no coinciden con el `count` de la API.

   El registro de la corrida queda en `codigo/descarga_bcra.log`. **Ese archivo no se sube**:
   puede mostrar datos de la red interna.
7. **Series de INDEC (para la rutina B).** No están en esta API. Bajá a mano el EMAE (índice
   mensual, desestacionalizado u original, siempre el mismo) y el IPC (nivel general, índice
   mensual) desde INDEC o datos.gob.ar. Guardalos como `datos/emae_mensual.csv` y
   `datos/ipc_mensual.csv`, en el mismo formato `fecha,valor`, con la fecha del primer día del mes.
8. **Subir a GitHub por la web.** En el repositorio, con la rama
   `claude/affectionate-brown-oqk41w` elegida:
   1. entrá a la carpeta `datos/`;
   2. hacé clic en *Add file > Upload files*;
   3. arrastrá los `bcra_<id>_daily.csv`, `metadata_<id>.json`, `catalogo_monetarias.csv` y los
      CSV de INDEC;
   4. escribí un mensaje (p. ej., "Datos públicos BCRA e INDEC al AAAA-MM-DD");
   5. elegí *Commit directly to the `claude/affectionate-brown-oqk41w` branch* y confirmá.

   Antes de subir, revisá que todo sea público y que ningún archivo mencione servidores, usuarios
   o rutas internas.

## Series sugeridas

| Serie (buscar en el catálogo) | Frecuencia | Uso |
|---|---|---|
| Base monetaria (saldo) | diaria | Rutina A (liquidez) y C (banda) |
| Circulación monetaria / billetes y monedas en poder del público | diaria | Rutina A (billetes) y construcción de M2 |
| Depósitos del sector privado en pesos (cuenta corriente, caja de ahorro, plazo fijo) | diaria | Construcción de M2 y seguimiento |
| M2 privado (o M2 transaccional del sector privado, si está publicado) | diaria o mensual | Rutina B (demanda de dinero) y C (banda) |
| Tasa call interbancaria, tasa de caución | diaria | Eje 1 (cuadro de tasas) y costo de oportunidad |
| TAMAR, BADLAR o tasa de plazo fijo | diaria | Rutina B (costo de oportunidad, en % anual) |
| EMAE e IPC (INDEC, fuera de esta API) | mensual | Rutina B |

Si alguna serie no aparece en el catálogo de la API, puede bajarse a mano desde
bcra.gob.ar > Estadísticas > Principales variables. Si sale en Excel, guardala como CSV con las
columnas `fecha,valor` y un nombre descriptivo (p. ej., `datos/m2_privado_mensual.csv`).
