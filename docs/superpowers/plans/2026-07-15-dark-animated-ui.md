# Plan de implementación de la interfaz oscura y animada

**Objetivo:** implementar la interfaz aprobada, traducir toda la experiencia al castellano y reconstruir un ZIP portable listo para RRHH sin alterar los tres flujos de captura.

**Arquitectura:** la lógica de grabación permanece en los módulos actuales. Un nuevo `ui.py` concentra paleta, interpolación de color y widgets `Canvas` reutilizables. `app.py` coordina estos widgets y los estados existentes. `browser_capture.html` replica el sistema visual con CSS y animaciones respetuosas con `prefers-reduced-motion`.

**Tecnología:** Python 3.11, Tkinter/ttk, HTML/CSS/JavaScript, unittest, Ruff, PyInstaller y PowerShell.

**Especificación:** `docs/superpowers/specs/2026-07-15-dark-animated-ui-design.md`.

---

### Tarea 1: contrato de idioma y modelo de fuentes

**Archivos:**

- Modificar: `tests/test_models.py`
- Modificar: `tests/test_main.py`
- Modificar: `src/bizneo_recorder/models.py`
- Modificar: `src/bizneo_recorder/main.py`

1. Cambiar las expectativas de fuente a `Pantalla completa`, `Elegir pantalla` y `Pestaña de Chrome` y exigir errores en castellano.
2. Añadir expectativas de autodiagnóstico y ayuda de CLI en castellano.
3. Ejecutar `python -m unittest tests.test_models tests.test_main -v` y confirmar el fallo por las etiquetas antiguas.
4. Traducir etiquetas, validaciones y autodiagnóstico.
5. Repetir las pruebas hasta obtener resultado correcto.
6. Commit: `feat: localize recorder model and diagnostics`.

### Tarea 2: primitivas visuales animadas

**Archivos:**

- Crear: `src/bizneo_recorder/ui.py`
- Crear: `tests/test_ui.py`

1. Escribir pruebas para interpolación cromática, rectángulos redondeados, selección de `CaptureCard`, control de estado de `AnimatedActionButton`, conmutación de `ToggleSwitch` y ciclo de `OrbitalRecorder`.
2. Ejecutar `python -m unittest tests.test_ui -v` y confirmar el error de importación.
3. Implementar la paleta y los widgets con teclado, foco, estados desactivados y cancelación limpia de callbacks `after`.
4. Repetir las pruebas y Ruff hasta que sean correctas.
5. Commit: `feat: add animated recorder UI primitives`.

### Tarea 3: integrar la nueva ventana y la carpeta de destino

**Archivos:**

- Modificar: `tests/test_app.py`
- Modificar: `src/bizneo_recorder/app.py`

1. Ampliar las pruebas para la jerarquía nueva, las tres tarjetas, textos en castellano, micrófono opcional, estados de acción/orbe y selección de carpeta.
2. Ejecutar `python -m unittest tests.test_app -v` y confirmar los fallos.
3. Reconstruir `_build_interface()` según la maqueta con barra superior, hero, tarjetas, paneles de opciones y CTA.
4. Inyectar el selector de carpeta para poder probarlo y actualizar `output_dir` y su resumen visual.
5. Conectar animaciones y estilos con las transiciones `IDLE`, preparación, `RECORDING`, parada, éxito y error.
6. Mantener los workers actuales y desactivar todos los controles relevantes durante la sesión.
7. Repetir `tests.test_app`, `tests.test_models` y Ruff.
8. Commit: `feat: redesign recorder window for HR`.

### Tarea 4: rediseñar el selector auxiliar de Chrome

**Archivos:**

- Modificar: `tests/test_browser_capture.py`
- Modificar: `src/bizneo_recorder/assets/browser_capture.html`

1. Añadir pruebas de `lang="es"`, textos españoles, variables de paleta, animaciones y `prefers-reduced-motion`, conservando las comprobaciones del protocolo.
2. Ejecutar `python -m unittest tests.test_browser_capture -v` y confirmar los fallos.
3. Sustituir la tarjeta clara por una pantalla grafito con orbe, instrucciones contextualizadas, CTA coral y estados accesibles.
4. Traducir todos los mensajes JavaScript sin modificar `getDisplayMedia`, `MediaRecorder`, el token ni el envío secuencial.
5. Repetir la prueba del puente completa.
6. Commit: `feat: redesign Chrome capture selector`.

### Tarea 5: completar la localización del runtime

**Archivos:**

- Modificar: `tests/test_app.py`
- Modificar: `tests/test_browser_capture.py`
- Modificar según resultados: `src/bizneo_recorder/chrome_audio.py`
- Modificar según resultados: `src/bizneo_recorder/ffmpeg.py`
- Modificar según resultados: `src/bizneo_recorder/processes.py`
- Modificar según resultados: `src/bizneo_recorder/recorder.py`
- Modificar según resultados: `native/chrome_audio_capture/ChromeAudioCapture.cs`

1. Buscar cadenas visibles no castellanas en `src`, el helper y el asset.
2. Añadir expectativas para cualquier mensaje que llegue a la UI.
3. Ejecutar las pruebas enfocadas y comprobar los fallos.
4. Traducir solo las cadenas orientadas al usuario; mantener identificadores y protocolos técnicos estables.
5. Ejecutar toda la suite.
6. Commit: `feat: complete Spanish runtime localization`.

### Tarea 6: documentación, versión y arquitectura

**Archivos:**

- Modificar: `README.md`
- Modificar: `docs/usage.md`
- Modificar: `docs/portable-readme.txt`
- Modificar: `docs/architecture.md`
- Modificar: `docs/verification.md`
- Modificar: `pyproject.toml`

1. Subir la versión a `3.0.0` por el rediseño completo de interacción y lenguaje.
2. Traducir la documentación mantenida al castellano.
3. Documentar `ui.py`, el flujo de animación, el cambio de carpeta, el diseño aprobado y las instrucciones exactas para RRHH.
4. Actualizar el árbol de `docs/architecture.md` y el recuento real de pruebas.
5. Ejecutar una búsqueda de restos de textos valencianos fuera de documentos históricos.
6. Commit: `docs: document Spanish animated UI`.

### Tarea 7: verificación visual y portable

**Archivos:**

- Modificar con resultados reales: `docs/verification.md`
- Regenerar: `outputs/Conference-Recorder-Portable/`
- Regenerar: `outputs/Conference-Recorder-Portable.zip`

1. Ejecutar:

   ```powershell
   python -m unittest discover -s tests -t . -v
   python -m ruff check src tests scripts
   python -m compileall -q src tests scripts
   ```

2. Abrir la aplicación real con dobles controlados de grabador/Chrome y capturar los estados inicial, micrófono activo y grabación para inspección visual.
3. Comparar la captura real con `docs/design/recorder-ui-concept.png`: composición, color, jerarquía, foco, recortes y legibilidad.
4. Corregir cualquier regresión y repetir pruebas.
5. Ejecutar `powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`.
6. Ejecutar el autodiagnóstico del ejecutable y `scripts/build-portable.ps1 -ValidateOnly`.
7. Calcular tamaño y SHA-256 del ZIP, anotarlos en `docs/verification.md` y comprobar el contenido.
8. Commit: `build: package animated Spanish recorder`.

