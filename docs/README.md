# Documentación técnica

Esta carpeta reúne la documentación técnica de **Grabador de conferencias 3.0.1**, una aplicación portable para Windows que captura pantalla, monitor o pestaña de Chrome y genera un MP4 local.

## Índice

- [Arquitectura](architecture.md): componentes, responsabilidades, flujos de captura, codificación y distribución.
- [Operación y mantenimiento](operations.md): requisitos, configuración, construcción, diagnóstico, seguridad, incidencias y actualización.
- [Uso](usage.md): recorrido funcional, privacidad y resolución de problemas orientada a soporte.
- [Verificación](verification.md): pruebas realizadas, entorno, integridad del paquete y limitaciones comprobadas.
- [LEEME del paquete portable](portable-readme.txt): instrucciones incluidas en la entrega a usuarios.
- [Diseño](design/): referencia visual del producto.
- [Especificaciones y planes históricos](superpowers/): decisiones de diseño e implementación conservadas como contexto; no sustituyen a la documentación vigente.

## Mapa del sistema

| Área | Implementación principal | Responsabilidad |
|---|---|---|
| Interfaz y coordinación | `src/bizneo_recorder/app.py`, `ui.py` | Estado de la sesión, opciones, mensajes y trabajo asíncrono |
| Modelo de sesión | `models.py` | Modos, resolución, FPS, micrófono y rutas de archivos |
| Captura de pantalla | `ffmpeg.py` | `gdigrab`, DirectShow, mezcla y MP4 final |
| Captura de monitor o pestaña | `browser_capture.py`, `assets/browser_capture.html` | Selector nativo de Chrome y recepción local de WebM |
| Audio de Chrome | `chrome_audio.py`, `native/chrome_audio_capture/` | Captura WASAPI del árbol de procesos de Chrome |
| Ciclo de vida | `recorder.py` | Propiedad de procesos, parada, validación, promoción atómica y limpieza |
| Empaquetado | `scripts/build-portable.ps1` | Helper nativo, FFmpeg, PyInstaller, licencias, validaciones y ZIP |

## Alcance y fuentes de verdad

El código de `src/`, `native/` y `scripts/` es la fuente de verdad del comportamiento. `README.md` y `docs/usage.md` describen el producto desde el punto de vista funcional. Los documentos de `docs/superpowers/` son históricos y pueden reflejar estados anteriores.

No existe una API pública ni un servicio remoto: la única interfaz HTTP es temporal, escucha en `127.0.0.1` y pertenece a una sola sesión de selección de monitor o pestaña.

## Cambios en el producto

Al modificar fuentes, dependencias o empaquetado:

1. Actualiza la versión en `pyproject.toml` y la documentación que la muestre.
2. Ejecuta pruebas, análisis estático y compilación de bytecode.
3. Genera y valida el paquete portable en Windows.
4. Ejecuta el autodiagnóstico del ejecutable compilado.
5. Actualiza `verification.md` solo con resultados realmente obtenidos, incluyendo fecha, entorno, versión y huellas del artefacto cuando proceda.
6. Verifica manualmente al menos los flujos afectados y conserva la descripción de limitaciones conocida.

Consulta [Operación y mantenimiento](operations.md) para los comandos y criterios concretos.
