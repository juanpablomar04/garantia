import threading
from pathlib import Path

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

# Límite de caracteres del contexto de documentos enviado a Claude
MAX_CHARS = 150_000
# Ventana deslizante del historial de conversación (número de mensajes)
MAX_HISTORY = 20


def _build_context(documentos: list[dict], max_chars: int) -> str:
    """Concatena el texto de todos los documentos respetando el límite de caracteres."""
    resultado = ""
    for doc in documentos:
        bloque = f"=== {doc['filename']} ===\n{doc['text']}\n\n"
        if len(resultado) + len(bloque) > max_chars:
            remaining = max_chars - len(resultado)
            if remaining > 100:
                resultado += bloque[:remaining]
            break
        resultado += bloque
    return resultado


class WarrantyAssistant:
    def __init__(self):
        self.pdf_documents: list[dict] = []
        self.conversation_history: list[dict] = []

    @property
    def docs_loaded(self) -> bool:
        return bool(self.pdf_documents)

    def load_all_pdfs(self) -> list[str]:
        """
        Carga todos los PDFs de la carpeta 'docs/'.
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
                f"No se encontraron PDFs en '{docs_folder}'.\n"
                "Copiá los documentos de garantía en esa carpeta y reiniciá el asistente."
            )

        nuevos_docs = []
        cargados = []
        for pdf_path in pdfs:
            try:
                reader = PdfReader(str(pdf_path))
                texto = "".join(page.extract_text() or "" for page in reader.pages)
                if texto.strip():
                    nuevos_docs.append({"filename": pdf_path.name, "text": texto})
                    cargados.append(pdf_path.name)
            except Exception:
                pass  # saltar PDFs ilegibles

        if not cargados:
            raise ValueError(
                "Los PDFs encontrados no contienen texto extraíble. "
                "Pueden estar escaneados como imagen."
            )

        self.pdf_documents = nuevos_docs
        return cargados

    def clear_history(self):
        """Limpia solo el historial de conversación; mantiene los documentos en caché."""
        self.conversation_history = []

    def clear(self):
        """Limpia documentos e historial completos."""
        self.pdf_documents = []
        self.conversation_history = []

    def ask(self, question: str, on_response, on_error):
        """
        Envía una pregunta a Claude. El texto completo de los documentos se coloca en el
        system prompt con cache_control=ephemeral, de modo que la API lo reutiliza entre
        consultas consecutivas y reduce latencia y costo.
        """
        def _run():
            try:
                import anthropic
                client = anthropic.Anthropic()

                full_context = _build_context(self.pdf_documents, MAX_CHARS)

                # El bloque de documentos se marca como cacheable; el system prompt base
                # queda incluido en el mismo breakpoint de caché.
                system = [
                    {"type": "text", "text": SYSTEM_PROMPT},
                    {
                        "type": "text",
                        "text": f"Documentos de garantía cargados:\n\n{full_context}",
                        "cache_control": {"type": "ephemeral"},
                    },
                ]

                self.conversation_history.append({"role": "user", "content": question})
                # Ventana deslizante: solo los últimos MAX_HISTORY mensajes
                messages = self.conversation_history[-MAX_HISTORY:]

                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2048,
                    system=system,
                    messages=messages,
                )

                answer = response.content[0].text
                self.conversation_history.append({"role": "assistant", "content": answer})
                on_response(answer)

            except Exception as e:
                # Revertir el turno fallido para no corromper el historial
                if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                    self.conversation_history.pop()
                on_error(str(e))

        threading.Thread(target=_run, daemon=True).start()
