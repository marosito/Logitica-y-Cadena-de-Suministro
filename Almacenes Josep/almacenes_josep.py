import os
import sys
import sqlite3
import csv
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk

# ==========================================
# CONFIGURACIÓN PARÁMETROS DEL ALMACÉN (Fácilmente modificables)
# ==========================================
PASILLOS = 10
ESTANTES = 10
ALTURAS = 3

DB_DIR = "SQLite"
DB_NAME = os.path.join(DB_DIR, "BaseDeDatos.sqlite")
BACKUP_DIR = "CSV_Backup"

# ==========================================
# INICIALIZACIÓN DE ENTORNOS Y DIRECTORIOS
# ==========================================
for directory in [DB_DIR, BACKUP_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

def obtener_turno():
    """Deduce automáticamente el turno según la hora del sistema."""
    hora = datetime.now().hour
    if 6 <= hora < 14:
        return "Mañana (06-14)"
    elif 14 <= hora < 22:
        return "Tarde (14-22)"
    else:
        return "Noche (22-06)"

# ==========================================
# GESTIÓN DE BASE DE DATOS (SQLite)
# ==========================================
def conectar_db():
    return sqlite3.connect(DB_NAME)

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    
    # 1. Tabla de Productos (Estructura base adaptada)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_sku TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT,
            stock_actual INTEGER DEFAULT 0,
            stock_seguridad INTEGER DEFAULT 0,
            stock_maximo INTEGER DEFAULT 0,
            punto_pedido INTEGER DEFAULT 0,
            costo_unitario REAL NOT NULL,
            precio_venta REAL NOT NULL,
            id_ubicacion TEXT,
            fecha_ultimo_movimiento TEXT
        )
    ''')
    
    # 2. Tabla de Histórico / Trazabilidad de Movimientos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_movimientos (
            id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TEXT NOT NULL,
            codigo_sku TEXT NOT NULL,
            tipo_movimiento TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            stock_anterior INTEGER NOT NULL,
            stock_posterior INTEGER NOT NULL,
            volumen_producido INTEGER DEFAULT 0,
            piezas_malas INTEGER DEFAULT 0,
            operario TEXT,
            turno TEXT,
            motivo TEXT
        )
    ''')
    
    # 3. Tabla de Tareas del Operario
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tareas_operario (
            id_tarea INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            fecha_creacion TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    
    # Insertar 128 referencias de prueba automáticas si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone() == 0:
        for i in range(1, 129):
            sku = f"REF-{i:03d}"
            nombre = f"Producto Tipo Especial {i}"
            p = ((i - 1) % PASILLOS) + 1
            e = (((i - 1) // PASILLOS) % ESTANTES) + 1
            a = (((i - 1) // (PASILLOS * ESTANTES)) % ALTURAS) + 1
            ubicacion = f"{chr(64+p)}-{e:02d}-{a}"
            
            cursor.execute('''
                INSERT INTO productos (codigo_sku, nombre, categoria, stock_actual, stock_seguridad, stock_maximo, punto_pedido, costo_unitario, precio_venta, id_ubicacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sku, nombre, 'General', 50, 15, 200, 30, 10.0, 15.0, ubicacion))
        conn.commit()
    conn.close()

# ==========================================
# LÓGICA DE BACKUPS LOGÍSTICOS (CSV - Retención 90 días)
# ==========================================
def realizar_backup_csv():
    """Genera snapshots diarios en formato CSV y elimina los superiores a 90 días."""
    conn = conectar_db()
    cursor = conn.cursor()
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Exportar Productos
    cursor.execute("SELECT * FROM productos")
    filas = cursor.fetchall()
    columnas = [description[0] for description in cursor.description]
    
    archivo_prod = os.path.join(BACKUP_DIR, f"Backup_Productos_{fecha_str}.csv")
    with open(archivo_prod, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columnas)
        writer.writerows(filas)
        
    conn.close()
    limpiar_backups_antiguos()

def limpiar_backups_antiguos():
    """Elimina archivos de backup con más de 90 días de antigüedad (3 meses)."""
    limite_tiempo = datetime.now() - timedelta(days=90)
    for archivo in os.listdir(BACKUP_DIR):
        ruta_archivo = os.path.join(BACKUP_DIR, archivo)
        if os.path.isfile(ruta_archivo):
            fecha_creacion = datetime.fromtimestamp(os.path.getmtime(ruta_archivo))
            if fecha_creacion < limite_tiempo:
                try:
                    os.remove(ruta_archivo)
                except Exception:
                    pass

# ==========================================
# INTERFAZ GRÁFICA PRINCIPAL (Tkinter HMI de planta)
# ==========================================
class AppAlmacen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Almacenes Josep - Control de Planta V0.1")
        
        # Configuración de pantalla completa sin bordes (Borderless)
        self.attributes('-fullscreen', True)
        
        self.operador_actual = "Operario Estándar"
        
        self.style = ttk.Style()
        self.style.configure("TLabel", font=("Arial", 12))
        self.style.configure("TButton", font=("Arial", 12, "bold"), padding=10)
        self.style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        self.style.configure("Treeview", font=("Arial", 11), rowheight=25)
        
        self.crear_interfaz()
        self.refrescar_datos()
        
    def crear_interfaz(self):
        panel_sup = tk.Frame(self, bg="#2c3e50", height=60)
        panel_sup.pack(fill=tk.X, side=tk.TOP)
        
        lbl_titulo = tk.Label(panel_sup, text="ALMACENES JOSEP - SISTEMA LOGÍSTICO", font=("Arial", 16, "bold"), fg="white", bg="#2c3e50")
        lbl_titulo.pack(side=tk.LEFT, padx=20, pady=15)
        
        # Botón para salir de pantalla completa de forma segura en planta
        btn_salir = tk.Button(panel_sup, text="❌ SALIR APP", command=self.quit, font=("Arial", 10, "bold"), bg="#c0392b", fg="white", bd=0, padx=15, pady=5)
        btn_salir.pack(side=tk.RIGHT, padx=20)
        
        self.lbl_turno = tk.Label(panel_sup, text=f"Turno: {obtener_turno()}", font=("Arial", 12, "bold"), fg="#f1c40f", bg="#2c3e50")
        self.lbl_turno.pack(side=tk.RIGHT, padx=20)
        
        pestanas = ttk.Notebook(self)
        pestanas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tab_inventario = ttk.Frame(pestanas)
        self.tab_operaciones = ttk.Frame(pestanas)
        self.tab_tareas = ttk.Frame(pestanas)
        self.tab_historico = ttk.Frame(pestanas)
        
        pestanas.add(self.tab_inventario, text=" 📦 INVENTARIO ACTUAL ")
        pestanas.add(self.tab_operaciones, text=" ⚙️ REGISTRAR OPERACIÓN ")
        pestanas.add(self.tab_tareas, text=" 📋 TAREAS DEL OPERARIO ")
        pestanas.add(self.tab_historico, text=" 🕒 HISTÓRICO TRAZABILIDAD ")
        
        self.construir_tab_inventario()
        self.construir_tab_operaciones()
        self.construir_tab_tareas()
        self.construir_tab_historico()

    def construir_tab_inventario(self):
        frame_busqueda = tk.Frame(self.tab_inventario, pady=10)
        frame_busqueda.pack(fill=tk.X)
        
        tk.Label(frame_busqueda, text="Buscar Código SKU: ").pack(side=tk.LEFT, padx=10)
        self.txt_buscar = tk.Entry(frame_busqueda, font=("Arial", 12))
        self.txt_buscar.pack(side=tk.LEFT, padx=10)
        self.txt_buscar.bind("<KeyRelease>", lambda event: self.refrescar_datos())
        
        self.tabla_inv = ttk.Treeview(self.tab_inventario, columns=("SKU", "Nombre", "Ubicación", "Stock", "Mínimo", "Estado"), show="headings")
        self.tabla_inv.heading("SKU", text="Código SKU")
        self.tabla_inv.heading("Nombre", text="Nombre Producto")
        self.tabla_inv.heading("Ubicación", text="Ubicación Física")
        self.tabla_inv.heading("Stock", text="Stock Actual")
        self.tabla_inv.heading("Mínimo", text="Stock Mínimo")
        self.tabla_inv.heading("Estado", text="Alerta Estado")
        
        self.tabla_inv.tag_configure("ROTURA", background="#ffcccc", foreground="#cc0000")
        self.tabla_inv.tag_configure("MINIMO", background="#ffe5cc", foreground="#cc6600")
        
        self.tabla_inv.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def construir_tab_operaciones(self):
        frame_form = tk.Frame(self.tab_operaciones, padx=20, pady=20)
        frame_form.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(frame_form, text="Código SKU del Producto:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.cmb_sku = ttk.Combobox(frame_form, font=("Arial", 12), width=30, state="readonly")
        self.cmb_sku.grid(row=0, column=1, pady=10, padx=10)
        
        tk.Label(frame_form, text="Tipo de Acción / Movimiento:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.cmb_tipo_mov = ttk.Combobox(frame_form, values=["ENTRADA", "SALIDA", "PRODUCCIÓN", "REGULARIZACIÓN"], font=("Arial", 12), width=30, state="readonly")
        self.cmb_tipo_mov.grid(row=1, column=1, pady=10, padx=10)
        self.cmb_tipo_mov.bind("<<ComboboxSelected>>", self.gestionar_campos_dinamicos)
        
        self.lbl_cant = tk.Label(frame_form, text="Cantidad / Unidades:")
        self.lbl_cant.grid(row=2, column=0, sticky=tk.W, pady=10)
        self.txt_cant = tk.Entry(frame_form, font=("Arial", 12), width=32)
        self.txt_cant.grid(row=2, column=1, pady=10, padx=10)
        
        self.lbl_malas = tk.Label(frame_form, text="Piezas Defectuosas (Mermas):")
        self.txt_malas = tk.Entry(frame_form, font=("Arial", 12), width=32)
        
        self.lbl_motivo = tk.Label(frame_form, text="Motivo del Ajuste:")
        self.cmb_motivo = ttk.Combobox(frame_form, values=["Recuento físico cíclico", "Rotura en estantería", "Pérdida/Extravío", "Error de registro anterior"], font=("Arial", 12), width=30, state="readonly")
        
        btn_guardar = ttk.Button(frame_form, text="💾 VALIDAR Y APLICAR OPERACIÓN", command=self.procesar_operacion)
        btn_guardar.grid(row=5, column=0, columnspan=2, pady=30, ipady=5)

    def gestionar_campos_dinamicos(self, event):
        tipo = self.cmb_tipo_mov.get()
        self.lbl_malas.grid_remove()
        self.txt_malas.grid_remove()
        self.lbl_motivo.grid_remove()
        self.cmb_motivo.grid_remove()
        
        if tipo == "PRODUCCIÓN":
            self.lbl_cant.config(text="Volumen Total Producido:")
            self.lbl_malas.grid(row=3, column=0, sticky=tk.W, pady=10)
            self.txt_malas.grid(row=3, column=1, pady=10, padx=10)
        elif tipo == "REGULARIZACIÓN":
            self.lbl_cant.config(text="Stock Físico Real Encontrado:")
            self.lbl_motivo.grid(row=3, column=0, sticky=tk.W, pady=10)
            self.cmb_motivo.grid(row=3, column=1, pady=10, padx=10)
        else:
            self.lbl_cant.config(text="Cantidad / Unidades:")

    def construir_tab_tareas(self):
        lbl_info = tk.Label(self.tab_tareas, text="Instrucciones automáticas de movimientos físicos dentro del almacén:", font=("Arial", 12, "bold"))
        lbl_info.pack(anchor=tk.W, padx=10, pady=10)
        
        self.tabla_tareas = ttk.Treeview(self.tab_tareas, columns=("ID", "Descripcion", "Estado"), show="headings")
        self.tabla_tareas.heading("ID", text="ID Tarea")
        self.tabla_tareas.heading("Descripcion", text="Instrucción de Trabajo Física")
        self.tabla_tareas.heading("Estado", text="Estado de Ejecución")
        self.tabla_tareas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        btn_completar = ttk.Button(self.tab_tareas, text="✓ SELECCIONAR Y MARCAR COMO HECHO", command=self.completar_tarea)
        btn_completar.pack(pady=10)

    def construir_tab_historico(self):
        self.tabla_hist = ttk.Treeview(self.tab_historico, columns=("Fecha", "SKU", "Tipo", "Cant", "Ant", "Post", "Turno", "Info Extra"), show="headings")
        self.tabla_hist.heading("Fecha", text="Fecha / Hora")
        self.tabla_hist.heading("SKU", text="SKU")
        self.tabla_hist.heading("Tipo", text="Movimiento")
        self.tabla_hist.heading("Cant", text="Cant.")
        self.tabla_hist.heading("Ant", text="St. Ant")
        self.tabla_hist.heading("Post", text="St. Post")
        self.tabla_hist.heading("Turno", text="Turno")
        self.tabla_hist.heading("Info Extra", text="Anotación / Motivo")
        
        self.tabla_hist.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def refrescar_datos(self):
        for row in self.tabla_inv.get_children():
            self.tabla_inv.delete(row)
            
        conn = conectar_db()
        cursor = conn.cursor()
        
        busqueda = f"%{self.txt_buscar.get()}%"
        cursor.execute("SELECT codigo_sku, nombre, id_ubicacion, stock_actual, stock_seguridad FROM productos WHERE codigo_sku LIKE ?", (busqueda,))
        productos = cursor.fetchall()
        
        lista_skus = []
        for p in productos:
            sku, nombre, ubicacion, stock, min_stock = p
            lista_skus.append(sku)
            
            estado = "NORMAL"
            tag_color = ""
            if stock == 0:
                estado = "⚠️ ROTURA DE STOCK"
                tag_color = "ROTURA"
            elif stock <= min_stock:
                estado = "⏳ STOCK MÍNIMO"
                tag_color = "MINIMO"
                
            self.tabla_inv.insert("", tk.END, values=(sku, nombre, ubicacion, stock, min_stock, estado), tags=(tag_color,))
            
        self.cmb_sku['values'] = lista_skus
        
        for row in self.tabla_hist.get_children():
            self.tabla_hist.delete(row)
        cursor.execute("SELECT fecha_hora, codigo_sku, tipo_movimiento, cantidad, stock_anterior, stock_posterior, turno, motivo FROM historico_movimientos ORDER BY id_movimiento DESC")
        for h in cursor.fetchall():
            self.tabla_hist.insert("", tk.END, values=h)
            
        for row in self.tabla_tareas.get_children():
            self.tabla_tareas.delete(row)
        cursor.execute("SELECT id_tarea, descripcion, estado FROM tareas_operario WHERE estado != 'Hecha'")
        for t in cursor.fetchall():
            self.tabla_tareas.insert("", tk.END, values=t)
            
        conn.close()

    def procesar_operacion(self):
        sku = self.cmb_sku.get()
        tipo = self.cmb_tipo_mov.get()
        cant_raw = self.txt_cant.get()
        
        if not sku or not tipo or not cant_raw:
            messagebox.showerror("Error de Planta", "Operación cancelada: Todos los campos del formulario son obligatorios.")
            return
            
        try:
            cantidad = int(cant_raw)
            if cantidad < 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Error de Datos", "La cantidad ingresada debe ser un número entero positivo.")
            return
            
        conn = conectar_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT stock_actual, id_ubicacion FROM productos WHERE codigo_sku = ?", (sku,))
        producto = cursor.fetchone()
        stock_anterior = producto[0]
        ubicacion_fisica = producto[1]
        
        stock_posterior = stock_anterior
        vol_prod, p_malas = 0, 0
        motivo_registro = ""
        
        if tipo == "ENTRADA":
            stock_posterior = stock_anterior + cantidad
            cursor.execute("INSERT INTO tareas_operario (descripcion, fecha_creacion) VALUES (?, ?)",
                           (f"Ubicar {cantidad} uds de {sku} desde la zona de RECEPCIÓN hasta la estantería {ubicacion_fisica}", datetime.now().strftime("%Y-%m-%d %H:%M")))
            
        elif tipo == "SALIDA":
            if cantidad > stock_anterior:
                messagebox.showerror("Falta de Capacidad", f"Operación Denegada: No hay stock suficiente. Stock actual de {sku} es de {stock_anterior} unidades.")
                conn.close()
                return
            stock_posterior = stock_anterior - cantidad
            cursor.execute("INSERT INTO tareas_operario (descripcion, fecha_creacion) VALUES (?, ?)",
                           (f"Preparar salida de {cantidad} uds de {sku} desde ubicación {ubicacion_fisica} hacia la zona de EXPEDICIÓN", datetime.now().strftime("%Y-%m-%d %H:%M")))
            
        elif tipo == "PRODUCCIÓN":
            vol_prod = cantidad
            malas_raw = self.txt_malas.get()
            try:
                p_malas = int(malas_raw) if malas_raw else 0
                if p_malas < 0 or p_malas > vol_prod: raise ValueError()
            except ValueError:
                messagebox.showerror("Error de Calidad", "Las piezas malas no pueden ser negativas ni superar el volumen total producido.")
                conn.close()
                return
            
            piezas_buenas = vol_prod - p_malas
            stock_posterior = stock_anterior + piezas_buenas
            motivo_registro = f"Mermas detectadas en lote: {p_malas} uds."
            
        elif tipo == "REGULARIZACIÓN":
            stock_posterior = cantidad
            motivo_registro = self.cmb_motivo.get() if self.cmb_motivo.get() else "Recuento rutinario"
            
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        turno = obtener_turno()
        
        cursor.execute("UPDATE productos SET stock_actual = ?, fecha_ultimo_movimiento = ? WHERE codigo_sku = ?", (stock_posterior, ahora, sku))
        cursor.execute('''
            INSERT INTO historico_movimientos (fecha_hora, codigo_sku, tipo_movimiento, cantidad, stock_anterior, stock_posterior, volumen_producido, piezas_malas, operario, turno, motivo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ahora, sku, tipo, cantidad, stock_anterior, stock_posterior, vol_prod, p_malas, self.operador_actual, turno, motivo_registro))
        
        conn.commit()
        conn.close()
        
        realizar_backup_csv()
        
        messagebox.showinfo("Éxito Operativo", f"Registro asentado con éxito. Stock de {sku} actualizado de {stock_anterior} a {stock_posterior}.")
        
        self.txt_cant.delete(0, tk.END)
        self.txt_malas.delete(0, tk.END)
        self.refrescar_datos()

    def completar_tarea(self):
        seleccion = self.tabla_tareas.selection()
        if not seleccion:
            messagebox.showwarning("Atención", "Por favor, seleccione la tarea física que ha terminado de ejecutar.")
            return
            
        id_tarea = self.tabla_tareas.item(seleccion)['values'][0]
        
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE tareas_operario SET estado = 'Hecha' WHERE id_tarea = ?", (id_tarea,))
        conn.commit()
        conn.close()
        
        self.refrescar_datos()

if __name__ == "__main__":
    inicializar_db()
    app = AppAlmacen()
    app.mainloop()
