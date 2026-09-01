# Operación y mantenimiento

## Requisitos

### Uso del paquete portable

- Windows 10 build 20348 o posterior, en x64.
- Google Chrome abierto antes de iniciar y durante toda la grabación.
- El paquete completo: `Grabador de conferencias.exe`, `_runtime/` y `tools/` deben permanecer juntos.
- Espacio libre suficiente en la carpeta de destino para temporales y MP4 final.
- Acceso de aplicaciones de escritorio al micrófono solo cuando se active esa fuente opcional.

La aplicación no necesita privilegios de administrador, Python, una instalación externa de FFmpeg ni extensiones de Chrome.

### Desarrollo y construcción

- Python 3.11 o posterior.
- Windows x64 y PowerShell.
- Compilador C# disponible para `scripts/build-chrome-audio.ps1`.
- Acceso de red durante la construcción para descargar FFmpeg y las dependencias fijadas del entorno de empaquetado.

`pyproject.toml` declara Pillow `>=12.1,<13`. El script portable fija PyInstaller 6.21.0 y Pillow 12.1.1, descarga FFmpeg Essentials y conserva los avisos y licencias de terceros.

## Configuración de una sesión

La configuración es interactiva y no usa archivo de configuración ni variables de entorno:

| Opción | Valores admitidos | Valor inicial |
|---|---|---|
| Fuente | Pantalla principal, monitor completo, pestaña de Chrome | Pantalla principal |
| Resolución | 1280×720, 1920×1080 | 1920×1080 |
| Frecuencia | 30 o 60 FPS | 30 FPS |
| Micrófono | Dispositivo DirectShow detectado o ninguno | Desactivado |
| Destino | Carpeta local elegida por el usuario | `Videos/Grabador de conferencias` del perfil |

Los nombres siguen `Grabacion-AAAA-MM-DD-HHMMSS.mp4`; si ya existe cualquier archivo de la sesión, se añade un contador para evitar sobrescrituras.

## Ejecución desde código fuente

```powershell
python -m pip install -e .
python -m bizneo_recorder.main
```

El punto de entrada instalado es también `conference-recorder`. Desde el código fuente deben existir `tools/ffmpeg.exe` y `tools/chrome-audio-capture.exe` junto a la raíz que resuelve `main.py`.

## Diagnóstico

Ejecuta el autodiagnóstico sin abrir la interfaz:

```powershell
python -m bizneo_recorder.main --self-test
```

En el paquete portable:

```powershell
& '.\Grabador de conferencias.exe' --self-test
```

La comprobación informa de:

- disponibilidad del codificador H.264 de FFmpeg;
- compatibilidad del capturador de audio de Chrome;
- detección del proceso de Chrome;
- micrófonos DirectShow disponibles, si los hay.

El código de salida es 0 cuando H.264 y el capturador de audio por proceso están disponibles; Chrome y el micrófono pueden no estar presentes durante esta prueba.

## Pruebas y calidad

```powershell
python -m unittest discover -s tests -t . -v
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
```

La prueba rápida real de pantalla principal se encuentra en `scripts/smoke-recording.py`. `scripts/verify-recording.ps1` comprueba los streams del resultado con `ffprobe`. Estas comprobaciones requieren Windows, las herramientas laterales y, para una captura real, interacción y fuentes disponibles.

No presentes los resultados históricos de `verification.md` como una ejecución actual: registra siempre fecha, entorno y resultado nuevo.

## Construcción y entrega

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -ValidateOnly
```

La construcción:

1. descarga y extrae FFmpeg Essentials;
2. crea un entorno de build y fija PyInstaller y Pillow;
3. compila `chrome-audio-capture.exe` para x64;
4. empaqueta la aplicación con PyInstaller en modo `onedir`;
5. incorpora herramientas, asset HTML, guía y licencias;
6. valida el layout y ejecuta los autodiagnósticos;
7. genera `outputs/Grabador-de-conferencias-Portable.zip`.

Antes de entregar, valida el ZIP descomprimido y calcula su SHA-256. Distribuye el ZIP completo; un ejecutable aislado no funciona.

## Seguridad y privacidad

- Vídeo, audio, temporales y MP4 se procesan en el equipo local.
- El selector de Chrome usa un servidor efímero limitado a `127.0.0.1` y un token aleatorio de 32 bytes por sesión.
- El puente valida el tipo de superficie y exige audio al seleccionar una pestaña.
- Los fragmentos WebM están numerados, se aceptan de forma idempotente y tienen un límite de 16 MiB cada uno.
- El servidor no registra peticiones y la aplicación no envía telemetría, URL, títulos ni contenido a Internet.
- Los artefactos no están firmados comercialmente; SmartScreen puede mostrar una advertencia.
- El script de construcción rechaza borrados fuera de la raíz del proyecto y empaqueta avisos y licencias de FFmpeg y Pillow.

La aplicación graba contenido visible y audible. La autorización para grabar, la retención de los MP4 y el acceso a la carpeta de destino corresponden al procedimiento operativo de la organización; el programa no incorpora consentimiento, cifrado, control de acceso ni borrado automático.

## Observabilidad y soporte

No hay servicio, telemetría ni registro persistente. La observabilidad disponible es:

- estados y mensajes en la interfaz;
- salida de `--self-test`;
- código de salida de los procesos auxiliares;
- últimas líneas de diagnóstico de FFmpeg y del capturador de audio, que se trasladan al error mostrado;
- existencia y tamaño de archivos temporales.

Al investigar una incidencia, anota versión, build de Windows, modo, resolución, FPS, uso de micrófono, momento del fallo, texto exacto y resultado del autodiagnóstico. No adjuntes una grabación real salvo que exista autorización y sea imprescindible.

## Recuperación de incidencias

| Síntoma | Comprobación | Actuación |
|---|---|---|
| Chrome no está listo | Chrome abierto y proceso detectable | Abrir Chrome y pulsar **Comprobar** |
| Falta audio de pestaña | Superficie `browser` y audio compartido | Repetir la selección y activar **Compartir también el audio** |
| Se eligió una ventana | El modo monitor exige `displaySurface=monitor` | Repetir y elegir una pantalla completa |
| No aparece micrófono | Permiso de aplicaciones de escritorio y dispositivo conectado | Corregir permisos y pulsar **Actualizar** |
| Falla el autodiagnóstico | Presencia de `tools/`, H.264 y compatibilidad Windows | Restaurar el paquete completo o usar un equipo compatible |
| La grabación no finaliza | Espacio, temporales y últimas líneas del error | Conservar temporales; no sobrescribirlos y escalar con el diagnóstico |
| SmartScreen bloquea | Procedencia e integridad del ZIP | Comparar SHA-256 y continuar solo si el origen es de confianza |

Los temporales `.capture.mkv`, `.browser.webm`, `.chrome.wav`, `.microphone.wav` y `.part.mp4` se eliminan después de crear correctamente el MP4. Ante un fallo de finalización se conservan para diagnóstico o recuperación; no los borres hasta cerrar la incidencia.

## Mantenimiento

- Revisa compatibilidad al cambiar Windows, Chrome, FFmpeg, Pillow, PyInstaller o el helper C#.
- Mantén alineada la versión de `pyproject.toml`, README, guías y paquete.
- Actualiza hashes e integridad solo después de generar un artefacto nuevo.
- Conserva pruebas para los tres modos, con y sin micrófono, así como el protocolo local y la limpieza de recursos.
- Verifica manualmente la selección nativa de Chrome: por diseño no se puede automatizar la concesión del permiso.
- Revisa licencias y avisos cuando cambie cualquier dependencia distribuida.

## Limitaciones conocidas

- Solo Windows x64 compatible con Process Loopback.
- Chrome es obligatorio y debe seguir abierto.
- No captura una ventana individual, webcam ni aplicaciones externas a Chrome como fuente de audio principal.
- No ofrece anotación, edición, subida, almacenamiento remoto ni gestión del ciclo de vida del vídeo.
- En pantalla o monitor, el audio incluye el árbol audible de Chrome, no una única pestaña.
