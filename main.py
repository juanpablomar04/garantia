import os
import csv
import logging
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pymongo import MongoClient
from warranty_assistant import WarrantyAssistant
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

DATE_COL_NAMES = {"fecha", "date", "fecha_alta", "created_at", "scanned_at"}


class MongoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Administración de Garantía")
        self.root.geometry("1000x620")

        self.mongo_uri = os.getenv("MONGO_URI")
        self.db_name = "work"
        self.coll_1 = "orders"
        self.coll_2 = "parts"
        self.coll_3 = "claims"
        self.coll_4 = "faults"
        self.coll_5 = "debts"

        self._client = None
        self.assistant = WarrantyAssistant()

        self.setup_menu()
        self._setup_status_bar()   # primero el status bar (queda abajo)
        self._setup_home()         # luego el contenido principal

    # ──────────────────────────────────────────────
    #  CONEXIÓN MONGODB
    # ──────────────────────────────────────────────
    def _get_db(self):
        if not self.mongo_uri:
            raise ValueError("MONGO_URI no está configurada. Verificá el archivo .env.")
        if self._client is None:
            self._client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
        return self._client[self.db_name]

    # ──────────────────────────────────────────────
    #  PANTALLA DE INICIO
    # ──────────────────────────────────────────────
    def _setup_home(self):
        home = tk.Frame(self.root, bg="#ffffff")
        home.pack(fill=tk.BOTH, expand=True)

        tk.Label(home, text="Administración de Garantía",
                 font=("Arial", 17, "bold"), bg="#ffffff", fg="#1a1a1a").pack(pady=(28, 4))
        tk.Label(home, text="Seleccioná una acción para comenzar",
                 font=("Arial", 10), bg="#ffffff", fg="#999999").pack(pady=(0, 22))

        grid = tk.Frame(home, bg="#ffffff")
        grid.pack()

        buttons = [
            ("📋  Ver órdenes",         lambda: self.open_viewer(self.coll_1), "#e3f2fd", "#1565c0"),
            ("🔩  Ver piezas",          lambda: self.open_viewer(self.coll_2), "#e3f2fd", "#1565c0"),
            ("✅  Ver acreditaciones",   lambda: self.open_viewer(self.coll_3), "#e3f2fd", "#1565c0"),
            ("⚠  Ver desvíos",          lambda: self.open_viewer(self.coll_4), "#fff3e0", "#e65100"),
            ("💰  Ver débitos",         self.open_debts_viewer,                "#fff3e0", "#e65100"),
            ("🔍  Consulta por orden",  self.open_order_query,                 "#f3e5f5", "#6a1b9a"),
            ("🤖  Asistente IA",        self.open_warranty_assistant,          "#e8f5e9", "#2e7d32"),
            ("📊  Dashboard",           self.open_dashboard,                   "#fce4ec", "#880e4f"),
        ]

        for idx, (label, cmd, bg, fg) in enumerate(buttons):
            row, col = divmod(idx, 4)
            btn = tk.Button(grid, text=label, command=cmd,
                            font=("Arial", 10), bg=bg, fg=fg,
                            relief=tk.FLAT, width=20, pady=14,
                            cursor="hand2", activebackground=bg)
            btn.grid(row=row, column=col, padx=8, pady=8)

    # ──────────────────────────────────────────────
    #  BARRA DE ESTADO
    # ──────────────────────────────────────────────
    def _setup_status_bar(self):
        bar = tk.Frame(self.root, bg="#2c2c2c", height=26)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        bar.pack_propagate(False)

        self._lbl_db = tk.Label(bar, text="⬤  Verificando conexión…",
                                font=("Arial", 8), bg="#2c2c2c", fg="#aaaaaa")
        self._lbl_db.pack(side=tk.LEFT, padx=10)

        self._lbl_clock = tk.Label(bar, text="",
                                   font=("Arial", 8), bg="#2c2c2c", fg="#aaaaaa")
        self._lbl_clock.pack(side=tk.RIGHT, padx=10)

        self._tick_clock()
        self.root.after(300, self._ping_db)

    def _tick_clock(self):
        self._lbl_clock.config(text=datetime.now().strftime("%d/%m/%Y   %H:%M:%S"))
        self.root.after(1000, self._tick_clock)

    def _ping_db(self):
        def _run():
            try:
                self._get_db().command("ping")
                self.root.after(0, lambda: self._lbl_db.config(
                    text="⬤  MongoDB conectado", fg="#66bb6a"))
            except Exception:
                self.root.after(0, lambda: self._lbl_db.config(
                    text="⬤  Sin conexión a MongoDB", fg="#ef5350"))
        threading.Thread(target=_run, daemon=True).start()

    # ──────────────────────────────────────────────
    #  MENÚ
    # ──────────────────────────────────────────────
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
        options_menu.add_command(label="5. Ver débitos",
                                 command=self.open_debts_viewer)
        options_menu.add_separator()
        options_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Ingresar desvío", command=self.open_fault_form)
        edit_menu.add_command(label="Ingresar débito", command=self.open_debt_form)

        queries_menu = tk.Menu(menubar, tearoff=0)
        queries_menu.add_command(label="Consulta por orden", command=self.open_order_query)

        dashboard_menu = tk.Menu(menubar, tearoff=0)
        dashboard_menu.add_command(label="Abrir dashboard", command=self.open_dashboard)

        assistant_menu = tk.Menu(menubar, tearoff=0)
        assistant_menu.add_command(label="Abrir asistente IA",
                                   command=self.open_warranty_assistant)

        menubar.add_cascade(label="Inicio", menu=options_menu)
        menubar.add_cascade(label="Editar", menu=edit_menu)
        menubar.add_cascade(label="Consultas", menu=queries_menu)
        menubar.add_cascade(label="📊 Dashboard", menu=dashboard_menu)
        menubar.add_cascade(label="🤖 Asistente", menu=assistant_menu)

        self.root.config(menu=menubar)

    # ──────────────────────────────────────────────
    #  UTILIDADES
    # ──────────────────────────────────────────────
    def _fmt_val(self, col: str, val) -> str:
        if col in DATE_COL_NAMES and val:
            try:
                if hasattr(val, "strftime"):
                    return val.strftime("%Y-%m-%d")
                return str(val).split("T")[0].split(" ")[0]
            except Exception:
                pass
        return str(val) if val is not None else ""

    # ──────────────────────────────────────────────
    #  VISOR UNIFICADO DE COLECCIONES
    # ──────────────────────────────────────────────
    def open_viewer(self, collection_name, title=None, query=None):
        try:
            db = self._get_db()
            coll = db[collection_name]
            raw_docs = list(coll.find(query or {}, limit=2000))
            if not raw_docs:
                messagebox.showwarning("Sin datos", f"No hay registros en '{collection_name}'.")
                return

            exclude = {"_id", "source"}
            columns = [k for k in raw_docs[0].keys() if k not in exclude]
            processed_data = [
                [self._fmt_val(col, doc.get(col, "")) for col in columns]
                for doc in raw_docs
            ]

            logger.info("Viewer '%s': %d docs.", collection_name, len(raw_docs))

            view_win = tk.Toplevel(self.root)
            view_win.title(title or f"Viewer: {collection_name}")
            view_win.geometry("950x560")

            # ── Toolbar ──
            toolbar = tk.Frame(view_win, bg="#f5f5f5", pady=4)
            toolbar.pack(fill=tk.X, padx=10)

            lbl_count = tk.Label(toolbar, text=f"{len(processed_data)} registros",
                                 font=("Arial", 9), bg="#f5f5f5", fg="#555")
            lbl_count.pack(side=tk.LEFT)

            # ── Filtros ──
            filter_frame = tk.Frame(view_win)
            filter_frame.pack(fill=tk.X, padx=10, pady=(4, 0))

            filter_vars: dict[str, tk.StringVar] = {}
            _debounce = [None]
            _sort_state: dict[str, bool] = {}  # col -> True=asc

            # ── Treeview ──
            tree_frame = tk.Frame(view_win)
            tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
            vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

            # ── Filtrado con debounce ──
            def apply_filters():
                for item in tree.get_children():
                    tree.delete(item)
                shown = 0
                for row in processed_data:
                    if all(
                        not filter_vars[c].get() or
                        filter_vars[c].get().lower() in row[i].lower()
                        for i, c in enumerate(columns)
                    ):
                        tree.insert("", tk.END, values=row)
                        shown += 1
                lbl_count.config(text=f"{shown} / {len(processed_data)} registros")

            def schedule_filter(*_):
                if _debounce[0]:
                    view_win.after_cancel(_debounce[0])
                _debounce[0] = view_win.after(300, apply_filters)

            # ── Ordenamiento por columna ──
            def sort_by(col):
                asc = not _sort_state.get(col, True)
                _sort_state[col] = asc
                col_idx = columns.index(col)

                def sort_key(iid):
                    val = tree.set(iid, col)
                    try:
                        return (0, float(val.replace(",", ".")))
                    except (ValueError, AttributeError):
                        return (1, val.lower())

                items = sorted(tree.get_children(""), key=sort_key, reverse=not asc)
                for i, iid in enumerate(items):
                    tree.move(iid, "", i)

                # Actualizar flechas en headers
                for c in columns:
                    tree.heading(c, text=c.replace("_", " ").upper(),
                                 command=lambda x=c: sort_by(x))
                arrow = " ▲" if asc else " ▼"
                tree.heading(col, text=col.replace("_", " ").upper() + arrow,
                             command=lambda x=col: sort_by(x))

            # ── Vista de detalle (doble click) ──
            def show_detail(event):
                sel = tree.selection()
                if not sel:
                    return
                values = tree.item(sel[0], "values")

                detail = tk.Toplevel(view_win)
                detail.title("Detalle del registro")
                detail.geometry("440x420")
                detail.resizable(True, True)

                container = tk.Frame(detail)
                container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

                canvas = tk.Canvas(container, highlightthickness=0)
                sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
                inner = tk.Frame(canvas, bg="#ffffff")

                inner.bind("<Configure>",
                           lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                canvas.create_window((0, 0), window=inner, anchor="nw")
                canvas.configure(yscrollcommand=sb.set)

                for i, (col, val) in enumerate(zip(columns, values)):
                    bg = "#f4f4f4" if i % 2 == 0 else "#ffffff"
                    row_f = tk.Frame(inner, bg=bg)
                    row_f.pack(fill=tk.X, padx=4, pady=1)
                    tk.Label(row_f, text=col.replace("_", " ").upper() + ":",
                             font=("Arial", 9, "bold"), bg=bg,
                             width=20, anchor="w").pack(side=tk.LEFT, padx=(4, 8))
                    tk.Label(row_f, text=val, font=("Arial", 9), bg=bg,
                             anchor="w", wraplength=260, justify=tk.LEFT).pack(
                                 side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

                sb.pack(side=tk.RIGHT, fill=tk.Y)
                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            tree.bind("<Double-1>", show_detail)

            # ── Exportar CSV ──
            def export_csv():
                path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[("CSV", "*.csv")],
                    title="Exportar como CSV",
                    parent=view_win,
                )
                if not path:
                    return
                rows = [tree.item(c, "values") for c in tree.get_children()]
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(rows)
                logger.info("CSV exportado: %s (%d filas)", path, len(rows))
                messagebox.showinfo("Exportado", f"Exportado a:\n{path}", parent=view_win)

            tk.Button(toolbar, text="Exportar CSV ⬇", font=("Arial", 9),
                      command=export_csv, relief=tk.FLAT,
                      bg="#e8f5e9", fg="#2e7d32", padx=8).pack(side=tk.RIGHT)
            tk.Label(toolbar, text="Doble click en una fila para ver detalle",
                     font=("Arial", 8, "italic"), bg="#f5f5f5", fg="#aaa").pack(side=tk.RIGHT, padx=10)

            # ── Configurar columnas y filtros ──
            for i, col in enumerate(columns):
                tree.heading(col, text=col.replace("_", " ").upper(),
                             command=lambda c=col: sort_by(c))
                tree.column(col, width=140, minwidth=60)

                tk.Label(filter_frame, text=col, font=("Arial", 8, "bold")).grid(
                    row=0, column=i, padx=4, sticky="w"
                )
                v = tk.StringVar()
                v.trace_add("write", schedule_filter)
                tk.Entry(filter_frame, textvariable=v, width=14).grid(
                    row=1, column=i, padx=4, pady=2
                )
                filter_vars[col] = v

            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            apply_filters()

        except Exception as e:
            logger.error("Viewer error '%s': %s", collection_name, e)
            messagebox.showerror("Error", f"No se pudo cargar la colección:\n{e}")

    def open_debts_viewer(self):
        self.open_viewer(
            self.coll_5,
            title="Ver débitos (desde 2026)",
            query={"fecha": {"$gte": datetime(2026, 1, 1)}},
        )

    # ──────────────────────────────────────────────
    #  CONSULTA POR ORDEN
    # ──────────────────────────────────────────────
    def open_order_query(self):
        win = tk.Toplevel(self.root)
        win.title("Consulta por Orden")
        win.geometry("950x620")
        win.resizable(True, True)

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

        notebook = ttk.Notebook(win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))

        def make_tab(label):
            frame = tk.Frame(notebook)
            notebook.add(frame, text=f"  {label}  ")
            tf = tk.Frame(frame)
            tf.pack(fill=tk.BOTH, expand=True)
            t = ttk.Treeview(tf, show="headings")
            vsb = ttk.Scrollbar(tf, orient="vertical", command=t.yview)
            hsb = ttk.Scrollbar(tf, orient="horizontal", command=t.xview)
            t.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            vsb.pack(side=tk.RIGHT, fill=tk.Y)
            hsb.pack(side=tk.BOTTOM, fill=tk.X)
            t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            lbl = tk.Label(frame, text="", font=("Arial", 10, "italic"), fg="#888888")
            lbl.pack(pady=4)
            return frame, t, lbl

        frame_orders, tree_orders, lbl_no_orders = make_tab("Órdenes")
        frame_parts,  tree_parts,  lbl_no_parts  = make_tab("Piezas")
        frame_claims, tree_claims, lbl_no_claims = make_tab("Reclamos")
        frame_faults, tree_faults, lbl_no_faults = make_tab("Desvíos")

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
                row = [self._fmt_val(col, doc.get(col, "")) for col in columns]
                tree.insert("", tk.END, values=row)

        def _build_query(collection, terms):
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

        def buscar(event=None):
            numero_orden = orden_var.get().strip()
            if not numero_orden:
                messagebox.showwarning("Campo vacío", "Ingresá un número de orden para buscar.")
                return

            lbl_estado.config(text="Buscando…", fg="#888888")
            btn_buscar.config(state=tk.DISABLED)
            win.update_idletasks()

            try:
                db = self._get_db()

                coll_orders = db[self.coll_1]
                coll_parts  = db[self.coll_2]
                coll_claims = db[self.coll_3]
                coll_faults = db[self.coll_4]

                query_orders = _build_query(coll_orders, numero_orden)
                query_parts  = _build_query(coll_parts,  numero_orden)
                query_faults = _build_query(coll_faults, numero_orden)

                # Transformación de prefijo para búsqueda en claims:
                # 20xxxxx → 2xxxxx  |  60xxxxx → 26xxxxx  |  50xxxxx → 15xxxxx y 5xxxxx
                if numero_orden.startswith("20"):
                    numero_claims = "2" + numero_orden[2:]
                elif numero_orden.startswith("60"):
                    numero_claims = "26" + numero_orden[2:]
                elif numero_orden.startswith("50"):
                    numero_claims = ["15" + numero_orden[2:], "5" + numero_orden[2:]]
                else:
                    numero_claims = numero_orden
                query_claims = _build_query(coll_claims, numero_claims)

                orders_docs = list(coll_orders.find(query_orders, limit=1000)) if query_orders else []
                parts_docs  = list(coll_parts.find(query_parts,   limit=1000)) if query_parts  else []
                claims_docs = list(coll_claims.find(query_claims,  limit=1000)) if query_claims else []
                faults_docs = list(coll_faults.find(query_faults,  limit=1000)) if query_faults else []

                total = len(orders_docs) + len(parts_docs) + len(claims_docs) + len(faults_docs)
                if total == 0:
                    lbl_estado.config(text=f"Sin resultados para '{numero_orden}'.", fg="#c62828")
                else:
                    lbl_estado.config(
                        text=(f"{len(orders_docs)} orden(es) · "
                              f"{len(parts_docs)} pieza(s) · "
                              f"{len(claims_docs)} reclamo(s) · "
                              f"{len(faults_docs)} desvío(s) encontrados."),
                        fg="#2e7d32",
                    )

                _poblar_tree(tree_orders, orders_docs, lbl_no_orders, "órdenes")
                _poblar_tree(tree_parts,  parts_docs,  lbl_no_parts,  "piezas")
                _poblar_tree(tree_claims, claims_docs, lbl_no_claims, "reclamos")
                _poblar_tree(tree_faults, faults_docs, lbl_no_faults, "desvíos")

                if orders_docs:
                    notebook.select(frame_orders)
                elif parts_docs:
                    notebook.select(frame_parts)
                elif claims_docs:
                    notebook.select(frame_claims)
                elif faults_docs:
                    notebook.select(frame_faults)

            except Exception as e:
                logger.error("Consulta por orden error: %s", e)
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

        tk.Label(win, text="Orden *", font=("Arial", 10, "bold"), anchor="w").pack(fill=tk.X, **pad)
        orden_var = tk.StringVar()
        tk.Entry(win, textvariable=orden_var, font=("Arial", 11)).pack(fill=tk.X, padx=16, ipady=3)

        tk.Label(win, text="Desvío *", font=("Arial", 10, "bold"), anchor="w").pack(fill=tk.X, **pad)
        desvio_var = tk.StringVar(value=DESVIOS[0])
        ttk.Combobox(win, textvariable=desvio_var, values=DESVIOS, state="readonly",
                     font=("Arial", 11)).pack(fill=tk.X, padx=16, ipady=3)

        tk.Label(win, text="Comentario", font=("Arial", 10, "bold"), anchor="w").pack(fill=tk.X, **pad)
        comentario_txt = tk.Text(win, font=("Arial", 11), height=5, relief=tk.SUNKEN)
        comentario_txt.pack(fill=tk.X, padx=16, pady=(0, 4))

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
                db = self._get_db()
                db[self.coll_4].insert_one(doc)
                logger.info("Desvío guardado: orden=%s desvío=%s", orden, desvio)
                lbl_feedback.config(text="✔ Desvío guardado correctamente.", fg="#2e7d32")
                orden_var.set("")
                desvio_var.set(DESVIOS[0])
                comentario_txt.delete("1.0", tk.END)
            except Exception as e:
                logger.error("Error al guardar desvío: %s", e)
                messagebox.showerror("Error", f"No se pudo guardar:\n{e}", parent=win)

        tk.Button(win, text="Guardar desvío", font=("Arial", 10, "bold"),
                  bg="#1a6eb5", fg="white", relief=tk.FLAT, padx=12, pady=4,
                  command=guardar).pack(pady=(4, 0))

    # ──────────────────────────────────────────────
    #  INGRESAR DÉBITO
    # ──────────────────────────────────────────────
    def open_debt_form(self):
        from decimal import Decimal, InvalidOperation
        from bson.decimal128 import Decimal128

        win = tk.Toplevel(self.root)
        win.title("Ingresar Débito")
        win.geometry("520x580")
        win.resizable(False, False)

        pad = {"padx": 16, "pady": (5, 0)}

        def make_label(text):
            tk.Label(win, text=text, font=("Arial", 10, "bold"), anchor="w").pack(fill=tk.X, **pad)

        def make_entry(var):
            tk.Entry(win, textvariable=var, font=("Arial", 11)).pack(fill=tk.X, padx=16, ipady=2)
            return var

        make_label("Orden *")
        orden_var = make_entry(tk.StringVar())

        make_label("Reparación")
        reparacion_var = make_entry(tk.StringVar())

        make_label("Motivo")
        motivo_var = make_entry(tk.StringVar())

        dec_frame = tk.Frame(win)
        dec_frame.pack(fill=tk.X, padx=16, pady=(5, 0))

        decimal_vars: dict[str, tk.StringVar] = {}
        decimal_fields = [("MO", "MO e"), ("Material", "Material e")]

        for row_idx, (left, right) in enumerate(decimal_fields):
            for col_idx, field in enumerate([left, right]):
                tk.Label(dec_frame, text=field, font=("Arial", 10, "bold"), anchor="w").grid(
                    row=row_idx * 2, column=col_idx,
                    padx=(0 if col_idx == 0 else 10, 0), sticky="w",
                )
                v = tk.StringVar()
                v.trace_add("write", lambda *_: actualizar_total())
                tk.Entry(dec_frame, textvariable=v, font=("Arial", 11), width=18).grid(
                    row=row_idx * 2 + 1, column=col_idx,
                    padx=(0 if col_idx == 0 else 10, 0), sticky="ew", ipady=2,
                )
                decimal_vars[field] = v
        dec_frame.columnconfigure(0, weight=1)
        dec_frame.columnconfigure(1, weight=1)

        total_frame = tk.Frame(win)
        total_frame.pack(fill=tk.X, padx=16, pady=(6, 0))
        tk.Label(total_frame, text="Total", font=("Arial", 10, "bold"), anchor="w").pack(side=tk.LEFT)
        lbl_total = tk.Label(total_frame, text="0.00", font=("Arial", 11), fg="#1a6eb5", anchor="w")
        lbl_total.pack(side=tk.LEFT, padx=(8, 0))

        def actualizar_total():
            total = Decimal("0")
            for v in decimal_vars.values():
                raw = v.get().strip().replace(",", ".")
                try:
                    total += Decimal(raw) if raw else Decimal("0")
                except InvalidOperation:
                    pass
            lbl_total.config(text=str(total.quantize(Decimal("0.01"))))

        make_label("Observación")
        obs_txt = tk.Text(win, font=("Arial", 11), height=3, relief=tk.SUNKEN)
        obs_txt.pack(fill=tk.X, padx=16, pady=(0, 4))

        lbl_feedback = tk.Label(win, text="", font=("Arial", 9, "italic"))
        lbl_feedback.pack(pady=(2, 0))

        def guardar():
            orden = orden_var.get().strip()
            if not orden:
                messagebox.showwarning("Campo requerido", "El campo Orden es obligatorio.", parent=win)
                return
            if not any(v.get().strip() for v in decimal_vars.values()):
                messagebox.showwarning(
                    "Campo requerido",
                    "Ingresá al menos un valor decimal (MO, MO e, Material o Material e).",
                    parent=win,
                )
                return

            def to_decimal128(val_str):
                v = val_str.strip().replace(",", ".")
                if not v:
                    return Decimal128("0")
                try:
                    return Decimal128(str(Decimal(v)))
                except InvalidOperation:
                    raise ValueError(f"Valor decimal inválido: '{val_str}'")

            try:
                mo       = to_decimal128(decimal_vars["MO"].get())
                mo_e     = to_decimal128(decimal_vars["MO e"].get())
                material = to_decimal128(decimal_vars["Material"].get())
                mat_e    = to_decimal128(decimal_vars["Material e"].get())
                total    = Decimal128(str(
                    Decimal(mo.to_decimal()) +
                    Decimal(mo_e.to_decimal()) +
                    Decimal(material.to_decimal()) +
                    Decimal(mat_e.to_decimal())
                ))
                doc = {
                    "orden":       orden,
                    "fecha":       datetime.now(),
                    "reparacion":  reparacion_var.get().strip(),
                    "motivo":      motivo_var.get().strip(),
                    "MO":          mo,
                    "MO_e":        mo_e,
                    "Material":    material,
                    "Material_e":  mat_e,
                    "Total":       total,
                    "observacion": obs_txt.get("1.0", tk.END).strip(),
                }
            except ValueError as e:
                messagebox.showerror("Error de formato", str(e), parent=win)
                return

            try:
                db = self._get_db()
                db[self.coll_5].insert_one(doc)
                logger.info("Débito guardado: orden=%s total=%s", orden, total)
                lbl_feedback.config(text="✔ Débito guardado correctamente.", fg="#2e7d32")
                orden_var.set("")
                reparacion_var.set("")
                motivo_var.set("")
                for v in decimal_vars.values():
                    v.set("")
                lbl_total.config(text="0.00")
                obs_txt.delete("1.0", tk.END)
            except Exception as e:
                logger.error("Error al guardar débito: %s", e)
                messagebox.showerror("Error", f"No se pudo guardar:\n{e}", parent=win)

        tk.Button(win, text="Guardar débito", font=("Arial", 10, "bold"),
                  bg="#1a6eb5", fg="white", relief=tk.FLAT, padx=12, pady=4,
                  command=guardar).pack(pady=(4, 0))

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
                f"No se encontró dashboard_viewer.py en:\n{viewer}",
            )
            return

        subprocess.Popen(
            [sys.executable, str(viewer)],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

    # ──────────────────────────────────────────────
    #  ASISTENTE DE GARANTÍA
    # ──────────────────────────────────────────────
    def open_warranty_assistant(self):
        win = tk.Toplevel(self.root)
        win.title("Asistente de Garantía — IA")
        win.geometry("800x580")
        win.resizable(True, True)

        self.assistant.clear_history()

        tk.Label(win, text="Consultas al asistente", font=("Arial", 10, "bold")).pack(
            anchor="w", padx=10, pady=(10, 2)
        )

        chat_area = scrolledtext.ScrolledText(
            win, state=tk.DISABLED, wrap=tk.WORD,
            font=("Arial", 10), bg="#fafafa", relief=tk.SUNKEN,
        )
        chat_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        chat_area.tag_config("sistema",         foreground="#888888", font=("Arial", 9, "italic"))
        chat_area.tag_config("agente_label",    foreground="#1a6eb5", font=("Arial", 10, "bold"))
        chat_area.tag_config("agente_text",     foreground="#1a1a1a", font=("Arial", 10))
        chat_area.tag_config("asistente_label", foreground="#2e7d32", font=("Arial", 10, "bold"))
        chat_area.tag_config("asistente_text",  foreground="#1a1a1a", font=("Arial", 10))
        chat_area.tag_config("error_label",     foreground="#c62828", font=("Arial", 10, "bold"))
        chat_area.tag_config("separador",       foreground="#cccccc")

        entry_frame = tk.Frame(win)
        entry_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        entrada = tk.Entry(entry_frame, font=("Arial", 11))
        entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        btn_enviar = tk.Button(entry_frame, text="Consultar ▶",
                               font=("Arial", 10, "bold"),
                               bg="#2e7d32", fg="white",
                               relief=tk.FLAT, padx=10)
        btn_enviar.pack(side=tk.RIGHT, padx=(6, 0))

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
                on_error=lambda e: win.after(0, mostrar_error, e),
            )

        btn_enviar.config(command=enviar_pregunta)
        entrada.bind("<Return>", enviar_pregunta)

        def cargar_docs():
            if self.assistant.docs_loaded:
                nombres = ", ".join(d["filename"] for d in self.assistant.pdf_documents)
                agregar_mensaje("Sistema", f"Documentos en caché: {nombres}")
                agregar_mensaje("Sistema", "Listo para responder consultas.")
                entrada.focus()
                return
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
