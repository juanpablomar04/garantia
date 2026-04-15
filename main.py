import os
from datetime import datetime
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
        self.coll_4 = "faults"

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
        options_menu.add_command(label="4. Ver desvíos",
                                 command=lambda: self.open_viewer(self.coll_4))
        options_menu.add_separator()
        options_menu.add_command(label="Consulta por orden", command=self.open_order_query)
        options_menu.add_command(label="Ingresar desvío", command=self.open_fault_form)
        options_menu.add_separator()
        options_menu.add_command(label="Exit", command=self.root.quit)

        dashboard_menu = tk.Menu(menubar, tearoff=0)
        dashboard_menu.add_command(label="Abrir dashboard", command=self.open_dashboard)

        menubar.add_cascade(label="Inicio", menu=options_menu)
        menubar.add_cascade(label="📊 Dashboard", menu=dashboard_menu)

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
    #  CONSULTA POR ORDEN
    # ──────────────────────────────────────────────
    def open_order_query(self):
        win = tk.Toplevel(self.root)
        win.title("Consulta por Orden")
        win.geometry("950x620")
        win.resizable(True, True)

        # ── Barra de búsqueda ──
        search_frame = tk.Frame(win, pady=8)
        search_frame.pack(fill=tk.X, padx=12)

        tk.Label(search_frame, text="Número de orden:", font=("Arial", 11, "bold")).pack(side=tk.LEFT)

        orden_var = tk.StringVar()
        entrada = tk.Entry(search_frame, textvariable=orden_var, font=("Arial", 11), width=28)
        entrada.pack(side=tk.LEFT, padx=(8, 6), ipady=3)

        btn_buscar = tk.Button(search_frame, text="Buscar 🔍",
                               font=("Arial", 10, "bold"),
                               bg="#1a6eb5", fg="white",
                               relief=tk.FLAT, padx=10)
        btn_buscar.pack(side=tk.LEFT)

        lbl_estado = tk.Label(search_frame, text="", font=("Arial", 9, "italic"), fg="#888888")
        lbl_estado.pack(side=tk.LEFT, padx=(12, 0))

        # ── Notebook con dos pestañas ──
        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

        # Pestaña Órdenes
        frame_orders = tk.Frame(notebook)
        notebook.add(frame_orders, text="  Órdenes  ")

        tree_orders_frame = tk.Frame(frame_orders)
        tree_orders_frame.pack(fill=tk.BOTH, expand=True)

        tree_orders = ttk.Treeview(tree_orders_frame, show='headings')
        vsb_orders = ttk.Scrollbar(tree_orders_frame, orient="vertical", command=tree_orders.yview)
        hsb_orders = ttk.Scrollbar(tree_orders_frame, orient="horizontal", command=tree_orders.xview)
        tree_orders.configure(yscrollcommand=vsb_orders.set, xscrollcommand=hsb_orders.set)
        tree_orders.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_orders.pack(side=tk.RIGHT, fill=tk.Y)
        hsb_orders.pack(side=tk.BOTTOM, fill=tk.X)

        lbl_no_orders = tk.Label(frame_orders, text="", font=("Arial", 10, "italic"), fg="#888888")
        lbl_no_orders.pack(pady=4)

        # Pestaña Piezas
        frame_parts = tk.Frame(notebook)
        notebook.add(frame_parts, text="  Piezas  ")

        tree_parts_frame = tk.Frame(frame_parts)
        tree_parts_frame.pack(fill=tk.BOTH, expand=True)

        tree_parts = ttk.Treeview(tree_parts_frame, show='headings')
        vsb_parts = ttk.Scrollbar(tree_parts_frame, orient="vertical", command=tree_parts.yview)
        hsb_parts = ttk.Scrollbar(tree_parts_frame, orient="horizontal", command=tree_parts.xview)
        tree_parts.configure(yscrollcommand=vsb_parts.set, xscrollcommand=hsb_parts.set)
        tree_parts.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_parts.pack(side=tk.RIGHT, fill=tk.Y)
        hsb_parts.pack(side=tk.BOTTOM, fill=tk.X)

        lbl_no_parts = tk.Label(frame_parts, text="", font=("Arial", 10, "italic"), fg="#888888")
        lbl_no_parts.pack(pady=4)

        # Pestaña Reclamos
        frame_claims = tk.Frame(notebook)
        notebook.add(frame_claims, text="  Reclamos  ")

        tree_claims_frame = tk.Frame(frame_claims)
        tree_claims_frame.pack(fill=tk.BOTH, expand=True)

        tree_claims = ttk.Treeview(tree_claims_frame, show='headings')
        vsb_claims = ttk.Scrollbar(tree_claims_frame, orient="vertical", command=tree_claims.yview)
        hsb_claims = ttk.Scrollbar(tree_claims_frame, orient="horizontal", command=tree_claims.xview)
        tree_claims.configure(yscrollcommand=vsb_claims.set, xscrollcommand=hsb_claims.set)
        tree_claims.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_claims.pack(side=tk.RIGHT, fill=tk.Y)
        hsb_claims.pack(side=tk.BOTTOM, fill=tk.X)

        lbl_no_claims = tk.Label(frame_claims, text="", font=("Arial", 10, "italic"), fg="#888888")
        lbl_no_claims.pack(pady=4)

        # Pestaña Desvíos
        frame_faults = tk.Frame(notebook)
        notebook.add(frame_faults, text="  Desvíos  ")

        tree_faults_frame = tk.Frame(frame_faults)
        tree_faults_frame.pack(fill=tk.BOTH, expand=True)

        tree_faults = ttk.Treeview(tree_faults_frame, show='headings')
        vsb_faults = ttk.Scrollbar(tree_faults_frame, orient="vertical", command=tree_faults.yview)
        hsb_faults = ttk.Scrollbar(tree_faults_frame, orient="horizontal", command=tree_faults.xview)
        tree_faults.configure(yscrollcommand=vsb_faults.set, xscrollcommand=hsb_faults.set)
        tree_faults.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb_faults.pack(side=tk.RIGHT, fill=tk.Y)
        hsb_faults.pack(side=tk.BOTTOM, fill=tk.X)

        lbl_no_faults = tk.Label(frame_faults, text="", font=("Arial", 10, "italic"), fg="#888888")
        lbl_no_faults.pack(pady=4)

        # ── Función auxiliar para poblar un Treeview ──
        def _poblar_tree(tree, docs, lbl_vacio, nombre_col):
            tree.delete(*tree.get_children())
            lbl_vacio.config(text="")

            if not docs:
                lbl_vacio.config(text=f"No se encontraron {nombre_col} para esta orden.")
                tree["columns"] = ()
                return

            exclude = {"_id", "source"}
            columns = [k for k in docs[0].keys() if k not in exclude]
            tree["columns"] = columns

            for col in columns:
                tree.heading(col, text=col.replace("_", " ").upper())
                tree.column(col, width=150, minwidth=80)

            for doc in docs:
                row = []
                for col in columns:
                    val = doc.get(col, "")
                    if col == "scanned_at" and val:
                        val = str(val).split('T')[0].split(' ')[0]
                    row.append(str(val))
                tree.insert("", tk.END, values=row)

        # ── Función auxiliar: construye query buscando en todos los campos string ──
        def _build_query(collection, terms):
            """
            Inspecciona un documento de muestra de la colección para detectar
            qué campos son strings, y arma un $or buscando cada term en todos ellos.
            'terms' puede ser un string o una lista de strings.
            Si no hay documentos o no hay campos string, devuelve None.
            """
            sample = collection.find_one()
            if not sample:
                return None
            exclude = {"_id", "source"}
            str_fields = [
                k for k, v in sample.items()
                if k not in exclude and isinstance(v, str)
            ]
            if not str_fields:
                return None
            if isinstance(terms, str):
                terms = [terms]
            return {"$or": [
                {field: {"$regex": term, "$options": "i"}}
                for field in str_fields
                for term in terms
            ]}

        # ── Función principal de búsqueda ──
        def buscar(event=None):
            numero_orden = orden_var.get().strip()
            if not numero_orden:
                messagebox.showwarning("Campo vacío", "Ingresá un número de orden para buscar.")
                return

            lbl_estado.config(text="Buscando…", fg="#888888")
            btn_buscar.config(state=tk.DISABLED)
            win.update_idletasks()

            try:
                client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                db = client[self.db_name]

                coll_orders = db[self.coll_1]
                coll_parts  = db[self.coll_2]
                coll_claims = db[self.coll_3]
                coll_faults = db[self.coll_4]

                query_orders = _build_query(coll_orders, numero_orden)
                query_parts  = _build_query(coll_parts,  numero_orden)
                query_faults = _build_query(coll_faults, numero_orden)
                # Transformación de prefijo para búsqueda en claims:
                # 20xxxxx → 02xxxxx        (ej: 2012345 → 0212345)
                # 60xxxxx → 26xxxxx        (ej: 6012345 → 2612345)
                # 50xxxxx → 15xxxxx Y 05xxxxx (ej: 5012345 → 1512345 y 0512345)
                if numero_orden.startswith("20"):
                    numero_claims = "2" + numero_orden[2:]
                elif numero_orden.startswith("60"):
                    numero_claims = "26" + numero_orden[2:]
                elif numero_orden.startswith("50"):
                    numero_claims = ["15" + numero_orden[2:], "5" + numero_orden[2:]]
                else:
                    numero_claims = numero_orden
                query_claims = _build_query(coll_claims, numero_claims)

                orders_docs = list(coll_orders.find(query_orders)) if query_orders else []
                parts_docs  = list(coll_parts.find(query_parts))   if query_parts  else []
                claims_docs = list(coll_claims.find(query_claims)) if query_claims else []
                faults_docs = list(coll_faults.find(query_faults)) if query_faults else []

                total = len(orders_docs) + len(parts_docs) + len(claims_docs) + len(faults_docs)
                if total == 0:
                    lbl_estado.config(text=f"Sin resultados para '{numero_orden}'.", fg="#c62828")
                else:
                    lbl_estado.config(
                        text=(f"{len(orders_docs)} orden(es) · "
                              f"{len(parts_docs)} pieza(s) · "
                              f"{len(claims_docs)} reclamo(s) · "
                              f"{len(faults_docs)} desvío(s) encontrados."),
                        fg="#2e7d32"
                    )

                _poblar_tree(tree_orders, orders_docs, lbl_no_orders, "órdenes")
                _poblar_tree(tree_parts,  parts_docs,  lbl_no_parts,  "piezas")
                _poblar_tree(tree_claims, claims_docs, lbl_no_claims, "reclamos")
                _poblar_tree(tree_faults, faults_docs, lbl_no_faults, "desvíos")

                # Ir a la pestaña con resultados (prioriza órdenes)
                if orders_docs:
                    notebook.select(frame_orders)
                elif parts_docs:
                    notebook.select(frame_parts)
                elif claims_docs:
                    notebook.select(frame_claims)
                elif faults_docs:
                    notebook.select(frame_faults)

            except Exception as e:
                lbl_estado.config(text="Error de conexión.", fg="#c62828")
                messagebox.showerror("Error", f"No se pudo conectar a la base de datos:\n{e}")
            finally:
                btn_buscar.config(state=tk.NORMAL)

        btn_buscar.config(command=buscar)
        entrada.bind("<Return>", buscar)
        entrada.focus()

    # ──────────────────────────────────────────────
    #  INGRESAR DESVÍO
    # ──────────────────────────────────────────────
    def open_fault_form(self):
        win = tk.Toplevel(self.root)
        win.title("Ingresar Desvío")
        win.geometry("480x380")
        win.resizable(False, False)

        DESVIOS = [
            "Faltó revalidar",
            "Sin Diss",
            "Sin material",
            "Material incorrecto",
            "Vale sin firma/s",
        ]

        pad = {"padx": 16, "pady": (6, 0)}

        # ── Orden ──
        tk.Label(win, text="Orden *", font=("Arial", 10, "bold"), anchor="w").pack(fill=tk.X, **pad)
        orden_var = tk.StringVar()
        tk.Entry(win, textvariable=orden_var, font=("Arial", 11)).pack(fill=tk.X, padx=16, ipady=3)

        # ── Desvío ──
        tk.Label(win, text="Desvío *", font=("Arial", 10, "bold"), anchor="w").pack(fill=tk.X, **pad)
        desvio_var = tk.StringVar(value=DESVIOS[0])
        ttk.Combobox(
            win, textvariable=desvio_var,
            values=DESVIOS, state="readonly",
            font=("Arial", 11)
        ).pack(fill=tk.X, padx=16, ipady=3)

        # ── Comentario ──
        tk.Label(win, text="Comentario", font=("Arial", 10, "bold"), anchor="w").pack(fill=tk.X, **pad)
        comentario_txt = tk.Text(win, font=("Arial", 11), height=5, relief=tk.SUNKEN)
        comentario_txt.pack(fill=tk.X, padx=16, pady=(0, 4))

        # ── Feedback y botón ──
        lbl_feedback = tk.Label(win, text="", font=("Arial", 9, "italic"))
        lbl_feedback.pack(pady=(2, 0))

        def guardar():
            orden = orden_var.get().strip()
            desvio = desvio_var.get().strip()
            comentario = comentario_txt.get("1.0", tk.END).strip()

            if not orden:
                messagebox.showwarning("Campo requerido", "El campo Orden es obligatorio.", parent=win)
                return
            if not desvio:
                messagebox.showwarning("Campo requerido", "Seleccioná un Desvío.", parent=win)
                return

            doc = {
                "orden": orden,
                "desvio": desvio,
                "comentario": comentario,
                "fecha": datetime.now(),
            }

            try:
                client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=2000)
                db = client[self.db_name]
                db[self.coll_4].insert_one(doc)
                lbl_feedback.config(text="✔ Desvío guardado correctamente.", fg="#2e7d32")
                orden_var.set("")
                desvio_var.set(DESVIOS[0])
                comentario_txt.delete("1.0", tk.END)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar:\n{e}", parent=win)

        tk.Button(
            win, text="Guardar desvío",
            font=("Arial", 10, "bold"),
            bg="#1a6eb5", fg="white",
            relief=tk.FLAT, padx=12, pady=4,
            command=guardar
        ).pack(pady=(4, 0))

    # ──────────────────────────────────────────────
    #  DASHBOARD MONGODB CHARTS
    # ──────────────────────────────────────────────
    def open_dashboard(self):
        import subprocess, sys
        from pathlib import Path

        viewer = Path(__file__).parent / "dashboard_viewer.py"
        if not viewer.exists():
            messagebox.showerror(
                "Archivo faltante",
                f"No se encontró dashboard_viewer.py en:\n{viewer}"
            )
            return

        subprocess.Popen(
            [sys.executable, str(viewer)],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

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
