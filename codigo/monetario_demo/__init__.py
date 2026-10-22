"""Rutinas ilustrativas de análisis monetario (proyecto 426 05).

Módulos:
    datos           cargadores de CSV y de la API del BCRA; datos sintéticos de demostración
    evaluacion      métricas fuera de muestra, cobertura y test de Diebold-Mariano (HLN)
    liquidez        Anexo A, Eje 1: pronóstico diario con efectos de calendario
    demanda_dinero  Anexo B, Eje 4: demanda de dinero con corrección de errores en ventanas móviles
    bandas          Anexo C, Eje 4: banda de tolerancia y fan chart por cuantiles empíricos

Toda salida generada con ``--demo`` usa DATOS SINTÉTICOS DE DEMOSTRACIÓN, NO OFICIALES.
"""

__version__ = "0.1.0"
