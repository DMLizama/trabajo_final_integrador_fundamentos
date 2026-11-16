""" Uso: python cancionero.py cancion.txt --semitonos N [--latino] [--salida salida.txt] """

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Garantizar que el directorio del script esté en sys.path (incluso en entornos Python embebidos)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from acordes import (
    ALTERACIONES_INUSUALES,
    ER_TOKEN,
    Acorde,
    es_linea_de_acordes,
    extraer_acorde,
    transponer_acorde,
)

# ==============================================================================
# 1. EXPRESIONES REGULARES DE ESTRUCTURA DEL BLOQUE (CANCIÓN)
# ==============================================================================

# Reconoce el inicio de un bloque de canción: '# Título de la canción'
ER_TITULO = re.compile(r"^\s*#\s+(.+?)\s*$")

# Reconoce la línea opcional de tonalidad: 'Tono: X'
ER_TONO = re.compile(r"^\s*Tono:\s*(\S+)\s*$", re.IGNORECASE)

# Reconoce una línea en blanco (separador de estrofas)
ER_LINEA_VACIA = re.compile(r"^\s*$")


# ==============================================================================
# 2. ESTRUCTURA DE RESULTADOS Y PROCESAMIENTO
# ==============================================================================

@dataclass
class RegistroAcorde:
    """Almacena el desglose de un acorde extraído junto con su ubicación y transformación."""
    linea: int
    cancion: str
    acorde: Acorde
    transpuesto: str


@dataclass
class ResultadoCancionero:
    """Agrupa el texto transpuesto, los acordes extraídos y las validaciones/errores."""
    lineas_salida: list[str] = field(default_factory=list)
    acordes_extraidos: list[RegistroAcorde] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


def procesar_linea_acordes(
    linea: str,
    num_linea: int,
    cancion_actual: str,
    semitonos: int,
    usar_latino: bool,
    resultado: ResultadoCancionero,
) -> str:
    """
    Extrae cada acorde de una línea de acordes, lo separa en sus componentes,
    rechaza los acordes mal escritos y reconstruye la línea manteniendo la
    alineación exacta sobre las sílabas de la letra.
    """
    reemplazos: list[tuple[int, str]] = []

    for match in ER_TOKEN.finditer(linea.rstrip()):
        token = match.group(0)
        columna_original = match.start()
        acorde = extraer_acorde(token)

        if acorde is None:
            # Acorde mal escrito: se registra el rechazo y se marca en la salida
            resultado.advertencias.append(
                f"Línea {num_linea} ({cancion_actual}): Acorde mal escrito rechazado -> '{token}'"
            )
            reemplazos.append((columna_original, f"[?{token}]"))
            continue

        # Validación semántica adicional: advertir alteraciones enarmónicas inusuales (E#, B#, Cb, Fb)
        nota_con_alt = f"{acorde.nota}{acorde.alteracion}"
        if nota_con_alt in ALTERACIONES_INUSUALES or acorde.bajo_completo in ALTERACIONES_INUSUALES:
            resultado.advertencias.append(
                f"Línea {num_linea} ({cancion_actual}): Alteración inusual en '{token}' (normalizada al transponer)"
            )

        acorde_nuevo = transponer_acorde(acorde, semitonos, usar_latino)
        resultado.acordes_extraidos.append(
            RegistroAcorde(
                linea=num_linea,
                cancion=cancion_actual,
                acorde=acorde,
                transpuesto=acorde_nuevo,
            )
        )
        reemplazos.append((columna_original, acorde_nuevo))

    # Reconstrucción de la línea respetando la columna original de cada acorde
    linea_reconstruida = ""
    for col_original, texto_acorde in reemplazos:
        min_espacios = 1 if linea_reconstruida else 0
        espacios = max(min_espacios, col_original - len(linea_reconstruida))
        linea_reconstruida += (" " * espacios) + texto_acorde

    return linea_reconstruida


def procesar_tono(
    tono_str: str,
    num_linea: int,
    cancion_actual: str,
    semitonos: int,
    usar_latino: bool,
    resultado: ResultadoCancionero,
) -> str:
    """
    Valida y transpone la línea opcional 'Tono: X'.
    Además de validar con ER_ACORDE, comprueba semánticamente que sea una tonalidad
    musical válida (mayor o menor, sin bajo invertido ni tipos como sus4/7).
    """
    acorde_tono = extraer_acorde(tono_str)
    if acorde_tono is None:
        resultado.advertencias.append(
            f"Línea {num_linea} ({cancion_actual}): Tonalidad inválida rechazable -> 'Tono: {tono_str}'"
        )
        return f"Tono: [?{tono_str}]"

    # Validación semántica (lo que la ER general de acordes no restringe):
    # Una tonalidad solo puede ser mayor ('') o menor ('m'), y sin nota de bajo ('/X')
    if acorde_tono.tipo not in ("", "m") or acorde_tono.bajo_nota != "":
        resultado.advertencias.append(
            f"Línea {num_linea} ({cancion_actual}): 'Tono: {tono_str}' es un acorde pero no una tonalidad estándar (debe ser mayor o menor simple)"
        )

    tono_nuevo = transponer_acorde(acorde_tono, semitonos, usar_latino)
    return f"Tono: {tono_nuevo}"


def procesar_cancionero(
    texto: str, semitonos: int = 0, usar_latino: bool = False
) -> ResultadoCancionero:
    """
    Procesa el contenido completo de un archivo de cancionero línea por línea.
    Ignora líneas vacías al final del archivo según lo requerido por la cátedra.
    """
    resultado = ResultadoCancionero()
    lineas = texto.splitlines()

    # Eliminar líneas vacías al final del archivo para que no alteren el resultado
    while lineas and ER_LINEA_VACIA.match(lineas[-1]):
        lineas.pop()

    cancion_actual = "Sin título"
    esperando_tono = False

    for indice, linea_cruda in enumerate(lineas, start=1):
        # 1. ¿Es inicio de bloque (# Título)?
        match_titulo = ER_TITULO.match(linea_cruda)
        if match_titulo:
            cancion_actual = match_titulo.group(1)
            esperando_tono = True # Como encontramos el título, esperamos que después posiblemente venga la tonalidad de la canción
            resultado.lineas_salida.append(f"# {cancion_actual}")
            continue

        # 2. ¿Es la línea opcional 'Tono: X' después del título?
        match_tono = ER_TONO.match(linea_cruda)
        if match_tono:
            if not esperando_tono: # Caso en el que la tonalidad fue encontrada en otra posición distinta...
                resultado.advertencias.append(
                    f"Línea {indice} ({cancion_actual}): 'Tono:' encontrado fuera del encabezado de la canción"
                )
            esperando_tono = False
            tono_original = match_tono.group(1)
            linea_tono = procesar_tono(
                tono_original, indice, cancion_actual, semitonos, usar_latino, resultado
            )
            resultado.lineas_salida.append(linea_tono)
            continue

        # 3. ¿Es una línea en blanco (separador de estrofas)?
        if ER_LINEA_VACIA.match(linea_cruda):
            esperando_tono = False
            resultado.lineas_salida.append("")
            continue

        esperando_tono = False

        # 4. Distinguir línea de acordes vs. línea de letra
        if es_linea_de_acordes(linea_cruda):
            linea_transpuesta = procesar_linea_acordes(
                linea_cruda, indice, cancion_actual, semitonos, usar_latino, resultado
            )
            resultado.lineas_salida.append(linea_transpuesta)
        else:
            # Línea de letra: se conserva el texto limpiando espacios superfluos de los extremos
            resultado.lineas_salida.append(linea_cruda.strip())

    return resultado


# ==============================================================================
# 3. FORMATEO DE REPORTE Y CLI
# ==============================================================================

def generar_reporte(resultado: ResultadoCancionero) -> str:
    """Construye el texto completo de salida junto con el desglose y validaciones."""
    bloques: list[str] = []

    # 1. Cancionero transpuesto
    bloques.append("\n".join(resultado.lineas_salida))

    # 2. Tabla de desglose de acordes extraídos (Nota, Alteración, Tipo, Bajo)
    bloques.append("\n" + "=" * 72)
    bloques.append("RESUMEN DE ACORDES EXTRAÍDOS (EXPRESIONES REGULARES)")
    bloques.append("=" * 72)
    encabezado = f"{'Línea':<7} {'Original':<10} {'Nota':<6} {'Alt.':<6} {'Tipo':<8} {'Bajo':<8} {'Transpuesto':<12}"
    bloques.append(encabezado)
    bloques.append("-" * 72)

    for reg in resultado.acordes_extraidos:
        ac = reg.acorde
        bloques.append(
            f"{reg.linea:<7} {ac.texto_original:<10} {ac.nota:<6} "
            f"{(ac.alteracion or '-'):<6} {(ac.tipo or '-'):<8} "
            f"{(ac.bajo_completo or '-'):<8} {reg.transpuesto:<12}"
        )

    # 3. Reporte de errores / acordes rechazados
    bloques.append("\n" + "=" * 72)
    bloques.append("VALIDACIONES Y ACORDES RECHAZADOS")
    bloques.append("=" * 72)
    if resultado.advertencias:
        for adv in resultado.advertencias:
            bloques.append(f"[!] {adv}")
    else:
        bloques.append("[OK] Todos los acordes y tonalidades son válidos.")

    return "\n".join(bloques) + "\n"


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Procesa, valida y transpone un cancionero con acordes usando Expresiones Regulares."
    )
    parser.add_argument(
        "archivo",
        help="Ruta al archivo de texto de entrada en UTF-8 (ej. cancion.txt)",
    )
    parser.add_argument(
        "--semitonos",
        type=int,
        default=0,
        help="Cantidad de semitonos a transponer (positivo o negativo, ej. --semitonos -2)",
    )
    parser.add_argument(
        "--latino",
        action="store_true",
        help="Convierte la salida al cifrado latino (Do, Re, Mi, Fa, Sol, La, Si)",
    )
    parser.add_argument(
        "--salida",
        type=str,
        default=None,
        help="Archivo .txt donde guardar el resultado (por defecto: <entrada>_salida.txt)",
    )
    return parser


def main() -> int:
    # Asegurar salida UTF-8 en consolas de Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = construir_parser()
    args = parser.parse_args()

    ruta_entrada = Path(args.archivo)
    if not ruta_entrada.is_file():
        print(f"Error: No se encontró el archivo '{ruta_entrada}'.", file=sys.stderr)
        return 1

    texto_entrada = ruta_entrada.read_text(encoding="utf-8")
    resultado = procesar_cancionero(
        texto_entrada, semitonos=args.semitonos, usar_latino=args.latino
    )

    reporte_completo = generar_reporte(resultado)

    # Mostrar por consola
    print(reporte_completo)

    # Guardar en archivo .txt (cancionero transpuesto + reporte)
    if args.salida:
        ruta_salida = Path(args.salida)
    else:
        ruta_salida = ruta_entrada.with_name(f"{ruta_entrada.stem}_salida.txt")

    ruta_salida.write_text(reporte_completo, encoding="utf-8")
    print(f"--> Resultado guardado en: {ruta_salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
