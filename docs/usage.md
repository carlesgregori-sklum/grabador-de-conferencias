# Ús de Conference Recorder

## Inici ràpid

1. Descomprimeix `Conference-Recorder-Portable.zip` en una carpeta local.
2. Conserva junts `Conference Recorder.exe` i les carpetes `_runtime` i `tools`.
3. Obri Chrome i prepara la conferència o el cas de Bizneo.
4. Obri `Conference Recorder.exe` i comprova **Chrome detectat · àudio preparat**.
5. Tria la font: pantalla principal, monitor concret o pestanya de Chrome.
6. Activa **Incloure el meu micròfon** només si vols gravar la veu.
7. Prem el botó blau. Si has triat monitor o pestanya, completa el selector de Chrome.
8. En acabar, torna a l’aplicació i prem **Finalitzar i guardar**.

El resultat queda en `Vídeos\Conference Recorder` amb un nom com `Conference-2026-07-15-153010.mp4`.

## Fonts de captura

| Mode | Vídeo | Àudio principal |
|---|---|---|
| Tota la pantalla principal | Pantalla principal i cursor, sense selector | Tot l’àudio de l’arbre de processos de Chrome |
| Una pantalla concreta | El monitor complet triat en el selector de Chrome | Tot l’àudio de l’arbre de processos de Chrome |
| Una pestanya de Chrome | Només la pestanya triada | Només l’àudio compartit per eixa pestanya |

En **Una pantalla concreta**, entra en la secció de pantalles completes del selector. Si tries una finestra o una pestanya, la pàgina ho explica i permet repetir.

En **Una pestanya de Chrome**, entra en la secció de pestanyes i activa **Compartir també l’àudio**. Si falta eixa opció, l’aplicació permet tornar a seleccionar. No cal instal·lar cap extensió.

Tancar o cancel·lar el selector torna l’aplicació a l’estat inicial amb un missatge clar. Parar la compartició des de Chrome finalitza la sessió de manera controlada i conserva els temporals si no es pot generar l’MP4.

## Micròfon opcional

El micròfon està desactivat per defecte. En activar-lo apareix un selector de dispositius. Es mescla amb la font principal sense substituir l’àudio de Chrome o de la pestanya.

Si no apareix:

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
| 60 FPS | Moviment més fluid, amb més CPU i espai. |

## Privacitat

La gravació, els fragments temporals i la codificació són locals. La pàgina auxiliar es comunica únicament amb `127.0.0.1` mitjançant un identificador aleatori de sessió; no puja vídeos, àudio, URL, títols, diagnòstics ni telemetria. Quan el micròfon està desmarcat, no s’enumera ni s’obri.

## Resolució de problemes

### Chrome no està obert

Obri Chrome i prem **Tornar a comprovar**. Chrome ha d’estar obert abans de començar i continuar obert durant la gravació.

### No apareix l’àudio de la pestanya

Cancel·la i torna a triar **Una pestanya de Chrome**. En el selector activa **Compartir també l’àudio**. El mode de monitor usa l’àudio general de Chrome i no mostra esta casella.

### Windows no és compatible

La captura d’àudio exclusiva per procés requereix Windows 10 build 20348 o posterior. Executa `Conference Recorder.exe --self-test` per veure el diagnòstic.

### Queden fitxers temporals

Els fitxers `.capture.mkv`, `.browser.webm`, `.chrome.wav`, `.microphone.wav` o `.part.mp4` indiquen una interrupció. Conserva’ls: poden permetre recuperar vídeo o àudio. Els temporals només s’eliminen després de crear correctament l’MP4.

### Windows mostra SmartScreen

L’executable local no té signatura comercial. Usa **Més informació > Executar igualment** només si confies en el ZIP verificat d’este projecte.

## Verificació i manteniment

```powershell
python -m unittest discover -s tests -t . -v
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -ValidateOnly
```

El build compila el helper natiu, incorpora FFmpeg i la pàgina del selector, crea el paquet PyInstaller `onedir`, executa els autodiagnòstics, valida l’estructura i genera el ZIP.
