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

# Carpeta donde se guardan los PDFs de garantía
DOCS_FOLDER = Path(__file__).parent / "docs"


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

        DOCS_FOLDER.mkdir(exist_ok=True)
        pdfs = list(DOCS_FOLDER.glob("*.pdf"))

        if not pdfs:
            raise FileNotFoundError(
                f"No se encontraron PDFs en la carpeta '{DOCS_FOLDER}'.\n"
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
        Envía una pregunta a Claude en un hilo separado.
        on_response(str): callback con la respuesta
        on_error(str):    callback si hay un error
        """
        def _run():
            try:
                import anthropic
                client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY del entorno

                content = []
                for doc in self.pdf_documents:
                    content.append({
                        "type": "text",
                        "text": (
                            f"=== DOCUMENTO: {doc['filename']} ===\n"
                            f"{doc['text']}\n"
                            f"=== FIN DE {doc['filename']} ===\n"
                        )
                    })

                content.append({"type": "text", "text": question})

                self.conversation_history.append({
                    "role": "user",
                    "content": content
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
