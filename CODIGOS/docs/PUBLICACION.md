# Publicación del proyecto

Esta versión integra Google Forms/Sheets, informes mensuales y semanales y el rediseño de dashboard aprobado tras corregir R-01–R-04. Conserva pruebas, documentación técnica y evidencias con datos sintéticos.

Se excluyen archivos `.env`, credenciales JSON, almacenamiento de ejecución, credenciales de correo, ajustes personales de Obsidian e índices locales de código. Las rutas de usuario en registros se anonimizan. El archivo `requirements.lock.txt` utiliza `-e .` para evitar depender de una carpeta personal. La configuración pública está en `.env.example` y contiene valores de desarrollo y campos vacíos de integración.

La copia preparada para publicación se verificó con PostgreSQL desechable: **138 pruebas aprobadas**, seis avisos de deprecación; **Ruff limpio**; **ocho escenarios de Apps Script aprobados**. Resultados en `redesign/codex/evidencias/publish-pytest.txt`, `publish-ruff.txt` y `publish-apps-script.txt`.
