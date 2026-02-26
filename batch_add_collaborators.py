import sys
import os

# Configuración de Entorno para importar módulos de la App
sys.path.append(os.getcwd())
try:
    from app.core.database import SessionLocal
    from app.modulos.auth.models import User
except ImportError:
    print("Error: No se pudo importar la configuración de la base de datos.")
    sys.exit(1)

collaborators = [
    ("Anco Huaranga", "Rody Nilver", "ranco@sunat.gob.pe"),
    ("Ayala Morales", "Lia Lucy", "layala@sunat.gob.pe"),
    ("Cairo Diaz", "Jimmy", "jcairodi@sunat.gob.pe"),
    ("Carreño Ordaya", "Gladys", "gcarren1@sunat.gob.pe"),
    ("Cerron Gomez", "Vito", "vcerron@sunat.gob.pe"),
    ("Cipriano Castro", "Aldo", "acipriano@sunat.gob.pe"),
    ("Com Machuca", "George", "gcom@sunat.gob.pe"),
    ("Cordova Meza", "Luis", "lcordova@sunat.gob.pe"),
    ("Enriquez Jimenez", "Lidia", "lenrique@sunat.gob.pe"),
    ("Fernandez Calixto", "Brayan", "bfernandezca@sunat.gob.pe"),
    ("Fierro Flores", "Nelya", "nfierro@sunat.gob.pe"),
    ("Flores Arias", "Jhogan", "jfloresa@sunat.gob.pe"),
    ("Galvez Sanchez", "Angelica", "agalvez@sunat.gob.pe"),
    ("Gomez Escobar", "Dante", "dgomeze@sunat.gob.pe"),
    ("Huaman Espinoza", "Luis", "lhuamane@sunat.gob.pe"),
    ("Huaman Lazon", "Gabriel", "ghuamanl@sunat.gob.pe"),
    ("Huaman Mendoza", "Ana", "ahuamanmen@sunat.gob.pe"),
    ("Huanca Rondinel", "Karen", "khuanca@sunat.gob.pe"),
    ("Huayhua Almonacid", "Melissa", "mhuayhua@sunat.gob.pe"),
    ("Lazo Segura", "Olga", "olazos@sunat.gob.pe"),
    ("Lopez Miguel", "Miriam", "mlopez3@sunat.gob.pe"),
    ("Lujan Muñoz", "Raul", "rlujanm@sunat.gob.pe"),
    ("Miranda Cuyubamba", "Claudia", "cmirandac@sunat.gob.pe"),
    ("Montes Tovar", "Nestor", "wmontes@sunat.gob.pe"),
    ("Munive Jimenez", "Lourdes", "lmunive@sunat.gob.pe"),
    ("Pereira Ludeña", "Martha", "mpereiral@sunat.gob.pe"),
    ("Pereyra Castro", "Moises", "mpereyrac@sunat.gob.pe"),
    ("Quispe Moreno", "Erika", "equispemor@sunat.gob.pe"),
    ("Quispialaya Rojas", "Diego", "dquispialayar@sunat.gob.pe"),
    ("Ricardo Anchante", "Carlos", "cricardoa@sunat.gob.pe"),
    ("Rios Colqui", "Eli", "erios@sunat.gob.pe"),
    ("Sanabria Carhuamaca", "Julia", "jsanabri@sunat.gob.pe"),
    ("Trinidad Yanayaco", "William", "wtrinidad@sunat.gob.pe"),
    ("Villanes Alcantara", "Fanny", "fvillanesa@sunat.gob.pe")
]

def batch_add():
    db = SessionLocal()
    added_count = 0
    try:
        for apellido, nombre, correo in collaborators:
            username = correo.split("@")[0]
            
            # Verificar si ya existe
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                print(f"Saltando {username}: ya existe.")
                continue
            
            new_user = User(
                nombre=nombre,
                apellido=apellido,
                correo=correo,
                username=username,
                password="123456",
                role="Colaborador",
                is_active=True
            )
            db.add(new_user)
            added_count += 1
        
        db.commit()
        print(f"Éxito: Se agregaron {added_count} colaboradores.")
    except Exception as e:
        db.rollback()
        print(f"Error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    batch_add()
