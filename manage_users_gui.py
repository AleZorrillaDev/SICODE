import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Configuración de Entorno para importar módulos de la App
sys.path.append(os.getcwd())
try:
    from app.core.database import SessionLocal, Base, engine
    from app.modulos.auth.models import User
except ImportError:
    # Fallback si no encuentra los módulos (dev local sin estructura completa)
    pass
    
# ... imports remain ...
import json

# Archivo para guardar roles personalizados
ROLES_FILE = "roles.json"
DEFAULT_ROLES = ["Usuario", "Operador", "Administrador", "Supervisor", "Jefe"]

def load_roles():
    if os.path.exists(ROLES_FILE):
        try:
            with open(ROLES_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return DEFAULT_ROLES

def save_roles(roles_list):
    with open(ROLES_FILE, "w") as f:
        json.dump(roles_list, f)

# Asegurar que la BD existe
Base.metadata.create_all(bind=engine)

class UserEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Usuarios SICODE - Avanzado")
        self.root.geometry("1000x650")
        
        self.db = SessionLocal()
        self.selected_user_id = None
        self.roles = load_roles() # Cargar roles
        
        # --- Estilos ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", rowheight=25)
        
        # --- Layout Principal ---
        # Panel Izquierdo (Formulario)
        self.frame_form = ttk.LabelFrame(root, text="Detalles del Usuario", padding=15)
        self.frame_form.pack(side="left", fill="y", padx=10, pady=10)
        
        # Campos
        self.create_entry("ID (Auto):", "id", readonly=True)
        self.create_entry("Código:", "codigo")
        self.create_entry("Nombre:", "nombre")
        self.create_entry("Apellido:", "apellido")
        self.create_entry("Correo:", "correo")
        self.create_entry("Usuario (Login):", "username") 
        
        # --- CAMPO ROL CON BOTÓN DE EDICIÓN ---
        frame_rol = ttk.Frame(self.frame_form)
        frame_rol.pack(fill="x", pady=5)
        ttk.Label(frame_rol, text="Rol:").pack(anchor="w")
        
        self.role_var = tk.StringVar()
        self.combo_rol = ttk.Combobox(frame_rol, textvariable=self.role_var, values=self.roles)
        self.combo_rol.pack(side="left", fill="x", expand=True)
        self.entry_rol = self.combo_rol # Alias para compatibilidad con código anterior

        btn_edit_roles = ttk.Button(frame_rol, text="⚙", width=3, command=self.open_role_manager)
        btn_edit_roles.pack(side="right", padx=5)
        
        self.create_entry("Contraseña:", "password", show="*")
        
        # Botones Formulario
        btn_frame = ttk.Frame(self.frame_form)
        btn_frame.pack(fill="x", pady=20)
        
        ttk.Button(btn_frame, text="GUARDAR CAMBIOS", command=self.save_user).pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="LIMPIAR FORMULARIO", command=self.clear_form).pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="ELIMINAR USUARIO", command=self.delete_user).pack(fill="x", pady=5)
        
        # Panel Derecho (Lista)
        self.frame_list = ttk.LabelFrame(root, text="Lista de Usuarios", padding=10)
        self.frame_list.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # Treeview
        columns = ("id", "codigo", "nombre", "apellido", "correo", "username", "rol")
        self.tree = ttk.Treeview(self.frame_list, columns=columns, show="headings")
        
        self.tree.heading("id", text="ID")
        self.tree.column("id", width=30)
        self.tree.heading("codigo", text="Cód")
        self.tree.column("codigo", width=50)
        self.tree.heading("nombre", text="Nombre")
        self.tree.column("nombre", width=100)
        self.tree.heading("apellido", text="Apellido")
        self.tree.column("apellido", width=100)
        self.tree.heading("correo", text="Correo")
        self.tree.column("correo", width=150)
        self.tree.heading("username", text="Usuario Login")
        self.tree.column("username", width=100)
        self.tree.heading("rol", text="Rol")
        self.tree.column("rol", width=100)
        
        # Scrollbars
        ysb = ttk.Scrollbar(self.frame_list, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(self.frame_list, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        
        self.tree.pack(side="top", fill="both", expand=True)
        ysb.pack(side="right", fill="y")
        xsb.pack(side="bottom", fill="x")
        
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Cargar Datos Iniciales
        self.load_data()
        
    def create_entry(self, label_text, var_name, readonly=False, is_combo=False, values=[], show=None):
        frame = ttk.Frame(self.frame_form)
        frame.pack(fill="x", pady=5)
        
        ttk.Label(frame, text=label_text).pack(anchor="w")
        
        if is_combo:
            # state="normal" permite escribir texto libre
            entry = ttk.Combobox(frame, values=values, state="readonly" if readonly else "normal")
        else:
            entry = ttk.Entry(frame, show=show)
            if readonly:
                entry.config(state="readonly")
                
        entry.pack(fill="x")
        setattr(self, f"entry_{var_name}", entry)

    def load_data(self):
        # Limpiar
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Consultar
        users = self.db.query(User).all()
        for u in users:
            self.tree.insert("", "end", values=(u.id, u.codigo, u.nombre, u.apellido, u.correo, u.username, u.role))

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        vals = item['values']
        
        # Cargar en formulario
        self.selected_user_id = vals[0]
        
        self.set_entry("id", vals[0])
        self.set_entry("codigo", vals[1])
        self.set_entry("nombre", vals[2])
        self.set_entry("apellido", vals[3])
        self.set_entry("correo", vals[4])
        self.set_entry("username", vals[5]) # Cargar usuario actual
        self.set_entry("rol", vals[6])
        
        # Password no se muestra
        self.set_entry("password", "") 
        
    def set_entry(self, name, value):
        if not hasattr(self, f"entry_{name}"): return
        
        entry = getattr(self, f"entry_{name}")
        readonly = str(entry['state']) == 'readonly'
        if readonly:
            entry.config(state="normal")
        
        if isinstance(entry, ttk.Combobox):
            entry.set(value)
        else:
            entry.delete(0, tk.END)
            # Manejar None values
            text_val = str(value) if value is not None and value != 'None' else ""
            entry.insert(0, text_val)
            
        if readonly:
            entry.config(state="readonly")

    def clear_form(self):
        self.selected_user_id = None
        self.set_entry("id", "")
        self.set_entry("codigo", "")
        self.set_entry("nombre", "")
        self.set_entry("apellido", "")
        self.set_entry("correo", "")
        self.set_entry("username", "")
        self.set_entry("rol", "")
        self.set_entry("password", "")

    def save_user(self):
        nombre = self.entry_nombre.get().strip()
        correo = self.entry_correo.get().strip()
        username_input = self.entry_username.get().strip()
        
        if not nombre or not correo:
            messagebox.showerror("Error", "Nombre y Correo son obligatorios")
            return

        # Lógica de Username: Priorizar input manual, sino generar automático
        if username_input:
            final_username = username_input
        else:
            final_username = correo.split("@")[0]
            # Actualizar la vista del entry para mostrar lo generado
            self.set_entry("username", final_username)
        
        try:
            if self.selected_user_id:
                # EDITAR
                user = self.db.query(User).filter(User.id == self.selected_user_id).first()
                if user:
                    user.codigo = self.entry_codigo.get()
                    user.nombre = nombre
                    user.apellido = self.entry_apellido.get()
                    user.correo = correo
                    user.role = self.entry_rol.get() # Toma el valor textual libre
                    user.username = final_username
                    
                    pwd = self.entry_password.get()
                    if pwd: # Solo actualizar si escribió algo
                        user.password = pwd
                        
                    messagebox.showinfo("Éxito", f"Usuario {final_username} actualizado.")
            else:
                # CREAR NUEVO
                # Verificar duplicado de username
                existing = self.db.query(User).filter(User.username == final_username).first()
                if existing:
                    if not messagebox.askyesno("Advertencia", f"El usuario '{final_username}' ya existe. ¿Crear otro con el mismo nombre de usuario? (Probablemente fallará la BD)"):
                        return

                new_user = User(
                    codigo=self.entry_codigo.get(),
                    nombre=nombre,
                    apellido=self.entry_apellido.get(),
                    correo=correo,
                    role=self.entry_rol.get(),
                    username=final_username,
                    password=self.entry_password.get() or "123456",
                    is_active=True
                )
                self.db.add(new_user)
                messagebox.showinfo("Éxito", f"Usuario {final_username} creado.")
            
            self.db.commit()
            self.load_data()
            self.clear_form()
            
        except Exception as e:
            self.db.rollback()
            messagebox.showerror("Error de Base de Datos", f"Ocurrió un error:\n{str(e)}")

    def open_role_manager(self):
        """Abre ventana para gestionar lista de roles."""
        win = tk.Toplevel(self.root)
        win.title("Editar Lista de Roles")
        win.geometry("300x400")
        
        lbl = ttk.Label(win, text="Roles Disponibles:")
        lbl.pack(pady=5)
        
        listbox = tk.Listbox(win)
        listbox.pack(fill="both", expand=True, padx=10, pady=5)
        
        for r in self.roles:
            listbox.insert("end", r)
            
        frame_actions = ttk.Frame(win)
        frame_actions.pack(fill="x", padx=10, pady=10)
        
        entry_new = ttk.Entry(frame_actions)
        entry_new.pack(side="left", fill="x", expand=True)
        
        def add_role():
            val = entry_new.get().strip()
            if val and val not in self.roles:
                self.roles.append(val)
                listbox.insert("end", val)
                entry_new.delete(0, "end")
                save_roles(self.roles)
                self.combo_rol['values'] = self.roles # Actualizar combo principal
                
        def del_role():
            sel = listbox.curselection()
            if sel:
                val = listbox.get(sel[0])
                if val in self.roles:
                    self.roles.remove(val)
                    listbox.delete(sel[0])
                    save_roles(self.roles)
                    self.combo_rol['values'] = self.roles

        ttk.Button(frame_actions, text="+", width=3, command=add_role).pack(side="left", padx=5)
        ttk.Button(win, text="Eliminar Seleccionado", command=del_role).pack(fill="x", padx=10, pady=5)

    def delete_user(self):
        if not self.selected_user_id:
            messagebox.showwarning("Atención", "Selecciona un usuario de la lista primero.")
            return
            
        if messagebox.askyesno("Confirmar Eliminación", "¿Estás seguro de eliminar este usuario permanentemente?"):
            try:
                self.db.query(User).filter(User.id == self.selected_user_id).delete()
                self.db.commit()
                self.load_data()
                self.clear_form()
                messagebox.showinfo("Eliminado", "Usuario eliminado correctamente.")
            except Exception as e:
                self.db.rollback()
                messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = UserEditorApp(root)
    root.mainloop()
