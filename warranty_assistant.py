import threading
import math
import re
from pathlib import Path
from collections import Counter

SYSTEM_PROMPT = """
Eres un asistente especializado en garantías de vehículos y autopartes, diseñado para ayudar a
agentes de soporte interno a responder consultas de manera precisa y rápida.

## Rol y tono
- Hablar siempre en español, con tono profesional pero claro y directo.
- El usuario es un agente de soporte interno, no un cliente final. Puede manejar terminología técnica.
- Ser conciso: responder la pregunta directamente, luego agregar contexto si es necesario.
- Nunca inventar información. Si algo no está en los documentos, decirlo explícitamente.

## Formato de respuesta
Para cada pregunta usar este formato:

**Respuesta:** [respuesta directa a la pregunta]

**Fuente:** [nombre del documento] — [sección/página si está disponible]

**Condiciones importantes:** [exclusiones, requisitos, plazos u otras condiciones, si aplica]

Si la información no está en ningún documento:
**No encontrado en los documentos provistos.** Esta consulta no está cubierta por los manuales
cargados. Se recomienda escalar o consultar fuente adicional.

## Reglas
- Siempre citar el documento fuente.
- Indicar si una respuesta es incompleta por falta de información.
- Mencionar condiciones o excepciones relevantes.
- Nunca asumir ni inventar coberturas no documentadas.
- Nunca dar asesoramiento legal. Si se requiere, derivar al área legal.
"""

# Límite de caracteres a enviar por consulta (~150k tokens de seguridad)
MAX_CHARS = 150_000
# Tamaño de cada fragmento en caracteres
CHUNK_SIZE = 1_000
# Cuántos fragmentos relevantes incluir
TOP_K = 30


def _tokenizar(texto: str) -> list[str]:
    """Divide el texto en palabras en minúsculas."""
    return re.findall(r'\w+', texto.lower())


def _similitud_tf(fragmento: str, pregunta: str) -> float:
    """
    Calcula similitud simple entre fragmento y pregunta
    usando frecuencia de términos compartidos (TF).
    """
    palabras_pregunta = set(_tokenizar(pregunta))
    palabras_frag = _tokenizar(fragmento)
    if not palabras_frag or not palabras_pregunta:
        return 0.0
    coincidencias = sum(1 for p in palabras_frag if p in palabras_pregunta)
    return coincidencias / math.sqrt(len(palabras_frag))


def _chunker(texto: str, chunk_size: int) -> list[str]:
    """Divide el texto en fragmentos de tamaño aproximado."""
    parrafos = texto.split('\n')
    chunks = []
    actual = ""
    for parrafo in parrafos:
        if len(actual) + len(parrafo) > chunk_size and actual:
            chunks.append(actual.strip())
            actual = parrafo
        else:
            actual += "\n" + parrafo
    if actual.strip():
        chunks.append(actual.strip())
    return chunks


def _recuperar_fragmentos(documentos: list[dict], pregunta: str,
                           top_k: int, max_chars: int) -> str:
    """
    Busca los fragmentos más relevantes de todos los documentos
    y los concatena respetando el límite de caracteres.
    """
    candidatos = []
    for doc in documentos:
        chunks = _chunker(doc["text"], CHUNK_SIZE)
        for chunk in chunks:
            score = _similitud_tf(chunk, pregunta)
            candidatos.append((score, doc["filename"], chunk))

    # Ordenar por relevancia descendente
    candidatos.sort(key=lambda x: x[0], reverse=True)

    resultado = ""
    total_chars = 0
    for score, filename, chunk in candidatos[:top_k]:
        bloque = f"[{filename}]\n{chunk}\n\n"
        if total_chars + len(bloque) > max_chars:
            break
        resultado += bloque
        total_chars += len(bloque)

    return resultado


class WarrantyAssistant:
    def __init__(self):
        self.pdf_documents = []        # lista de {filename, text}
        self.conversation_history = [] # historial del chat

    def load_all_pdfs(self) -> list[str]:
        """
        Carga automáticamente todos los PDFs de la carpeta 'docs/'.
        Retorna lista de nombres de archivos cargados.
        """
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError("Instalá pypdf ejecutando: pip install pypdf")

        docs_folder = Path(__file__).parent / "docs"
        docs_folder.mkdir(exist_ok=True)
        pdfs = list(docs_folder.glob("*.pdf"))

        if not pdfs:
            raise FileNotFoundError(
                f"No se encontraron PDFs en la carpeta '{docs_folder}'.\n"
                "Copiá los documentos de garantía en esa carpeta y reiniciá el asistente."
            )

        cargados = []
        for pdf_path in pdfs:
            reader = PdfReader(str(pdf_path))
            texto = ""
            for page in reader.pages:
                texto += page.extract_text() or ""

            if texto.strip():
                self.pdf_documents.append({
                    "filename": pdf_path.name,
                    "text": texto
                })
                cargados.append(pdf_path.name)

        if not cargados:
            raise ValueError(
                "Los PDFs encontrados no contienen texto extraíble. "
                "Pueden estar escaneados como imagen."
            )

        return cargados

    def clear(self):
        """Limpia documentos e historial."""
        self.pdf_documents = []
        self.conversation_history = []

    def ask(self, question: str, on_response, on_error):
        """
        Envía una pregunta a Claude usando solo los fragmentos
        más relevantes del documento (evita superar el límite de tokens).
        """
        def _run():
            try:
                import anthropic
                client = anthropic.Anthropic()

                # Recuperar solo los fragmentos más relevantes
                contexto = _recuperar_fragmentos(
                    self.pdf_documents, question, TOP_K, MAX_CHARS
                )

                contenido_usuario = (
                    f"Usá exclusivamente los siguientes fragmentos de los documentos "
                    f"de garantía para responder la pregunta:\n\n"
                    f"{contexto}\n\n"
                    f"Pregunta: {question}"
                )

                self.conversation_history.append({
                    "role": "user",
                    "content": contenido_usuario
                })

                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=1500,
                    system=SYSTEM_PROMPT,
                    messages=self.conversation_history
                )

                answer = response.content[0].text

                self.conversation_history.append({
                    "role": "assistant",
                    "content": answer
                })

                on_response(answer)

            except Exception as e:
                on_error(str(e))

        threading.Thread(target=_run, daemon=True).start()
