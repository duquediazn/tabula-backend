from app.models.user import User
import unicodedata

def is_admin_user(user: User) -> bool:
    """Devuelve True si el usuario es administrador, False en caso contrario."""
    return user.rol.lower() == "admin"


def normalize_category(categoria: str) -> str:
    """Normaliza el nombre de la categoría:
    - Elimina tildes
    - Capitaliza la primera letra
    - Elimina espacios extra
    """
    categoria = categoria.strip()  # Elimina espacios
    categoria = ''.join(
        c for c in unicodedata.normalize('NFD', categoria) if unicodedata.category(c) != 'Mn'
    )  # Elimina tildes
    return categoria.capitalize()

'''
unicodedata.normalize('NFD', categoria)

NFD significa "Normalización de Forma de Descomposición".
Separa los caracteres acentuados en dos partes:
- Carácter base (Ej: "e")
- Carácter de tilde (Ej: "´")

Salida: E l e c t r o ´ n i c a

if unicodedata.category(c) != 'Mn'

unicodedata.category(c) devuelve la categoría Unicode del carácter.
"Mn" significa "Mark, Nonspacing" (es decir, tildes, diéresis, etc.).
La condición != 'Mn' filtra y elimina los caracteres de tildes

''.join(...)

Junta todos los caracteres filtrados en una cadena nueva sin tildes.
'''