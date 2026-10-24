# Protocolo del proyecto – Gerente/a de Análisis Monetario (426 05, BCRA)

## Objetivo

Elaborar el **proyecto con propuestas a desarrollar en la Gerencia de Análisis Monetario**, requerido por el perfil del puesto, en un archivo LaTeX (`proyecto.tex`) de **máximo 4 páginas** con formato estándar. El proyecto debe poder superar el análisis independiente de un jurado de selección.

## Insumos (raíz del repositorio)

| Archivo | Contenido | Uso |
|---|---|---|
| `Perfil 426 05.pdf` | Requisitos del cargo y consigna del proyecto | Criterios de alineación |
| `manual_organico.docx` | Manual orgánico: misión, 11 funciones, subgerencias (reemplaza al PDF `p426_RD214_...`, ya eliminado) | Estructura de las propuestas |
| `MSangia_CVeng.pdf` | CV del postulante (en inglés) | **Única fuente** de datos biográficos; fundamenta la credibilidad del proyecto |
| `Programa_Trabajo_gerente.pdf`, `Programa_Trabajo_subgerente.pdf` | Proyectos de **otros cargos** (Subgerente de Modelos Macroeconómicos / Macro-Financieros) | Sólo referencia de nivel y estilo. **No reutilizar contenido** |

Lectura de PDF: `pdftotext -layout "<archivo>.pdf" -`. Lectura del `.docx`: `python3 -c "import zipfile,re;x=zipfile.ZipFile('manual_organico.docx').read('word/document.xml').decode();print(re.sub(r'<[^>]+>',' ',x.replace('</w:p>','\n')))"`.

## Agentes (`.claude/agents/`, los tres `claude-opus-5-5`)

- **`autor-proyecto`**: especialista en análisis monetario con experiencia en BoE, Fed St. Louis, NY Fed, BCE y Banco de Canadá, adaptada al caso argentino. Hace el benchmark, el esquema y la redacción.
- **`analista-python-monetario`**: experto en análisis monetario con Python. Escribe y prueba las rutinas de `codigo/` y redacta `anexos_cuerpo.tex`. No toca el núcleo (`proyecto.tex`).
- **`jurado-seleccion`**: experto en RR.HH. y selección de personal. Evalúa de forma **independiente**, sin herramientas de escritura, y emite el dictamen.

Si el entorno no carga los agentes por nombre (se cargan al iniciar la sesión), invocar un subagente genérico con el contenido del archivo del agente como instrucciones y `model: opus`.

## Reglas inamovibles

1. **Núcleo: máximo 4 páginas** en PDF (`proyecto.tex`); los **anexos** (`anexos_cuerpo.tex`, incluido por `proyecto.tex` desde la página 5 en un único PDF; `anexos.tex` es sólo un envoltorio para compilarlos aparte) no integran ese límite, pero el núcleo debe entenderse sin ellos. Antes de presentar, el usuario confirma que la convocatoria admite anexos. Formato estándar: A4, márgenes 2,5 cm, cuerpo 11 pt, interlineado simple (1,0–1,15). Prohibido achicar márgenes, fuente o interlineado, o forzar el espaciado para entrar: se recorta contenido.
2. **Nada inventado.** No se escriben cifras, publicaciones, cargos, cursos, normas ni prácticas de otros bancos centrales que no estén verificados. Los datos biográficos del postulante salen **únicamente** de `MSangia_CVeng.pdf` (o de lo que confirme el usuario) y deben coincidir con él (cargos, fechas, cursos, publicaciones). Nunca se incluyen datos personales de contacto o de nacimiento. No se atribuye experiencia que el CV no muestre (p. ej., operaciones de liquidez): se aprovecha la real y se ofrece un plan para cubrir el resto.
3. **Confidencialidad.** No incluir datos internos ni información sensible del BCRA; usar sólo información pública. La propuesta de IA debe resguardar la información sensible (entornos internos).
4. **Independencia del jurado.** Al invocarlo se le pasa **sólo** la ruta de `proyecto.tex`/`proyecto.pdf` y la consigna de evaluar (el jurado ya sabe que puede consultar el CV para contrastar afirmaciones biográficas). No se le pasa la justificación del autor, ni el contenido de `trabajo/`, ni versiones anteriores de su dictamen.
5. **Adaptar, no copiar.** Cada práctica internacional se presenta con qué se toma, qué se cambia y por qué sirve en Argentina.
6. **Trazabilidad.** Toda propuesta se vincula a una función del manual o a un requisito del perfil.
7. **Datos y código.** Los resultados de los anexos provienen de datos públicos reales (`datos/` o API) o, si no hay acceso, de datos sintéticos **rotulados como tales**; nunca se presentan cifras sintéticas como oficiales. Todo código en `codigo/` con tests que pasen (`pytest`).
8. **Git.** Desarrollar en la rama asignada a la sesión; commits descriptivos; no crear PR salvo pedido expreso.

## Fases

| Fase | Responsable | Producto | Criterio de salida |
|---|---|---|---|
| 0. Lectura de insumos | autor | Notas en `trabajo/` | Perfil y manual leídos completos |
| 1. Matriz de trazabilidad | autor | `trabajo/matriz_trazabilidad.md` | Todo requisito del perfil y las 11 funciones mapeados |
| 2. Benchmark internacional verificado | autor | `trabajo/benchmark_internacional.md` | Fuente, fecha y nivel de confianza por práctica; lo "a verificar" no entra al proyecto |
| 3. Esquema con presupuesto de páginas | autor | Esquema (≤1 página) | Suma ≤ 4 páginas; aprobado por el usuario si lo solicita |
| 4. Redacción | autor | `proyecto.tex` | Compila sin errores |
| 5. Control formal | autor | `proyecto.pdf` | `pdfinfo` ≤ 4 páginas; sin *overfull* graves; referencias coherentes |
| 6. Revisión independiente | jurado | `trabajo/revisiones/dictamen_NN.md` | Veredicto registrado |
| 7. Corrección | autor | `proyecto.tex` ajustado + `trabajo/revisiones/respuesta_NN.md` | Todos los "cambios obligatorios" atendidos |
| 8. Cierre | autor | Versión final + commit | Veredicto **APROBADO** (≥ 80/100, ningún criterio < 60 %) |

Las fases 5-7 se repiten hasta obtener **APROBADO**, con un máximo de **4 iteraciones**; si no se alcanza, se informa al usuario con las discrepancias pendientes.

## Convenciones

- Idioma: español institucional (rioplatense neutro), primera persona, tono propositivo y sobrio.
- Compilación: `pdflatex -interaction=nonstopmode proyecto.tex` dos veces (o `latexmk -pdf` si está disponible). Artefactos auxiliares ignorados por git; se versiona `proyecto.pdf`.
- Autor y datos del postulante: macros al comienzo de `proyecto.tex` (`\autor`, `\trayectoria`), para ajustarlas sin tocar el cuerpo.
- Estructura del cuerpo: introducción y enfoque → ejes de trabajo ligados al manual → conducción y equipo → hoja de ruta con hitos e indicadores → riesgos → referencias breves.
- Cada eje: **qué** (entregable), **cómo** (método/referencia adaptada), **cuándo** (periodicidad/plazo), **cómo se mide** (indicador).

## Estructura del repositorio

```
CLAUDE.md                     Este protocolo
.claude/agents/               autor-proyecto.md, jurado-seleccion.md
proyecto.tex / proyecto.pdf   Entregable (≤ 4 páginas)
trabajo/                      Matriz, benchmark, revisiones (material de trabajo; no se entrega)
anexos_cuerpo.tex / anexos.tex  Anexos breves (incluidos en proyecto.pdf) con ejemplos de rutinas Python (fuera del límite de 4 páginas)
codigo/                       Rutinas Python, tests y requirements
datos/                        CSV públicos (los deja el usuario) o sintéticos rotulados
MSangia_CVeng.pdf, manual_organico.docx, *.pdf   Insumos
```
