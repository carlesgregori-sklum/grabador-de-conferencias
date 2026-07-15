# Arquitectura

## Visió general

Conference Recorder és una aplicació Windows portable. Tkinter presenta la UI; FFmpeg captura tota la pantalla principal i, opcionalment, DirectShow llig el micròfon. Un helper C# usa WASAPI Process Loopback per capturar només l’àudio de l’arbre de processos de Chrome. Una passada final de FFmpeg combina les fonts en un MP4.

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
│   ├── build-portable.ps1              PyInstaller, eines, validació i ZIP
│   ├── launcher.py                     Entrada de PyInstaller
│   ├── smoke-recording.py              Gravació real curta
│   └── verify-recording.ps1            Comprova streams amb ffprobe
├── src/bizneo_recorder/
│   ├── app.py                          UI i coordinació asíncrona
│   ├── chrome_audio.py                 Client/lifecycle del helper
│   ├── ffmpeg.py                       Dispositius i ordres FFmpeg
│   ├── main.py                         Entrada i --self-test
│   ├── models.py                       Configuració i rutes de sessió
│   ├── processes.py                    Detecció de l’arrel de Chrome
│   └── recorder.py                     Estat i finalització segura
└── tests/                               47 proves Python/helper/UI/build
```

`work/` conté compilacions i mostres temporals. `outputs/` conté el directori portable i el ZIP. Ambdues carpetes estan ignorades per Git.

## Flux principal

```text
Usuari prem Gravar conferència
        │
        ▼
processes.py ──► PID arrel chrome.exe
        │
        ▼
chrome_audio.py ──► chrome-audio-capture.exe
        │                  │
        │                  └─ WASAPI includetree ─► .chrome.wav
        ▼
recorder.py ──► FFmpeg gdigrab ─► .capture.mkv
                         └─ dshow micròfon opcional

Usuari prem Finalitzar
        │
        ├─ parada ordenada amb q
        ├─ FFmpeg copia H.264 i codifica AAC
        ├─ Chrome sol o Chrome + micròfon amb amix
        ▼
  .part.mp4 ── promoció atòmica ──► .mp4
```

## Límits i responsabilitats

- `processes.py` usa Tool Help per enumerar processos sense PowerShell ni WMI. Si hi ha diverses arrels de Chrome, tria determinísticament l’arbre amb més descendents.
- `ChromeAudioCapture.cs` rep PID i ruta WAV, exposa un callback COM àgil i captura PCM 44,1 kHz estèreo mitjançant `VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK`.
- `chrome_audio.py` espera el senyal `READY`, controla temps límit i parada, i valida la capçalera WAV.
- `ffmpeg.py` separa la captura intermèdia de la combinació final. El vídeo es codifica una sola vegada; la passada final usa `-c:v copy`.
- `recorder.py` és l’únic propietari dels dos processos. Els temporals només s’eliminen després d’una finalització correcta.
- `app.py` no enumera micròfons fins que l’usuari activa l’opció.

## Construcció

`scripts/build-chrome-audio.ps1` usa el compilador x64 inclòs en .NET Framework. `scripts/build-portable.ps1` descarrega el build Essentials de FFmpeg, crea un paquet PyInstaller `onedir`, copia el runtime Python a `_runtime/`, copia les dos eines a `tools/`, executa i espera els autodiagnòstics i genera `outputs/Conference-Recorder-Portable.zip`.

El mode `onedir` evita l’extracció temporal de Tcl/Tk a cada arrancada. L’executable i les carpetes `_runtime/` i `tools/` formen una sola unitat portable i s’han de mantindre juntes.

No s’han d’editar manualment els artefactes d’`outputs`; cal reconstruir-los.

## Compatibilitat i limitacions

- Windows 10 build 20348 o posterior.
- Captura tota la pantalla principal, no una finestra o pestanya.
- Captura tot l’àudio de l’arbre de Chrome; diverses pestanyes actives poden mesclar-se.
- Chrome ha d’estar obert abans de començar i continuar obert.
- No captura webcam, anotacions ni altres navegadors.
- L’executable no té signatura comercial i pot activar SmartScreen.
