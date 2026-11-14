"""Módulo de Expresiones Regulares y lógica musical para el procesamiento de acordes."""

import re
from dataclasses import dataclass
from typing import Optional

# ==============================================================================
# 1. DEFINICIÓN DE EXPRESIONES REGULARES
# ==============================================================================

# Reconoce un acorde en cifrado americano o latino y lo separa en:
#   Grupo 1 (nota):       A-G o Do, Re, Mi, Fa, Sol, La, Si
#   Grupo 2 (alteracion): # o b (opcional)
#   Grupo 3 (tipo):       m, 7, maj7, m7, sus2, sus4, dim, aug, add9, 6, 9, 5 (opcional)
#   Grupo 4 (bajo_nota):  Nota del bajo luego de '/' (opcional)
#   Grupo 5 (bajo_alt):   Alteración del bajo # o b (opcional)
PATRON_NOTA = r"(?:Do|Re|Mi|Fa|Sol|La|Si|[A-G])"
PATRON_ALTERACION = r"(#|b)"
PATRON_TIPO = r"(maj7|maj9|m7b5|m7|m6|m9|m|sus2|sus4|sus|dim7|dim|aug|add9|7|9|6|5)"

ER_ACORDE = re.compile(
    rf"^({PATRON_NOTA}){PATRON_ALTERACION}?{PATRON_TIPO}?(?:/({PATRON_NOTA}){PATRON_ALTERACION}?)?$"
)

# Reconoce cualquier token separado por espacios (conservando su columna inicial)
ER_TOKEN = re.compile(r"\S+")

# Reconoce un token con apariencia de intento de acorde (empieza con mayúscula,
# sin signos de puntuación literarios como comas, signos de exclamación, etc.)
ER_CANDIDATO_ACORDE = re.compile(r"^[A-Z][A-Za-z0-9#/]*$")

# Reconoce un token que contiene símbolos exclusivos de cifrado musical (números, '#' o '/')
ER_SIMBOLOS_CIFRADO = re.compile(r"^[A-Za-z]+[0-9#/][A-Za-z0-9#/]*$")

# Alteraciones enarmónicas inusuales que conviene advertir (aunque sean procesables)
ALTERACIONES_INUSUALES = {"E#", "B#", "Cb", "Fb", "Mi#", "Si#", "Dob", "Fab"}


# ==============================================================================
# 2. ESCALAS Y EQUIVALENCIAS MUSICALES
# ==============================================================================

ESCALA_CROMATICA = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Equivalencias para normalizar cualquier nota (latina o con bemoles/sostenidos) a su índice 0-11
INDICE_POR_NOTA = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

LATINO_A_AMERICANO = {
    "Do": "C",
    "Re": "D",
    "Mi": "E",
    "Fa": "F",
    "Sol": "G",
    "La": "A",
    "Si": "B",
}

AMERICANO_A_LATINO = {v: k for k, v in LATINO_A_AMERICANO.items()}


# ==============================================================================
# 3. ESTRUCTURAS DE DATOS Y FUNCIONES DE VALIDACIÓN / TRANSPOSICIÓN
# ==============================================================================

@dataclass
class Acorde:
    """Representa un acorde válido desglosado en sus componentes."""
    texto_original: str
    nota: str
    alteracion: str = ""
    tipo: str = ""
    bajo_nota: str = ""
    bajo_alteracion: str = ""

    @property
    def bajo_completo(self) -> str:
        return f"{self.bajo_nota}{self.bajo_alteracion}" if self.bajo_nota else ""


def extraer_acorde(token: str) -> Optional[Acorde]:
    """
    Evalúa si un token es un acorde válido usando ER_ACORDE.
    Si es válido, devuelve un objeto Acorde con nota, alteración, tipo y bajo.
    Si está mal escrito, devuelve None.
    """
    coincidencia = ER_ACORDE.match(token)
    if not coincidencia:
        return None

    nota, alt, tipo, bajo_nota, bajo_alt = coincidencia.groups()
    return Acorde(
        texto_original=token,
        nota=nota,
        alteracion=alt or "",
        tipo=tipo or "",
        bajo_nota=bajo_nota or "",
        bajo_alteracion=bajo_alt or "",
    )


def normalizar_a_americano(nota: str) -> str:
    """Convierte una nota base en cifrado latino a americano (si ya es americano, la devuelve igual)."""
    return LATINO_A_AMERICANO.get(nota, nota)


def formatear_nota(nota_americana_con_alt: str, usar_latino: bool) -> str:
    """Formatea una nota como 'F#' a cifrado americano ('F#') o latino ('Fa#')."""
    if not usar_latino:
        return nota_americana_con_alt
    nota_base = nota_americana_con_alt[0]
    alteracion = nota_americana_con_alt[1:]
    return f"{AMERICANO_A_LATINO[nota_base]}{alteracion}"


def transponer_nota(nota: str, alteracion: str, semitonos: int, usar_latino: bool = False) -> str:
    """
    Desplaza una nota (con su alteración) una cantidad N de semitonos
    dentro de la escala cromática de 12 notas.
    """
    nota_amer = normalizar_a_americano(nota)
    clave = f"{nota_amer}{alteracion}"
    indice_actual = INDICE_POR_NOTA[clave]
    nuevo_indice = (indice_actual + semitonos) % 12
    nueva_nota = ESCALA_CROMATICA[nuevo_indice]
    return formatear_nota(nueva_nota, usar_latino)


def transponer_acorde(acorde: Acorde, semitonos: int, usar_latino: bool = False) -> str:
    """
    Transpone tanto la nota raíz como el bajo (si existe) de un acorde,
    conservando su tipo (m, 7, maj7, sus4, dim, etc.).
    """
    raiz_nueva = transponer_nota(acorde.nota, acorde.alteracion, semitonos, usar_latino)
    resultado = f"{raiz_nueva}{acorde.tipo}"

    if acorde.bajo_nota:
        bajo_nuevo = transponer_nota(
            acorde.bajo_nota, acorde.bajo_alteracion, semitonos, usar_latino
        )
        resultado += f"/{bajo_nuevo}"

    return resultado


def es_linea_de_acordes(linea: str) -> bool:
    """
    Determina si una línea corresponde a acordes o a letra de canción.

    Criterio:
    - Se extraen todos los tokens separados por espacios con ER_TOKEN.
    - Si todos los tokens son acordes válidos -> Es línea de acordes.
    - Si al menos la mitad de los tokens son acordes válidos y el resto tienen
      formato de intento de acorde en mayúscula (ej. 'Hx7' en 'Dsus4 D G Hx7'),
      también se clasifica como línea de acordes para poder reportar y rechazar
      los acordes mal escritos sin confundir la línea con letra.
    """
    tokens = ER_TOKEN.findall(linea)
    if not tokens:
        return False

    acordes_validos = [t for t in tokens if extraer_acorde(t) is not None]
    if len(acordes_validos) == len(tokens):
        return True

    # Caso 2: Al menos la mitad de los tokens son acordes válidos y el resto tienen
    # estructura de cifrado (o hay al menos 2 acordes válidos en la línea)
    todos_parecen_acordes = all(
        ER_CANDIDATO_ACORDE.match(t) or ER_SIMBOLOS_CIFRADO.match(t) for t in tokens
    )
    if len(acordes_validos) >= len(tokens) / 2 and (
        len(acordes_validos) >= 2 or ( len(acordes_validos) >= 1 and todos_parecen_acordes )
    ):
        return True

    # Caso 3: Todos los tokens tienen símbolos inequívocos de cifrado (números, '#' o '/')
    if all(ER_SIMBOLOS_CIFRADO.match(t) for t in tokens):
        return True

    return False
