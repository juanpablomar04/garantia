import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pymongo import MongoClient
from warranty_assistant import WarrantyAssistant
from dotenv import load_dotenv

load_dotenv()  # carga las variables del archivo .env


class MongoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Administración de Garantía")
        self.root.geometry("1000x600")

        # --- CONFIGURATION ---
        self.mongo_uri = os.getenv("MONGO_URI")
        self.db_name = "work"
        self.coll_1 = "orders"
        self.coll_2 = "parts"
        self.coll_3 = "claims"

        # --- Asistente de garantía ---
        self.assistant = WarrantyAssistant()

        self.setup_menu()

        self.main_label = tk.Label(root, text="Seleccionar una opción de Inicio", font=("Arial", 14))
        self.main_label.pack(expand=True)

    def setup_menu(self):
        menubar = tk.Menu(self.root)

        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="1. Ver órdenes",
                                 command=lambda: self.open_viewer(self.coll_1))
        options_menu.add_command(label="2. Ver piezas",
                                 command=lambda: self.open_viewer(self.coll_2))
        options_menu.add_command(label="3. Ver acreditaciones",
                                 command=lambda: self.open_viewer(self.coll_3))
        options_menu.add_separator()
        options_menu.add_command(label="Exit", command=self.root.quit)

        asistente_menu = tk.Menu(menubar, tearoff=0)
        asistente_menu.add_command(label="Abrir asistente", command=self.open_warranty_assistant)

        menubar.add_cascade(label="Inicio", menu=options_menu)
        menubar.add_cascade(label="🤖 Asistente IA", menu=asistente_menu)

        self.root.config(menu=menubar)

    # ──────────────────────────────────────────────
    #  VISOR DE COLECCIONES (sin cambios)
    # ──────────────────────────────────────────────
    def open_viewer(self, collection_name):
        try:
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
            db = client[self.db_name]
            coll = db[collection_name]

            raw_docs = list(coll.find())
            if not raw_docs:
                messagebox.showwarning("Empty", f"Collection '{collection_name}' is empty.")
                return

            exclude = ["_id", "source"]
            columns = [k for k in raw_docs[0].keys() if k not in exclude]

            processed_data = []
            for doc in raw_docs:
                row = []
                for col in columns:
                    val = doc.get(col, "")
                    if col == "scanned_at" and val:
                        val = str(val).split('T')[0].split(' ')[0]
                    row.append(str(val))
                processed_data.append(row)

            view_win = tk.Toplevel(self.root)
            view_win.title(f"Viewer: {collection_name}")
            view_win.geometry("900x500")

            filter_frame = tk.Frame(view_win)
            filter_frame.pack(fill=tk.X, padx=10, pady=5)

            filter_vars = {}

            tree_frame = tk.Frame(view_win)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
            vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)

            def apply_filters(*args):
                for item in tree.get_children():
                    tree.delete(item)
                for row in processed_data:
                    match = True
                    for i, col in enumerate(columns):
                        f_val = filter_vars[col].get().lower()
                        if f_val and f_val not in row[i].lower():
                            match = False
                            break
                    if match:
                        tree.insert("", tk.END, values=row)

            for i, col in enumerate(columns):
                tree.heading(col, text=col.replace("_", " ").upper())
                tree.column(col, width=140)

                lbl = tk.Label(filter_frame, text=col, font=("Arial", 8, "bold"))
                lbl.grid(row=0, column=i, padx=5, sticky='w')

                v = tk.StringVar()
                v.trace_add("write", apply_filters)
                ent = tk.Entry(filter_frame, textvariable=v, width=15)
                ent.grid(row=1, column=i, padx=5, pady=2)
                filter_vars[col] = v

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)

            apply_filters()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load collection: {e}")

    # ──────────────────────────────────────────────
    #  ASISTENTE DE GARANTÍA
    # ──────────────────────────────────────────────
    def open_warranty_assistant(self):
        win = tk.Toplevel(self.root)
        win.title("Asistente de Garantía — IA")
        win.geometry("800x580")
        win.resizable(True, True)

        # Limpiar historial al abrir
        self.assistant.clear()

        # ── Área de chat ──
        tk.Label(win, text="Consultas al asistente", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 2))

        chat_area = scrolledtext.ScrolledText(
            win, state=tk.DISABLED, wrap=tk.WORD,
            font=("Arial", 10), bg="#fafafa", relief=tk.SUNKEN
        )
        chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        # Tags de color
        chat_area.tag_config("sistema", foreground="#888888", font=("Arial", 9, "italic"))
        chat_area.tag_config("agente_label", foreground="#1a6eb5", font=("Arial", 10, "bold"))
        chat_area.tag_config("agente_text", foreground="#1a1a1a", font=("Arial", 10))
        chat_area.tag_config("asistente_label", foreground="#2e7d32", font=("Arial", 10, "bold"))
        chat_area.tag_config("asistente_text", foreground="#1a1a1a", font=("Arial", 10))
        chat_area.tag_config("error_label", foreground="#c62828", font=("Arial", 10, "bold"))
        chat_area.tag_config("separador", foreground="#cccccc")

        # ── Barra de entrada ──
        entry_frame = tk.Frame(win)
        entry_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        entrada = tk.Entry(entry_frame, font=("Arial", 11))
        entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        btn_enviar = tk.Button(entry_frame, text="Consultar ▶",
                               font=("Arial", 10, "bold"),
                               bg="#2e7d32", fg="white",
                               relief=tk.FLAT, padx=10)
        btn_enviar.pack(side=tk.RIGHT, padx=(6, 0))

        # ── Funciones del chat ──
        def agregar_mensaje(remitente, texto):
            chat_area.config(state=tk.NORMAL)
            if remitente == "Sistema":
                chat_area.insert(tk.END, f"ℹ {texto}\n", "sistema")
            elif remitente == "Agente":
                chat_area.insert(tk.END, "Agente: ", "agente_label")
                chat_area.insert(tk.END, f"{texto}\n", "agente_text")
            elif remitente == "Asistente":
                chat_area.insert(tk.END, "Asistente: ", "asistente_label")
                chat_area.insert(tk.END, f"{texto}\n", "asistente_text")
            elif remitente == "Error":
                chat_area.insert(tk.END, "⚠ Error: ", "error_label")
                chat_area.insert(tk.END, f"{texto}\n", "agente_text")
            chat_area.insert(tk.END, "─" * 60 + "\n", "separador")
            chat_area.see(tk.END)
            chat_area.config(state=tk.DISABLED)

        def borrar_ultimo_mensaje():
            chat_area.config(state=tk.NORMAL)
            chat_area.delete("end-3l", tk.END)
            chat_area.config(state=tk.DISABLED)

        def mostrar_respuesta(respuesta):
            borrar_ultimo_mensaje()
            agregar_mensaje("Asistente", respuesta)
            btn_enviar.config(state=tk.NORMAL)
            entrada.config(state=tk.NORMAL)
            entrada.focus()

        def mostrar_error(error):
            borrar_ultimo_mensaje()
            agregar_mensaje("Error", error)
            btn_enviar.config(state=tk.NORMAL)
            entrada.config(state=tk.NORMAL)

        def enviar_pregunta(event=None):
            pregunta = entrada.get().strip()
            if not pregunta:
                return
            agregar_mensaje("Agente", pregunta)
            entrada.delete(0, tk.END)
            btn_enviar.config(state=tk.DISABLED)
            entrada.config(state=tk.DISABLED)
            agregar_mensaje("Asistente", "Consultando documentos…")

            self.assistant.ask(
                question=pregunta,
                on_response=lambda r: win.after(0, mostrar_respuesta, r),
                on_error=lambda e: win.after(0, mostrar_error, e)
            )

        btn_enviar.config(command=enviar_pregunta)
        entrada.bind("<Return>", enviar_pregunta)

        # ── Cargar PDFs automáticamente al abrir ──
        def cargar_docs():
            try:
                cargados = self.assistant.load_all_pdfs()
                nombres = ", ".join(cargados)
                agregar_mensaje("Sistema", f"Documentos cargados: {nombres}")
                agregar_mensaje("Sistema", "Listo para responder consultas.")
                entrada.focus()
            except Exception as e:
                agregar_mensaje("Error", str(e))
                btn_enviar.config(state=tk.DISABLED)
                entrada.config(state=tk.DISABLED)

        win.after(100, cargar_docs)


if __name__ == "__main__":
    root = tk.Tk()
    app = MongoApp(root)
    root.mainloop()
