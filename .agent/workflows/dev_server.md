---
description: Iniciar el servidor de desarrollo con recarga automática de JS, CSS y HTML
---

// turbo-all

1. Activa el entorno virtual e inicia uvicorn con watchfiles para detectar cambios en `.js`, `.css` y `.html`:

```
venv\Scripts\activate; uvicorn app.main:app --reload --reload-include "*.js" --reload-include "*.css" --reload-include "*.html"
```

> **Nota**: Este comando requiere `watchfiles` instalado (`pip install watchfiles`).
> Con este modo, cualquier cambio en JS/CSS/HTML reinicia el servidor automáticamente,
> actualizando el `BUILD_VERSION` y limpiando el caché del browser con solo F5.
