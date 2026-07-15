# Ús de Conference Recorder

## Inici ràpid

1. Descomprimeix `Conference-Recorder-Portable.zip` en una carpeta local.
2. Conserva junts `Conference Recorder.exe` i les carpetes `_runtime` i `tools`.
3. Obri Google Chrome i prepara la conferència, webinar o cas de Bizneo.
4. Obri `Conference Recorder.exe` i comprova que indica **Chrome detectat · àudio preparat**.
5. Deixa desmarcat **Incloure el meu micròfon** si només vols escoltar la conferència.
6. Prem **Gravar conferència**. La finestra es minimitzarà.
7. Quan acabes, recupera l’aplicació des de la barra de tasques i prem **Finalitzar i guardar**.

El resultat queda en `Vídeos\Conference Recorder` amb un nom com `Conference-2026-07-15-153010.mp4`.

## Què es grava

- Tota la pantalla principal i el cursor, encara que canvies entre Chrome, Bizneo o altres finestres.
- L’àudio reproduït pel procés principal de Chrome i els seus processos descendents.
- El micròfon seleccionat només quan actives explícitament l’opció.

No es grava l’àudio d’altres aplicacions ni les notificacions de Windows. No és una captura d’una pestanya concreta: si tens diverses pestanyes de Chrome reproduint àudio al mateix temps, totes formen part del mateix arbre del navegador.

## Micròfon opcional

El micròfon està desactivat per defecte. En activar-lo apareix el selector; tria el dispositiu que vols mesclar amb Chrome. Si no apareix:

1. Revisa **Configuració > Privacitat i seguretat > Micròfon**.
2. Activa l’accés per a aplicacions d’escriptori.
3. Connecta el dispositiu i prem **Actualitzar**.

## Qualitat

La configuració inicial és **Full HD 1080p · 30 FPS**, recomanada per a conferències i demostracions de Bizneo.

| Opció | Ús |
|---|---|
| HD 720p | Fitxer més lleuger i menor càrrega. |
| Full HD 1080p | Text i detalls més nítids. |
| 30 FPS | Recomanat per conferències i tutorials. |
| 60 FPS | Moviment més fluid, més CPU i fitxers més grans. |

## Privacitat

Tota la captura i codificació és local. L’aplicació no puja vídeos, àudio, diagnòstics ni telemetria. Quan l’opció del micròfon està desmarcada, el dispositiu no s’enumera ni s’obri.

## Resolució de problemes

### Chrome no està obert

Obri Chrome i prem **Tornar a comprovar**. Chrome ha d’estar obert abans de començar i no s’ha de tancar durant la gravació.

### Windows no és compatible

La captura exclusiva per procés requereix Windows 10 build 20348 o posterior. Executa `Conference Recorder.exe --self-test` per veure el diagnòstic.

### Windows mostra SmartScreen

L’executable local no té signatura de codi comercial. Verifica que prové del ZIP construït per este projecte. Usa **Més informació > Executar igualment** només amb el paquet verificat.

### Queden fitxers `.capture.mkv`, `.chrome.wav` o `.part.mp4`

Indiquen una interrupció durant captura o combinació. No els esborres immediatament: poden permetre recuperar vídeo o àudio. Prova una gravació curta després de revisar Chrome, espai lliure i el micròfon opcional.

## Verificació i manteniment

```powershell
python -m unittest discover -s tests -t . -v
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

El build compila el helper natiu, crea el paquet PyInstaller `onedir`, valida FFmpeg i Process Loopback, espera que acabe l’autoprova gràfica i només després genera el ZIP.
