# Verificación de Grabador de conferencias

Fecha: 15 de julio de 2026

Versión: 3.0.1

Entorno: Windows 11 x64, pantalla principal 1920×1080

## Resultados automatizados

- `python -m unittest discover -s tests -t . -v`: 89 pruebas correctas y 0 fallos.
- `python -m ruff check src tests scripts`: sin errores.
- `python -m compileall -q src tests scripts`: compilación correcta.
- Sintaxis de `scripts/build-portable.ps1`: correcta.
- Las 12 pruebas del puente local cubren token, superficie, audio de pestaña, orden de fragmentos, reintento idempotente, límite de tamaño, inicio, parada, error y asset empaquetado.
- El helper C# x64 confirma Process Loopback, callback COM ágil y PCM 44,1 kHz estéreo de 16 bits.
- `scripts/build-portable.ps1`: construcción correcta con PyInstaller 6.21.0 en modo `onedir`.
- `scripts/build-portable.ps1 -ValidateOnly`: ejecutable, runtime, asset HTML, FFmpeg, helper, licencias de FFmpeg y Pillow, aviso y guía presentes.
- Autodiagnóstico del ejecutable compilado: código de salida 0.
- El layout portable incluye el runtime `PIL` y la prueba de render comprueba que las curvas generan píxeles intermedios de antialiasing.

Las pruebas de `ffmpeg.py` y `recorder.py` verifican las órdenes y el ciclo de recursos para pantalla completa, monitor elegido y pestaña de Chrome, con y sin micrófono. No se capturó contenido real del usuario durante esta verificación.

## Revisión visual e interacción

Se abrió y manipuló el `.exe` generado, no una ejecución desde el código fuente:

- Estado inicial: ventana de 922×842 px, Chrome detectado, pantalla completa seleccionada, micrófono desactivado, Full HD 1080p y 30 FPS.
- Micrófono activo: expansión animada a 922×912 px; selector de dispositivo, estado **Micrófono preparado**, calidad, carpeta, CTA y pie permanecen visibles sin recortes.
- Pestaña de Chrome: selección visual, ayuda contextual, resumen inferior y CTA cambian a **Elegir pestaña y grabar**.
- Se comprobaron contraste, jerarquía, espaciado, foco visual, estados activos y movimiento del orbe y de la onda.
- Tarjetas, iconos, conmutador, onda, CTA y orbe se renderizan a 2×–3× y se reducen con Lanczos; las diagonales y curvas del `.exe` dejan de mostrar el escalonado del `Canvas` nativo.
- Rendimiento medido en el entorno de verificación: 5,56 ms por frame para el orbe de 780×176 y 2,34 ms para el CTA de 840×64.
- La implementación conserva la composición, el grafito, el coral y el violeta de `docs/design/recorder-ui-concept.png`, adaptados a una ventana de escritorio más compacta.

El diálogo nativo de Chrome exige una elección humana por diseño del navegador. No se aceptó automáticamente ningún permiso ni se grabó una pantalla o pestaña real.

## Integridad del paquete

- Fuente del build Windows de FFmpeg: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`.
- SHA-256 del archivo de FFmpeg: `DB580001CAA24AC104C8CB856CD113A87B0A443F7BDF47D8C12B1D740584A2EC`.
- ZIP final: `Grabador-de-conferencias-Portable.zip`.
- Tamaño: 55.912.985 bytes.
- Entradas del ZIP: 965.
- SHA-256: `6A292B95BDE35A0D02728EB4A8096CECD60D91CA238018329B0FEC581EEA964C`.

## Limitaciones conocidas

- Requiere Windows 10 build 20348 o posterior.
- Chrome debe estar abierto antes de comenzar y continuar abierto durante la captura.
- En una pestaña hay que activar **Compartir también el audio** en el selector de Chrome.
- No existe modo de ventana individual; las opciones son pantalla principal, monitor completo o pestaña.
- El paquete no tiene firma comercial de código y Windows puede mostrar SmartScreen.
