# TP Final Integrador — Tema 12: Cancioneros con Acordes

**Materia:** Fundamentos Teóricos de Informática (2026)  
**Herramienta principal:** Expresiones Regulares en Python (`re`)

---

## 1. Descripción del Proyecto

Este programa lee un archivo de texto plano en formato **Cancionero** (`.txt` en UTF-8), identifica bloques de canciones, distingue líneas de acordes de líneas de letra mediante **Expresiones Regulares**, valida y desglosa cada acorde en sus componentes musicales (**nota**, **alteración**, **tipo** y **bajo**), rechaza acordes mal escritos sin interrumpir la ejecución y transpone la canción una cantidad `N` de semitonos conservando la alineación exacta de cada acorde sobre su sílaba correspondiente.

Incluye además el **Plus** de conversión entre **cifrado americano** (`A–G`) y **cifrado latino** (`Do, Re, Mi, Fa, Sol, La, Si`).

---

## 2. Estructura del Proyecto

El código está dividido en dos módulos cortos y cohesivos siguiendo el principio de responsabilidad única:

- [`acordes.py`](acordes.py): Contiene las **Expresiones Regulares**, las tablas de escala cromática, el desglose/validación de acordes (`extraer_acorde`), la clasificación de líneas (`es_linea_de_acordes`) y la lógica de transposición/conversión (`transponer_acorde`).
- [`cancionero.py`](cancionero.py): Gestiona el procesamiento de bloques de canciones (`# Título`, `Tono: X`, estrofas), la preservación de alineación de columnas, la generación del reporte y la interfaz por línea de comandos (`argparse`).
- [`cancion.txt`](cancion.txt): Archivo de muestra con casos válidos e inválidos (incluyendo el ejemplo oficial de la cátedra).
- [`requirements.txt`](requirements.txt): Especificación de dependencias del entorno (el proyecto utiliza exclusivamente la librería estándar de Python 3 para garantizar funcionamiento 100% sin conexión).

---

## 3. Entorno Virtual, Instrucciones de Ejecución y Parámetros

### Activación del Entorno Virtual (`.venv`)

En **PowerShell**:

```powershell
.\.venv\Scripts\Activate.ps1
```

En **CMD**:

```cmd
.venv\Scripts\activate.bat
```

_(Si se desea recrear el entorno en otra máquina con Python 3 instalado: `python -m venv .venv` y `pip install -r requirements.txt`)._

### Sintaxis general

```bash
python cancionero.py <archivo_entrada.txt> --semitonos N [--latino] [--salida <archivo_salida.txt>]
```

### Parámetros

| Parámetro       | Descripción                                                                                                  | Ejemplo                  |
| :-------------- | :----------------------------------------------------------------------------------------------------------- | :----------------------- |
| `archivo`       | Ruta al archivo `.txt` del cancionero (UTF-8).                                                               | `cancion.txt`            |
| `--semitonos N` | Número entero de semitonos a transponer (positivo o negativo). Por defecto: `0`.                             | `--semitonos -2`         |
| `--latino`      | _(Opcional - Plus)_ Convierte las notas de salida al cifrado latino (`Do–Si`).                               | `--latino`               |
| `--salida RUTA` | _(Opcional)_ Ruta del archivo `.txt` donde guardar el resultado. Si se omite, genera `<entrada>_salida.txt`. | `--salida resultado.txt` |

### Ejemplos de ejecución

1. **Transponer 2 semitonos hacia abajo (ejemplo de la cátedra):**
   ```bash
   python cancionero.py cancion.txt --semitonos -2
   ```
2. **Transponer 3 semitonos hacia arriba y convertir a cifrado latino:**
   ```bash
   python cancionero.py cancion.txt --semitonos 3 --latino
   ```

---

## 4. Expresiones Regulares Utilizadas

1. **Reconocimiento y desglose de un acorde (`ER_ACORDE` en `acordes.py`):**

   ```regex
   ^((?:Do|Re|Mi|Fa|Sol|La|Si|[A-G]))(#|b)?(maj7|maj9|m7b5|m7|m6|m9|m|sus2|sus4|sus|dim7|dim|aug|add9|7|9|6|5)?(?:/((?:Do|Re|Mi|Fa|Sol|La|Si|[A-G]))(#|b)?)?$
   ```

   - **Grupo 1 (`nota`)**: Nota raíz en cifrado americano (`A-G`) o latino (`Do-Si`).
   - **Grupo 2 (`alteracion`)**: Sostenido (`#`) o bemol (`b`), opcional.
   - **Grupo 3 (`tipo`)**: Cualidad o tensión del acorde (`m`, `7`, `maj7`, `sus4`, `dim`, etc.), opcional.
   - **Grupo 4 (`bajo_nota`)**: Nota del bajo invertido luego de la barra `/`, opcional.
   - **Grupo 5 (`bajo_alteracion`)**: Alteración de la nota del bajo (`#` o `b`), opcional.

2. **Encabezado de canción (`ER_TITULO` en `cancionero.py`):**

   ```regex
   ^\s*#\s+(.+?)\s*$
   ```

   Identifica el inicio de un bloque de canción y extrae su título en el Grupo 1.

3. **Tonalidad opcional (`ER_TONO` en `cancionero.py`):**

   ```regex
   ^\s*Tono:\s*(\S+)\s*$
   ```

   Extrae la tonalidad declarada para luego validarla tanto sintácticamente (con `ER_ACORDE`) como semánticamente (verificando que sea una tonalidad mayor o menor simple, sin bajo invertido ni tensiones).

4. **Extracción posicional de tokens (`ER_TOKEN`):**
   ```regex
   \S+
   ```
   Se utiliza con `re.finditer` para obtener cada token junto con su columna exacta de inicio (`match.start()`), permitiendo mantener cada acorde alineado sobre la sílaba correspondiente tras la transposición.

---

## 5. Ejemplo de Entrada y Salida

### Entrada (`cancion.txt` - Fragmento)

```text
# Canción de ejemplo
Tono: G
G        D/F#      Em
Camino por la costa al sol
C            D7        G
miro el mar y pienso en vos

Am7     Bm     Cmaj7
vuelve la marea otra vez
Dsus4   D       G    Hx7
y se lleva todo lo que sé
```

### Salida (`python cancionero.py cancion.txt --semitonos -2`)

```text
# Canción de ejemplo
Tono: F
F        C/E       Dm
Camino por la costa al sol
A#           C7        F
miro el mar y pienso en vos

Gm7     Am     A#maj7
vuelve la marea otra vez
Csus4   C       F    [?Hx7]
y se lleva todo lo que sé
```

_(Seguido por la tabla de desglose de todos los acordes válidos y el reporte de rechazo de `Hx7` en la línea 11)._
