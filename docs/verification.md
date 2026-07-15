# Verificació de Conference Recorder

Data: 15 de juliol de 2026
Entorn: Windows 11 x64, pantalla principal 1920×1080

## Resultats automatitzats

- `python -m unittest discover -s tests -p "test_*.py" -v`: 47 proves correctes.
- `python -m ruff check src tests scripts`: cap error.
- `python -m compileall -q src tests scripts`: compilació correcta.
- Anàlisi de sintaxi dels scripts PowerShell: correcta.
- Helper natiu C# compilat per a x64 amb .NET Framework.
- `chrome-audio-capture.exe --self-test`: Process Loopback disponible, callback COM àgil i PCM 44,1 kHz estèreo de 16 bits.
- Captura WAV real del procés arrel de Chrome: 1,99 segons, 2 canals, 44.100 Hz, 16 bits i 351.080 bytes.
- `scripts/build-portable.ps1`: construcció PyInstaller 6.21.0 correcta en mode `onedir`.
- L'autoprova de l'executable gràfic s'espera explícitament abans de comprimir el paquet.
- `scripts/build-portable.ps1 -ValidateOnly`: executable, runtime, FFmpeg, helper, llicència, avís i guia presents.

## Gravacions reals

- Sense micròfon: H.264 1920×1080 a 30 FPS, AAC estèreo 44,1 kHz i 5,266 segons.
- Amb micròfon: H.264 1280×720 a aproximadament 60 FPS, AAC estèreo 44,1 kHz i 4,949 segons.
- Les dos proves van iniciar primer l'àudio de Chrome, després la captura de pantalla, i van finalitzar en un únic MP4.
- Durant les mostres Chrome no reproduïa contingut audible; els streams d'àudio i la mescla estan verificats, però no s'afirma una validació auditiva del contingut. La prova controlada amb una pàgina local de to va ser bloquejada per la política de seguretat de Chrome i no es va forçar cap alternativa.

Les mostres temporals viuen en `work/`, que està ignorat per Git, perquè poden contindre pantalla i veu reals.

## Revisió visual

- Arrancada neta del portable sense diàlegs ni errors.
- Estat inicial correcte: Chrome detectat, micròfon desactivat, 1080p i 30 FPS.
- En activar **Incloure el meu micròfon**, el selector apareix i detecta el dispositiu disponible.
- La finestra de 582×682 píxels no presenta retalls; jerarquia, contrast i botó principal són clars.
- Doble obertura del paquet `onedir`: dos finestres correctes i cap error d'extracció Tcl.

## Integritat del paquet

- Font del build Windows de FFmpeg: `https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip`.
- SHA-256 de l'arxiu FFmpeg descarregat: `DB580001CAA24AC104C8CB856CD113A87B0A443F7BDF47D8C12B1D740584A2EC`.
- ZIP final: 47.703.841 bytes.
- SHA-256 de `Conference-Recorder-Portable.zip`: `84CF95A7731D2C246CA8E3117DC5BF18CD7AA964344623DE11E87244F3CCDEE1`.

## Limitacions conegudes

- Windows 10 build 20348 o posterior.
- Chrome ha d'estar obert abans de començar i continuar obert durant la captura.
- El paquet no té signatura comercial de codi.
