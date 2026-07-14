# Arquitectura

## Visió general

Bizneo Recorder és una aplicació Windows portàtil escrita en Python. Tkinter presenta la interfície i un executable FFmpeg separat realitza la captura de pantalla, la lectura del micròfon i la codificació MP4. PyInstaller empaqueta Python i la interfície en un únic executable; FFmpeg queda com a binari adjacent per reduir el temps d’arrancada i mantindre visible la seua llicència.

```text
Bizneo Recorder
├── README.md                         Resum del projecte i ordres principals
├── pyproject.toml                    Metadades del paquet Python
├── docs/
│   ├── architecture.md               Este document
│   ├── usage.md                      Ús, privacitat i resolució de problemes
│   ├── portable-readme.txt           Guia inclosa en el ZIP
│   └── superpowers/                  Especificació i pla d’implementació
├── scripts/
│   ├── build-portable.ps1            Descàrrega, construcció, validació i ZIP
│   ├── launcher.py                   Punt d’entrada per a PyInstaller
│   ├── smoke-recording.py            Gravació curta de verificació
│   └── verify-recording.ps1          Inspecció dels streams resultants
├── src/bizneo_recorder/
│   ├── app.py                        Interfície i coordinació asíncrona
│   ├── ffmpeg.py                     Dispositius DirectShow i comandes FFmpeg
│   ├── main.py                       Entrada GUI i mode --self-test
│   ├── models.py                     Configuració i rutes d’eixida
│   └── recorder.py                   Estat, procés i finalització segura
└── tests/                             Proves unitàries dels mòduls anteriors
```

`work/` conté descàrregues, entorns i artefactes temporals. `outputs/` conté el paquet portable generat. Ambdues carpetes estan ignorades per Git.

## Flux principal

```text
Usuari
  │ selecciona micròfon i inicia
  ▼
app.py ── RecordingConfig ──► recorder.py
                                  │ construeix arguments
                                  ▼
                              ffmpeg.py
                                  │ executa FFmpeg
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
             gdigrab: pantalla          dshow: micròfon
                    └─────────────┬─────────────┘
                                  ▼
                         fitxer `.part.mp4`
                                  │ eixida 0 i parada amb `q`
                                  ▼
                              fitxer `.mp4`
```

La interfície executa la detecció, l’inici i l’aturada en fils de treball curts; totes les actualitzacions visuals tornen al fil de Tk amb `after`. `Recorder` és l’únic propietari del procés FFmpeg i impedeix dues gravacions simultànies.

## Decisions tècniques

- `gdigrab` captura exclusivament l’escriptori principal; `dshow` rep exclusivament el nom del micròfon triat.
- La resolució final és fixa a 1920×1080 amb escalat proporcional i farciment, evitant deformacions.
- El fitxer de treball usa `.part.mp4`. Només una eixida correcta de FFmpeg provoca el canvi atòmic al nom final.
- Els diagnòstics de FFmpeg es drenen en un fil daemon amb memòria limitada, evitant bloquejos per ompliment del pipe.
- El mode `--self-test` evita obrir la GUI i valida el còdec H.264 i la detecció de micròfons.

## Construcció

`scripts/build-portable.ps1` descarrega el build Essentials de Gyan que figura a la pàgina oficial de descàrregues de FFmpeg, registra el SHA-256, crea un entorn de construcció a `work`, usa PyInstaller 6.21.0 i valida l’estructura abans de comprimir-la.

No s’han d’editar manualment els artefactes de `outputs`; cal reconstruir-los amb el script.

## Limitacions conegudes

- Només grava la pantalla principal.
- No captura webcam, àudio del sistema ni anotacions.
- La gravació està optimitzada per a 1920×1080; pantalles amb una altra proporció poden mostrar bandes de farciment.
- L’executable no té una signatura de codi comercial i Windows pot mostrar SmartScreen la primera vegada.

