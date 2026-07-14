# Verificació de la versió 1.0.0

Data: 14 de juliol de 2026  
Entorn: Windows 11 Pro x64, pantalla principal 1920×1080

## Resultats

- `python -m unittest discover -s tests -t . -v`: 17 proves, 17 correctes.
- `ruff check src tests scripts`: cap error.
- `python -m compileall -q src scripts tests`: compilació correcta.
- Anàlisi de sintaxi dels scripts PowerShell: correcta.
- `scripts/build-portable.ps1`: construcció PyInstaller 6.21.0 correcta.
- Validació de l’estructura portable: executable, FFmpeg, avís, llicència i guia presents.
- `Bizneo Recorder.exe --self-test`: codi d’eixida 0, H.264 disponible i almenys un micròfon detectat.
- ZIP descomprimit en una carpeta neta: `--self-test` torna a finalitzar amb codi 0.
- Gravacions reals curtes: H.264 a 1920×1080, àudio AAC i duracions positives de 2,766667 i 1,633333 segons.
- La gravació temporal de verificació s’ha eliminat després d’inspeccionar els streams perquè contenia pantalla i veu reals.

## Integritat de dependències i paquet

- Font del build Windows de FFmpeg: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`, enllaçada des de `ffmpeg.org/download.html`.
- SHA-256 de l’arxiu FFmpeg descarregat: `DB580001CAA24AC104C8CB856CD113A87B0A443F7BDF47D8C12B1D740584A2EC`.
- SHA-256 del ZIP portable final: `0BEA6B17C7C9500B1DBA7BBB3EDB5AA1E8AF19F02E21D6025864A9824FD924DB`.

## Revisió visual

La connexió de control d’aplicacions de Windows va expirar dues vegades en intentar obrir la GUI, de manera que no es va obtindre una captura visual fiable. No es van executar clics amb coordenades no verificades. La finestra sí queda coberta indirectament per la importació de Tkinter, la compilació PyInstaller, el mode de diagnòstic de l’executable i la revisió estàtica del codi; la inspecció visual manual continua sent l’única comprovació no automatitzada.
