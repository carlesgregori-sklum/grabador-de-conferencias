# Arquitectura

## Visión general

Grabador de conferencias 3.0 es una aplicación Windows portable con tres fuentes de vídeo. Tkinter coordina el flujo y `ui.py` dibuja la interfaz oscura y sus animaciones con `Canvas`. La captura de la pantalla principal usa FFmpeg `gdigrab`; un monitor o una pestaña se obtienen con `getDisplayMedia` y `MediaRecorder` desde una página local abierta por Chrome. Un helper C# usa WASAPI Process Loopback cuando debe capturarse el audio de todo el árbol de Chrome.

```text
Grabador de conferencias
├── README.md
├── pyproject.toml
├── docs/
│   ├── architecture.md                 Este documento
│   ├── design/
│   │   └── recorder-ui-concept.png     Referencia visual aprobada
│   ├── usage.md                        Uso, privacidad y soporte
│   ├── portable-readme.txt             LEEME incluido en el ZIP
│   ├── verification.md                 Resultados y hashes
│   └── superpowers/                    Especificaciones y planes históricos
├── native/chrome_audio_capture/
│   └── ChromeAudioCapture.cs           WASAPI para árbol de procesos
├── scripts/
│   ├── build-chrome-audio.ps1          Compila el helper C# x64
│   ├── build-portable.ps1              PyInstaller, herramientas y ZIP
│   ├── launcher.py                     Entrada de PyInstaller
│   ├── smoke-recording.py              Prueba real de pantalla principal
│   └── verify-recording.ps1            Comprueba streams con ffprobe
├── src/bizneo_recorder/
│   ├── assets/browser_capture.html     Selector, MediaRecorder y envío local
│   ├── app.py                          Estado de producto y coordinación UI
│   ├── ui.py                           Paleta y widgets Canvas animados
│   ├── browser_capture.py              Servidor loopback y fragmentos
│   ├── chrome_audio.py                 Cliente y ciclo de vida del helper
│   ├── ffmpeg.py                       Captura y finalización por modo
│   ├── main.py                         Entrada, recursos y --self-test
│   ├── models.py                       Modos, configuración y rutas
│   ├── processes.py                    Árbol y ejecutable de Chrome
│   └── recorder.py                     Estado y propiedad de recursos
└── tests/                               87 pruebas Python, helper, UI y build
```

`work/` contiene compilaciones y muestras temporales. `outputs/` contiene el directorio portable y el ZIP. Ambas carpetas están ignoradas por Git y se regeneran.

## Flujo de interfaz

```text
Evento del usuario
      │
      ▼
app.py ── actualiza estado ──► ui.py / widgets Canvas
  │                              │
  ├── worker de inicio           ├── órbitas y pulso con root.after
  ├── worker de micrófonos       ├── selección y foco de tarjetas
  └── worker de finalización     └── CTA, conmutador y onda ambiental
```

Los widgets animados no poseen recursos de captura y no ejecutan trabajo bloqueante. Cada bucle usa `after`, conserva un único callback y lo cancela al destruirse. Las tarjetas ofrecen foco, teclado, marca y borde; la selección no depende solo del color.

`app.py` mantiene los estados de producto `LISTO`, preparación, grabación, guardado y error. Durante una sesión bloquea fuente, micrófono, calidad y carpeta sin bloquear el hilo principal. La ventana parte de una altura compacta de 810 px y anima su expansión a 880 px cuando aparecen los controles del micrófono, de modo que el CTA y el estado inferior nunca quedan recortados.

## Flujos de grabación

```text
Pantalla completa
  FFmpeg gdigrab ───────────────► .capture.mkv (H.264 + micrófono opcional)
  WASAPI árbol de Chrome ───────► .chrome.wav

Monitor elegido
  Chrome getDisplayMedia ───────► .browser.webm (vídeo)
  WASAPI árbol de Chrome ───────► .chrome.wav
  FFmpeg DirectShow opcional ───► .microphone.wav

Pestaña elegida
  Chrome getDisplayMedia ───────► .browser.webm (vídeo + audio de la pestaña)
  FFmpeg DirectShow opcional ───► .microphone.wav

Todos los modos
  FFmpeg finaliza ──► .part.mp4 ──► promoción atómica ──► .mp4
```

La pantalla principal codifica H.264 durante la captura y copia el vídeo en la pasada final. Las fuentes WebM se reescalan conservando proporción, se encajan en 720p o 1080p y se recodifican a H.264. El audio final es AAC estéreo a 44,1 kHz.

## Selector local de Chrome

`main.py` carga `assets/browser_capture.html` como recurso del paquete y crea un `BrowserCaptureBridge` por sesión. El puente:

- escucha solo en `127.0.0.1` sobre un puerto efímero;
- genera un token aleatorio de 32 bytes;
- abre Chrome con `--app=http://127.0.0.1:puerto/capture/token`;
- valida `displaySurface=monitor` o `displaySurface=browser`;
- exige una pista de audio para pestañas;
- recibe fragmentos WebM numerados, ordenados e idempotentes;
- limita cada fragmento a 16 MiB y no registra URL, título ni contenido;
- notifica la cancelación si se cierra la ventana auxiliar.

La página usa la misma paleta coral/violeta, animaciones CSS y `prefers-reduced-motion`. Chrome continúa controlando el selector nativo. No hay extensiones ni servidores externos.

## Responsabilidades

- `ui.py`: color, dibujo y widgets animados sin lógica de captura.
- `app.py`: experiencia, textos, selección de carpeta y coordinación asíncrona.
- `processes.py`: procesos de Chrome y ruta del ejecutable.
- `ChromeAudioCapture.cs`: PCM 44,1 kHz estéreo mediante `VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK`.
- `chrome_audio.py`: espera `READY`, parada y validación WAV.
- `browser_capture.py`: protocolo HTTP y archivo WebM.
- `ffmpeg.py`: órdenes deterministas y mezcla de audio.
- `recorder.py`: propietario único de procesos, puente y temporales.

## Construcción y distribución

`scripts/build-portable.ps1` compila el helper x64, incorpora el build Essentials de FFmpeg, crea un paquete PyInstaller `onedir`, ejecuta autodiagnósticos, valida el layout y genera `outputs/Grabador-de-conferencias-Portable.zip`.

El modo `onedir` evita la extracción temporal de Tcl/Tk. `Grabador de conferencias.exe`, `_runtime/` y `tools/` forman una unidad portable y deben mantenerse juntos. `LEEME.txt` explica el uso a RRHH.

## Compatibilidad y limitaciones

- Windows 10 build 20348 o posterior.
- Chrome debe estar abierto antes y durante la captura.
- No existe captura de una ventana individual, webcam, anotaciones ni edición.
- Pantalla y monitor mezclan todas las pestañas audibles del árbol de Chrome.
- La pestaña necesita **Compartir también el audio**.
- El ejecutable no tiene una firma comercial y puede activar SmartScreen.
