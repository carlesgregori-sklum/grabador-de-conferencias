# Arquitectura

## Visió general

Conference Recorder és una aplicació Windows portable amb tres fonts de vídeo. Tkinter presenta la UI i coordina treball en segon pla. La pantalla principal usa FFmpeg `gdigrab`; un monitor o una pestanya s’obtenen amb `getDisplayMedia` i `MediaRecorder` des d’una pàgina local oberta per Chrome. El micròfon és opcional. Un helper C# usa WASAPI Process Loopback quan cal capturar l’àudio de tot l’arbre de Chrome.

```text
Conference Recorder
├── README.md
├── pyproject.toml
├── docs/
│   ├── architecture.md                 Este document
│   ├── usage.md                        Ús, privacitat i problemes
│   ├── portable-readme.txt             Guia inclosa en el ZIP
│   ├── verification.md                 Resultats i hashes
│   └── superpowers/                    Especificacions i plans
├── native/chrome_audio_capture/
│   └── ChromeAudioCapture.cs           WASAPI per arbre de processos
├── scripts/
│   ├── build-chrome-audio.ps1          Compila el helper C# x64
│   ├── build-portable.ps1              PyInstaller, eines, assets i ZIP
│   ├── launcher.py                     Entrada de PyInstaller
│   ├── smoke-recording.py              Prova real de pantalla principal
│   └── verify-recording.ps1            Comprova streams amb ffprobe
├── src/bizneo_recorder/
│   ├── assets/browser_capture.html     Selector, MediaRecorder i enviament local
│   ├── app.py                          UI i coordinació asíncrona
│   ├── browser_capture.py              Servidor loopback i protocol de fragments
│   ├── chrome_audio.py                 Client i lifecycle del helper
│   ├── ffmpeg.py                       Dispositius, captura i finalització per mode
│   ├── main.py                         Entrada, recursos i --self-test
│   ├── models.py                       Modes, configuració i rutes de sessió
│   ├── processes.py                    Arrel i executable de Chrome
│   └── recorder.py                     Estat i propietat de tots els recursos
└── tests/                               76 proves Python/helper/UI/build
```

`work/` conté compilacions i mostres temporals. `outputs/` conté el directori portable i el ZIP. Les dos carpetes estan ignorades per Git.

## Fluxos de gravació

```text
Pantalla principal
  FFmpeg gdigrab ───────────────► .capture.mkv (H.264 + mic opcional)
  WASAPI arbre de Chrome ───────► .chrome.wav

Monitor seleccionat
  Chrome getDisplayMedia ───────► .browser.webm (vídeo)
  WASAPI arbre de Chrome ───────► .chrome.wav
  FFmpeg DirectShow opcional ───► .microphone.wav

Pestanya seleccionada
  Chrome getDisplayMedia ───────► .browser.webm (vídeo + àudio de la pestanya)
  FFmpeg DirectShow opcional ───► .microphone.wav

Totes les variants
  FFmpeg finalitza ─► .part.mp4 ─► promoció atòmica ─► .mp4
```

La pantalla principal codifica H.264 durant la captura i copia el vídeo en la passada final. Les fonts WebM de Chrome es reescalen amb proporció conservada, s’encaixen en 720p o 1080p i es recodifiquen a H.264. L’àudio final és AAC estèreo a 44,1 kHz.

## Selector local de Chrome

`main.py` carrega `assets/browser_capture.html` com a recurs del paquet i crea un `BrowserCaptureBridge` per sessió. El pont:

- escolta només en `127.0.0.1` sobre un port efímer;
- genera un token aleatori de 32 bytes per protegir les rutes;
- obri Chrome amb `--app=http://127.0.0.1:port/capture/token`;
- valida `displaySurface=monitor` o `displaySurface=browser` segons el mode;
- exigeix pista d’àudio per a pestanyes;
- rep fragments WebM numerats, ordenats i amb reintents idempotents;
- limita cada fragment a 16 MiB i no registra URL, títol ni contingut;
- notifica cancel·lació si es tanca la finestra auxiliar.

El navegador continua sent qui mostra i controla el selector natiu. No hi ha extensió ni servidor extern.

## Responsabilitats

- `processes.py` enumera processos amb Tool Help, tria l’arbre de Chrome més gran i obté la ruta executable amb `QueryFullProcessImageNameW`.
- `ChromeAudioCapture.cs` captura PCM 44,1 kHz estèreo mitjançant `VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK`.
- `chrome_audio.py` espera `READY`, controla parada i valida la capçalera WAV.
- `browser_capture.py` manté l’estat del protocol HTTP, les condicions d’inici/parada i el fitxer WebM.
- `ffmpeg.py` construeix ordres deterministes per cada mode i mescla el micròfon quan està actiu.
- `recorder.py` és l’únic propietari dels processos, el pont i els temporals; només elimina intermedis després d’una finalització correcta.
- `app.py` manté la UI responsiva amb workers, no enumera micròfons fins que l’usuari ho demana i bloqueja controls durant la sessió.

## Construcció

`scripts/build-portable.ps1` compila el helper x64, descarrega el build Essentials de FFmpeg, crea un paquet PyInstaller `onedir`, incorpora `browser_capture.html` en `_runtime/bizneo_recorder/assets`, copia les eines a `tools/`, executa autodiagnòstics, valida el layout i genera `outputs/Conference-Recorder-Portable.zip`.

El mode `onedir` evita l’extracció temporal de Tcl/Tk. L’executable i les carpetes `_runtime/` i `tools/` formen una unitat portable i s’han de mantindre juntes. Els artefactes d’`outputs/` es reconstrueixen; no s’editen manualment.

## Compatibilitat i limitacions

- Windows 10 build 20348 o posterior.
- Chrome ha d’estar obert abans de començar i mantindre’s obert.
- El selector permet pantalla completa o pestanya, no una finestra individual.
- En pantalla principal o monitor, diverses pestanyes de Chrome audibles poden mesclar-se.
- En mode pestanya només entra l’àudio de la pestanya si s’activa **Compartir també l’àudio**.
- No captura webcam, anotacions ni altres navegadors.
- L’executable no té signatura comercial i pot activar SmartScreen.
