import os
import csv
import json
import logging
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pymongo import MongoClient
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
        self.coll_6 = "tasks"

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
            ("🔍  Consulta por orden",  self.open_order_query,                 "#f3e5f5", "#6a1b9a"),
            ("📊  Dashboard",           self.open_dashboard,                   "#fce4ec", "#880e4f"),
            ("📷  Lector de órdenes",   self.open_order_scanner,               "#e8f5e9", "#1b5e20"),
            ("📷  Lector de piezas",    self.open_parts_scanner,               "#e8f5e9", "#1b5e20"),
            ("🏷   Generar QR piezas",  self.open_qr_generator,                "#fbe9e7", "#bf360c"),
            ("📝  Ver tareas",          self.open_tasks_viewer,                "#e8eaf6", "#283593"),
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
        options_menu.add_command(label="6. Ver tareas",
                                 command=self.open_tasks_viewer)
        options_menu.add_separator()
        options_menu.add_command(label="Exit", command=self.root.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Ingresar desvío", command=self.open_fault_form)
        edit_menu.add_command(label="Ingresar débito", command=self.open_debt_form)
        edit_menu.add_separator()
        edit_menu.add_command(label="Generar QR piezas", command=self.open_qr_generator)

        queries_menu = tk.Menu(menubar, tearoff=0)
        queries_menu.add_command(label="Consulta por orden", command=self.open_order_query)

        dashboard_menu = tk.Menu(menubar, tearoff=0)
        dashboard_menu.add_command(label="Abrir dashboard", command=self.open_dashboard)

        menubar.add_cascade(label="Inicio", menu=options_menu)
        menubar.add_cascade(label="Editar", menu=edit_menu)
        menubar.add_cascade(label="Consultas", menu=queries_menu)
        menubar.add_cascade(label="📊 Dashboard", menu=dashboard_menu)

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
    #  LECTOR DE ÓRDENES
    # ──────────────────────────────────────────────
    def open_order_scanner(self):
        win = tk.Toplevel(self.root)
        win.title("Lector de Órdenes")
        win.geometry("600x500")
        win.resizable(True, True)

        tk.Label(win, text="Lector de Órdenes",
                 font=("Arial", 13, "bold"), fg="#1b5e20").pack(pady=(16, 2))
        tk.Label(win, text="Escaneá o ingresá el código de orden y presioná Enter",
                 font=("Arial", 9), fg="#555555").pack(pady=(0, 10))

        entry_frame = tk.Frame(win)
        entry_frame.pack(fill=tk.X, padx=16, pady=(0, 10))

        entrada = tk.Entry(entry_frame, font=("Arial", 13), relief=tk.SOLID, bd=1)
        entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        btn_scan = tk.Button(entry_frame, text="Registrar ▶",
                             font=("Arial", 10, "bold"),
                             bg="#1b5e20", fg="white", relief=tk.FLAT, padx=10)
        btn_scan.pack(side=tk.RIGHT, padx=(8, 0))

        log = scrolledtext.ScrolledText(win, state=tk.DISABLED, wrap=tk.WORD,
                                        font=("Consolas", 10), bg="#f8f8f8", relief=tk.SUNKEN)
        log.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        log.tag_config("ok",   foreground="#2e7d32", font=("Consolas", 10, "bold"))
        log.tag_config("dup",  foreground="#e65100", font=("Consolas", 10, "bold"))
        log.tag_config("err",  foreground="#c62828", font=("Consolas", 10, "bold"))
        log.tag_config("info", foreground="#555555", font=("Consolas", 9, "italic"))

        def _log(msg, tag="info"):
            log.config(state=tk.NORMAL)
            ts = datetime.now().strftime("%H:%M:%S")
            log.insert(tk.END, f"[{ts}]  {msg}\n", tag)
            log.see(tk.END)
            log.config(state=tk.DISABLED)

        _log("Listo. Esperando escaneo…")

        def registrar(event=None):
            codigo = entrada.get().strip()
            entrada.delete(0, tk.END)
            if not codigo:
                return
            try:
                db = self._get_db()
                col = db[self.coll_1]
                existing = col.find_one({"orden": codigo})
                if existing:
                    fecha = existing.get("scanned_at", "fecha desconocida")
                    _log(f"DUPLICADO — '{codigo}' ya registrado el {fecha}", "dup")
                else:
                    col.insert_one({
                        "orden": codigo,
                        "scanned_at": datetime.now(),
                        "source": "handheld_scanner",
                    })
                    _log(f"OK — Orden '{codigo}' registrada correctamente", "ok")
            except Exception as e:
                _log(f"ERROR — {e}", "err")
            finally:
                entrada.focus()

        btn_scan.config(command=registrar)
        entrada.bind("<Return>", registrar)
        win.after(100, entrada.focus)

    # ──────────────────────────────────────────────
    #  LECTOR DE PIEZAS
    # ──────────────────────────────────────────────
    def open_parts_scanner(self):
        win = tk.Toplevel(self.root)
        win.title("Lector de Piezas")
        win.geometry("640x520")
        win.resizable(True, True)

        tk.Label(win, text="Lector de Piezas",
                 font=("Arial", 13, "bold"), fg="#1b5e20").pack(pady=(16, 2))
        tk.Label(win, text="Escaneá el código QR de la pieza y presioná Enter",
                 font=("Arial", 9), fg="#555555").pack(pady=(0, 10))

        entry_frame = tk.Frame(win)
        entry_frame.pack(fill=tk.X, padx=16, pady=(0, 10))

        entrada = tk.Entry(entry_frame, font=("Arial", 13), relief=tk.SOLID, bd=1)
        entrada.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)

        btn_scan = tk.Button(entry_frame, text="Registrar ▶",
                             font=("Arial", 10, "bold"),
                             bg="#1b5e20", fg="white", relief=tk.FLAT, padx=10)
        btn_scan.pack(side=tk.RIGHT, padx=(8, 0))

        log = scrolledtext.ScrolledText(win, state=tk.DISABLED, wrap=tk.WORD,
                                        font=("Consolas", 10), bg="#f8f8f8", relief=tk.SUNKEN)
        log.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 12))
        log.tag_config("ok",   foreground="#2e7d32", font=("Consolas", 10, "bold"))
        log.tag_config("dup",  foreground="#e65100", font=("Consolas", 10, "bold"))
        log.tag_config("err",  foreground="#c62828", font=("Consolas", 10, "bold"))
        log.tag_config("info", foreground="#555555", font=("Consolas", 9, "italic"))

        def _log(msg, tag="info"):
            log.config(state=tk.NORMAL)
            ts = datetime.now().strftime("%H:%M:%S")
            log.insert(tk.END, f"[{ts}]  {msg}\n", tag)
            log.see(tk.END)
            log.config(state=tk.DISABLED)

        _log("Listo. Esperando escaneo… (JSON con campos: orden, pieza, cantidad)")

        def registrar(event=None):
            raw = entrada.get().strip()
            entrada.delete(0, tk.END)
            if not raw:
                return
            try:
                data = json.loads(raw)
                orden    = str(data["orden"])
                pieza    = str(data["pieza"])
                cantidad = data["cantidad"]
            except (json.JSONDecodeError, KeyError) as e:
                _log(f"ERROR — Formato inválido: {e}. Se esperaba JSON con orden/pieza/cantidad", "err")
                entrada.focus()
                return
            try:
                db = self._get_db()
                col = db[self.coll_2]
                existing = col.find_one({"orden": orden, "pieza": pieza, "cantidad": cantidad})
                if existing:
                    fecha = existing.get("scanned_at", "fecha desconocida")
                    _log(
                        f"DUPLICADO — Orden '{orden}' / Pieza '{pieza}' / "
                        f"Cantidad '{cantidad}' ya registrado el {fecha}", "dup"
                    )
                else:
                    col.insert_one({
                        "orden": orden,
                        "pieza": pieza,
                        "cantidad": cantidad,
                        "scanned_at": datetime.now(),
                        "source": "handheld_scanner",
                    })
                    _log(f"OK — Pieza '{pieza}' (Orden: {orden} | Cant: {cantidad}) registrada", "ok")
            except Exception as e:
                _log(f"ERROR — {e}", "err")
            finally:
                entrada.focus()

        btn_scan.config(command=registrar)
        entrada.bind("<Return>", registrar)
        win.after(100, entrada.focus)

    # ──────────────────────────────────────────────
    #  GENERADOR DE QR DE PIEZAS
    # ──────────────────────────────────────────────
    def open_qr_generator(self):
        try:
            import qrcode as qrcode_lib
            from PIL import Image, ImageDraw, ImageFont, ImageTk
            from fpdf import FPDF
        except ImportError as e:
            messagebox.showerror(
                "Dependencias faltantes",
                f"Instalá los paquetes necesarios:\n  pip install qrcode Pillow fpdf2\n\nDetalle: {e}",
            )
            return

        temp_dir = os.path.join(BASE_DIR, "temp_qr")
        os.makedirs(temp_dir, exist_ok=True)
        for f in os.listdir(temp_dir):
            fp = os.path.join(temp_dir, f)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                except Exception:
                    pass

        queue = []
        preview_ref = [None]

        win = tk.Toplevel(self.root)
        win.title("Generador de QR de Piezas")
        win.geometry("740x560")
        win.resizable(True, True)

        tk.Label(win, text="Generador de QR de Piezas",
                 font=("Arial", 13, "bold"), fg="#bf360c").pack(pady=(14, 6))

        main_frame = tk.Frame(win)
        main_frame.pack(fill=tk.X, padx=16, pady=(0, 6))

        # ── Formulario
        form = tk.LabelFrame(main_frame, text="Nueva etiqueta",
                             font=("Arial", 9), padx=12, pady=10)
        form.pack(side=tk.LEFT, fill=tk.Y)

        def _field(parent, label, row):
            tk.Label(parent, text=label, font=("Arial", 10), anchor="w").grid(
                row=row, column=0, sticky="w", pady=4)
            e = tk.Entry(parent, font=("Arial", 11), width=18, relief=tk.SOLID, bd=1)
            e.grid(row=row, column=1, padx=(8, 0), pady=4)
            return e

        entry_orden    = _field(form, "Orden:",    0)
        entry_pieza    = _field(form, "Pieza:",    1)
        entry_cantidad = _field(form, "Cantidad:", 2)

        btn_agregar = tk.Button(form, text="Agregar QR ▶",
                                font=("Arial", 10, "bold"),
                                bg="#bf360c", fg="white", relief=tk.FLAT, pady=7, padx=12)
        btn_agregar.grid(row=3, column=0, columnspan=2, pady=(12, 0), sticky="ew")

        # ── Vista previa
        preview_frame = tk.LabelFrame(main_frame, text="Vista previa",
                                      font=("Arial", 9), padx=8, pady=8)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 0))

        preview_lbl = tk.Label(preview_frame, bg="#f0f0f0")
        preview_lbl.pack(fill=tk.BOTH, expand=True)

        # ── Cola
        queue_frame = tk.LabelFrame(win, text="Cola de etiquetas",
                                    font=("Arial", 9), padx=8, pady=4)
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 6))

        cols = ("num", "orden", "pieza", "cantidad")
        tree = ttk.Treeview(queue_frame, columns=cols, show="headings", height=5)
        tree.heading("num",      text="#")
        tree.heading("orden",    text="Orden")
        tree.heading("pieza",    text="Pieza")
        tree.heading("cantidad", text="Cantidad")
        tree.column("num",      width=40,  stretch=False)
        tree.column("orden",    width=180)
        tree.column("pieza",    width=180)
        tree.column("cantidad", width=100)
        vsb = ttk.Scrollbar(queue_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # ── Botones inferiores
        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

        lbl_count = tk.Label(btn_frame, text="0 etiquetas en cola",
                             font=("Arial", 9), fg="#555555")
        lbl_count.pack(side=tk.LEFT)

        btn_pdf      = tk.Button(btn_frame, text="🖨  Generar PDF",
                                 font=("Arial", 10, "bold"), bg="#1565c0", fg="white",
                                 relief=tk.FLAT, padx=12, pady=4)
        btn_eliminar = tk.Button(btn_frame, text="Eliminar seleccionado",
                                 font=("Arial", 9), bg="#c62828", fg="white",
                                 relief=tk.FLAT, padx=8)
        btn_limpiar  = tk.Button(btn_frame, text="Limpiar todo",
                                 font=("Arial", 9), bg="#757575", fg="white",
                                 relief=tk.FLAT, padx=8)
        btn_pdf.pack(side=tk.RIGHT, padx=(6, 0))
        btn_eliminar.pack(side=tk.RIGHT, padx=(6, 0))
        btn_limpiar.pack(side=tk.RIGHT, padx=(6, 0))

        # ── Lógica
        def _make_qr_image(orden, pieza, cantidad, path):
            data_str = json.dumps({"orden": orden, "pieza": pieza, "cantidad": cantidad})
            qr = qrcode_lib.QRCode(box_size=8, border=3)
            qr.add_data(data_str)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            w, h = qr_img.size
            canvas = Image.new("RGB", (w, h + 70), "white")
            canvas.paste(qr_img, (0, 0))
            draw = ImageDraw.Draw(canvas)
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
            except Exception:
                font = ImageFont.load_default()
            for i, line in enumerate([f"Orden: {orden}", f"Pieza: {pieza}", f"Cant:  {cantidad}"]):
                draw.text((20, h + 4 + i * 22), line, fill="black", font=font)
            canvas.save(path)
            return canvas

        def _refresh():
            for iid in tree.get_children():
                tree.delete(iid)
            for i, item in enumerate(queue, 1):
                tree.insert("", tk.END, iid=str(i),
                            values=(i, item["orden"], item["pieza"], item["cantidad"]))
            n = len(queue)
            lbl_count.config(text=f"{n} etiqueta{'s' if n != 1 else ''} en cola")

        def agregar(event=None):
            orden    = entry_orden.get().strip()
            pieza    = entry_pieza.get().strip().upper()
            cantidad = entry_cantidad.get().strip()
            if not orden or not pieza or not cantidad:
                messagebox.showwarning("Campos vacíos", "Completá todos los campos.", parent=win)
                return
            idx  = len(queue) + 1
            path = os.path.join(temp_dir, f"{idx}.png")
            try:
                img = _make_qr_image(orden, pieza, cantidad, path)
                queue.append({"orden": orden, "pieza": pieza, "cantidad": cantidad, "path": path})
                thumb = img.copy()
                thumb.thumbnail((170, 170))
                photo = ImageTk.PhotoImage(thumb)
                preview_ref[0] = photo
                preview_lbl.config(image=photo)
                _refresh()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)
                return
            entry_orden.delete(0, tk.END)
            entry_pieza.delete(0, tk.END)
            entry_cantidad.delete(0, tk.END)
            entry_orden.focus()

        def _rebuild_images():
            for f in os.listdir(temp_dir):
                fp = os.path.join(temp_dir, f)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
            for i, item in enumerate(queue, 1):
                path = os.path.join(temp_dir, f"{i}.png")
                _make_qr_image(item["orden"], item["pieza"], item["cantidad"], path)
                item["path"] = path

        def eliminar():
            sel = tree.selection()
            if not sel:
                return
            indices = {int(iid) - 1 for iid in sel}
            queue[:] = [item for i, item in enumerate(queue) if i not in indices]
            _rebuild_images()
            if queue:
                last = Image.open(queue[-1]["path"])
                last.thumbnail((170, 170))
                photo = ImageTk.PhotoImage(last)
                preview_ref[0] = photo
                preview_lbl.config(image=photo)
            else:
                preview_ref[0] = None
                preview_lbl.config(image="")
            _refresh()

        def limpiar():
            if not queue:
                return
            if not messagebox.askyesno("Confirmar", "¿Limpiar toda la cola?", parent=win):
                return
            queue.clear()
            for f in os.listdir(temp_dir):
                fp = os.path.join(temp_dir, f)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
            preview_ref[0] = None
            preview_lbl.config(image="")
            _refresh()

        def generar_pdf():
            if not queue:
                messagebox.showwarning("Cola vacía", "Agregá al menos una etiqueta.", parent=win)
                return
            pdf_path = os.path.join(temp_dir, "etiquetas.pdf")
            try:
                pdf      = FPDF("P", "mm", "A4")
                date_str = datetime.now().strftime("%d/%m/%Y")
                W        = 210  # A4 width

                # Fuente con soporte Unicode para caracteres acentuados
                pdf.add_font("Arial",  style="",  fname="C:/Windows/Fonts/arial.ttf")
                pdf.add_font("Arial",  style="B", fname="C:/Windows/Fonts/arialbd.ttf")

                # ── Hoja 1: remito ──────────────────────────────
                pdf.add_page()

                # Encabezado
                pdf.set_font("Arial", "B", 16)
                pdf.cell(0, 10, "Remito de piezas de Garantía", ln=True, align="C")
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, f"Fecha: {date_str}    |    Total de piezas: {len(queue)}",
                         ln=True, align="C")
                pdf.ln(6)

                # Línea divisoria
                pdf.set_draw_color(180, 180, 180)
                pdf.set_line_width(0.4)
                pdf.line(15, pdf.get_y(), W - 15, pdf.get_y())
                pdf.ln(4)

                # Encabezado de tabla
                col_w = {"num": 12, "orden": 58, "pieza": 78, "cantidad": 32}
                pdf.set_fill_color(40, 40, 40)
                pdf.set_text_color(255, 255, 255)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(col_w["num"],      8, "#",        border=0, fill=True, align="C")
                pdf.cell(col_w["orden"],    8, "Orden",    border=0, fill=True, align="C")
                pdf.cell(col_w["pieza"],    8, "Pieza",    border=0, fill=True, align="C")
                pdf.cell(col_w["cantidad"], 8, "Cantidad", border=0, fill=True, align="C")
                pdf.ln()

                # Filas
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "", 10)
                fill_colors = [(255, 255, 255), (245, 245, 245)]
                for idx, item in enumerate(queue, 1):
                    r, g, b = fill_colors[idx % 2]
                    pdf.set_fill_color(r, g, b)
                    pdf.cell(col_w["num"],      7, str(idx),              border=0, fill=True, align="C")
                    pdf.cell(col_w["orden"],    7, item["orden"],          border=0, fill=True)
                    pdf.cell(col_w["pieza"],    7, item["pieza"],          border=0, fill=True)
                    pdf.cell(col_w["cantidad"], 7, str(item["cantidad"]),  border=0, fill=True, align="C")
                    pdf.ln()

                # Línea cierre de tabla
                pdf.set_draw_color(180, 180, 180)
                pdf.line(15, pdf.get_y(), W - 15, pdf.get_y())
                pdf.ln(8)

                # Firma
                pdf.set_font("Arial", "", 9)
                pdf.set_text_color(120, 120, 120)
                pdf.cell(0, 5, "Firma: ______________________________    Aclaracion: ______________________________",
                         ln=True)

                # ── Hojas 2+: etiquetas QR ──────────────────────
                col_x = [15, 110]
                row_y = [22, 112, 202]

                for page_start in range(0, len(queue), 6):
                    pdf.add_page()
                    pdf.set_font("Arial", "", 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.cell(0, 0, text=f"Etiquetas QR  -  {date_str}")
                    for i, item in enumerate(queue[page_start:page_start + 6]):
                        pdf.image(item["path"], col_x[i % 2], row_y[i // 2], w=0, h=82)

                pdf.output(pdf_path)
                os.startfile(pdf_path)
            except Exception as e:
                messagebox.showerror("Error al generar PDF", str(e), parent=win)

        btn_agregar.config(command=agregar)
        btn_eliminar.config(command=eliminar)
        btn_limpiar.config(command=limpiar)
        btn_pdf.config(command=generar_pdf)

        entry_orden.bind("<Return>",    lambda e: entry_pieza.focus())
        entry_pieza.bind("<Return>",    lambda e: entry_cantidad.focus())
        entry_cantidad.bind("<Return>", agregar)

        def on_close():
            for f in os.listdir(temp_dir):
                fp = os.path.join(temp_dir, f)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)
        win.after(100, entry_orden.focus)

    # ──────────────────────────────────────────────
    #  TAREAS
    # ──────────────────────────────────────────────
    def open_tasks_viewer(self):
        from bson import ObjectId

        COLS    = ("cierre", "orden", "descripcion", "reclamado", "contrato_pendiente", "observacion")
        HEADERS = ("Cierre", "Orden", "Descripción", "Reclamado", "Contrato pend.", "Observación")
        COL_W   = (88, 95, 190, 88, 95, 180)

        editing_id = [None]   # ObjectId del doc en edición, None = nueva tarea

        def _fmt_date(val):
            if val and hasattr(val, "strftime"):
                return val.strftime("%d/%m/%Y")
            return str(val) if val else ""

        def _parse_date(s):
            s = s.strip()
            if not s:
                return None
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    pass
            raise ValueError(f"Fecha inválida: '{s}'. Usá dd/mm/yyyy")

        def _row_values(doc):
            return (
                _fmt_date(doc.get("cierre")),
                doc.get("orden", ""),
                doc.get("descripcion", ""),
                _fmt_date(doc.get("reclamado")),
                "Sí" if doc.get("contrato_pendiente") else "No",
                doc.get("observacion", ""),
            )

        # ── Ventana principal ──────────────────────────────────────────────
        win = tk.Toplevel(self.root)
        win.title("Tareas")
        win.geometry("1180x560")
        win.resizable(True, True)

        # Header
        header = tk.Frame(win, bg="#283593")
        header.pack(fill=tk.X)
        tk.Label(header, text="Tareas", font=("Arial", 12, "bold"),
                 bg="#283593", fg="white").pack(side=tk.LEFT, padx=14, pady=8)

        # Contenido principal: treeview (izq) + formulario (der)
        body = tk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # ── Panel izquierdo: treeview ──────────────────────────────────────
        left = tk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(left, columns=COLS, show="headings", selectmode="browse")
        for col, hdr, w in zip(COLS, HEADERS, COL_W):
            tree.heading(col, text=hdr)
            tree.column(col, width=w, minwidth=50)

        vsb = ttk.Scrollbar(left, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(left, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT,  fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(fill=tk.BOTH, expand=True)

        lbl_status = tk.Label(left, text="", font=("Arial", 8), fg="#555555", anchor="w")
        lbl_status.pack(fill=tk.X, pady=(3, 0))

        # ── Panel derecho: formulario ──────────────────────────────────────
        sep = tk.Frame(body, bg="#cccccc", width=1)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))

        right = tk.Frame(body, width=272)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        lbl_form_title = tk.Label(right, text="Nueva tarea",
                                  font=("Arial", 10, "bold"), fg="#283593", anchor="w")
        lbl_form_title.pack(fill=tk.X, pady=(0, 8))

        ff = tk.Frame(right)
        ff.pack(fill=tk.X)
        ff.columnconfigure(1, weight=1)

        def _lbl(text, row):
            tk.Label(ff, text=text, font=("Arial", 9), anchor="w").grid(
                row=row, column=0, sticky="w", pady=3, padx=(0, 6))

        def _ent(row):
            e = tk.Entry(ff, font=("Arial", 10), relief=tk.SOLID, bd=1)
            e.grid(row=row, column=1, sticky="ew", pady=3)
            return e

        _lbl("Cierre (dd/mm/yyyy):", 0);  e_cierre = _ent(0)
        _lbl("Orden:",               1);  e_orden  = _ent(1)
        _lbl("Descripción:",         2);  e_desc   = _ent(2)
        _lbl("Reclamado (dd/mm/yyyy):", 3); e_recl = _ent(3)

        _lbl("Contrato pendiente:", 4)
        var_contrato = tk.BooleanVar()
        tk.Checkbutton(ff, variable=var_contrato).grid(row=4, column=1, sticky="w", pady=3)

        _lbl("Observación:", 5)
        e_obs = tk.Text(ff, font=("Arial", 10), height=4, relief=tk.SOLID, bd=1, wrap=tk.WORD)
        e_obs.grid(row=5, column=1, sticky="ew", pady=3)

        lbl_err = tk.Label(right, text="", font=("Arial", 8), fg="#c62828",
                           wraplength=260, anchor="w", justify="left")
        lbl_err.pack(fill=tk.X, pady=(4, 0))

        btn_row = tk.Frame(right)
        btn_row.pack(fill=tk.X, pady=(8, 0))

        btn_limpiar = tk.Button(btn_row, text="Nueva tarea",
                                font=("Arial", 9), bg="#eeeeee",
                                relief=tk.FLAT, padx=8)
        btn_limpiar.pack(side=tk.LEFT)

        btn_guardar = tk.Button(btn_row, text="Guardar",
                                font=("Arial", 9, "bold"),
                                bg="#283593", fg="white", relief=tk.FLAT, padx=10)
        btn_guardar.pack(side=tk.RIGHT)

        # ── Lógica ────────────────────────────────────────────────────────
        def _load():
            for iid in tree.get_children():
                tree.delete(iid)
            try:
                docs = list(self._get_db()[self.coll_6].find().sort("cierre", 1))
                for doc in docs:
                    tree.insert("", tk.END, iid=str(doc["_id"]), values=_row_values(doc))
                n = len(docs)
                lbl_status.config(text=f"{n} tarea{'s' if n != 1 else ''}")
            except Exception as exc:
                lbl_status.config(text=f"Error: {exc}")

        def _clear_form():
            editing_id[0] = None
            lbl_form_title.config(text="Nueva tarea")
            lbl_err.config(text="")
            for e in (e_cierre, e_orden, e_desc, e_recl):
                e.delete(0, tk.END)
            var_contrato.set(False)
            e_obs.delete("1.0", tk.END)
            tree.selection_remove(*tree.selection())

        def _load_doc(doc):
            editing_id[0] = doc["_id"]
            lbl_form_title.config(text="Editar tarea")
            lbl_err.config(text="")
            e_cierre.delete(0, tk.END); e_cierre.insert(0, _fmt_date(doc.get("cierre")))
            e_orden.delete(0, tk.END);  e_orden.insert(0,  doc.get("orden", ""))
            e_desc.delete(0, tk.END);   e_desc.insert(0,   doc.get("descripcion", ""))
            e_recl.delete(0, tk.END);   e_recl.insert(0,   _fmt_date(doc.get("reclamado")))
            var_contrato.set(doc.get("contrato_pendiente", False))
            e_obs.delete("1.0", tk.END)
            if doc.get("observacion"):
                e_obs.insert("1.0", doc["observacion"])

        def _guardar():
            lbl_err.config(text="")
            try:
                cierre = _parse_date(e_cierre.get())
                recl   = _parse_date(e_recl.get())
            except ValueError as exc:
                lbl_err.config(text=str(exc))
                return
            datos = {
                "cierre":             cierre,
                "orden":              e_orden.get().strip(),
                "descripcion":        e_desc.get().strip(),
                "reclamado":          recl,
                "contrato_pendiente": var_contrato.get(),
                "observacion":        e_obs.get("1.0", tk.END).strip(),
            }
            try:
                col = self._get_db()[self.coll_6]
                if editing_id[0]:
                    col.update_one({"_id": editing_id[0]}, {"$set": datos})
                else:
                    col.insert_one(datos)
            except Exception as exc:
                lbl_err.config(text=f"Error: {exc}")
                return
            _clear_form()
            _load()

        def _on_double_click(event):
            sel = tree.selection()
            if not sel:
                return
            try:
                doc = self._get_db()[self.coll_6].find_one({"_id": ObjectId(sel[0])})
            except Exception:
                return
            if doc:
                _load_doc(doc)

        tree.bind("<Double-1>", _on_double_click)
        btn_guardar.config(command=_guardar)
        btn_limpiar.config(command=_clear_form)

        _load()


if __name__ == "__main__":
    root = tk.Tk()
    app = MongoApp(root)
    root.mainloop()
