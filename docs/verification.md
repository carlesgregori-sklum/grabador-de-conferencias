# Verificació de Conference Recorder

Data: 15 de juliol de 2026

Versió: 2.1.0

Entorn: Windows 11 x64, pantalla principal 1920×1080

## Resultats automatitzats

- `python -m unittest discover -s tests -t . -v`: 76 proves correctes.
- `python -m ruff check src tests scripts`: cap error.
- `python -m compileall -q src tests scripts`: compilació correcta.
- Sintaxi de `scripts/build-portable.ps1`: correcta.
- 12 proves del pont loopback: token, superfície, àudio de pestanya, ordenació, reintent idempotent, límit de fragment, inici, parada, error i asset.
- Helper C# x64: `Process loopback: supported`, callback COM àgil i PCM 44,1 kHz estèreo de 16 bits.
- `scripts/build-portable.ps1`: construcció correcta amb PyInstaller 6.21.0 en mode `onedir`.
- `scripts/build-portable.ps1 -ValidateOnly`: executable, runtime, asset HTML, FFmpeg, helper, llicència, avís i guia presents.
- L’asset empaquetat conté la notificació `navigator.sendBeacon` usada quan es tanca el selector.

## Integració de vídeo i àudio

S’han generat fonts audiovisuals sintètiques, sense capturar dades de l’usuari, i s’han passat per les ordres FFmpeg reals de la versió 2.1.0:

- Monitor seleccionat simulat: WebM de vídeo + WAV de Chrome + WAV de micròfon.
- Pestanya simulada: WebM amb vídeo i àudio de pestanya, sense helper d’àudio global.
- Els dos resultats són MP4 de 2,000 segons, H.264 1280×720 a 30 FPS i AAC.
- `scripts/verify-recording.ps1` ha validat exactament un stream de vídeo i un d’àudio en cada fitxer.

El diàleg natiu de compartició de Chrome requereix una elecció humana per disseny del navegador. No s’ha acceptat automàticament cap permís ni s’ha gravat una pantalla o pestanya real de l’usuari durant esta verificació.

## Revisions visuals

- Arrancada neta del portable sense diàlegs d’error.
- Finestra de 582×822 píxels sense retalls ni scroll.
- Chrome detectat, micròfon desactivat, 1080p i 30 FPS com a estat inicial.
- Els tres modes són visibles alhora i el botó principal indica **Gravar pantalla principal**.
- La pàgina auxiliar de pestanya conserva la mateixa jerarquia visual, instruïx sobre **Compartir també l’àudio** i mostra estat accessible.
- Controls, textos d’ajuda, contrast, focus i jerarquia són coherents amb la UI existent.

## Integritat del paquet

- Font del build Windows de FFmpeg: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`.
- SHA-256 de l’arxiu FFmpeg: `DB580001CAA24AC104C8CB856CD113A87B0A443F7BDF47D8C12B1D740584A2EC`.
- ZIP final: 48.234.865 bytes.
- SHA-256 de `Conference-Recorder-Portable.zip`: `3533D973752D13631BAAB0A922EDB8B6BA483060CE1DA770B7F6D74A4683C8FE`.

## Limitacions conegudes

- Windows 10 build 20348 o posterior.
- Chrome ha d’estar obert abans de començar i continuar obert durant la captura.
- La pestanya necessita **Compartir també l’àudio**.
- No hi ha mode de finestra individual; les opcions són pantalla principal, monitor complet o pestanya.
- El paquet no té signatura comercial de codi.
