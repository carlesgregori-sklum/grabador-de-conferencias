# Capture Source Selection Design

## Objectiu

Ampliar Conference Recorder perquè l’usuari puga triar què es grava sense perdre el comportament actual d’àudio de Chrome i micròfon opcional.

Els tres modes seran:

1. **Tota la pantalla principal**: captura directa actual amb FFmpeg.
2. **Una pantalla concreta**: selector natiu de Chrome per triar un monitor.
3. **Una pestanya de Chrome**: selector natiu de Chrome amb vídeo i àudio exclusius de la pestanya triada.

La solució no instal·larà cap extensió. Conference Recorder obrirà en Chrome una pàgina temporal servida exclusivament des de `127.0.0.1`; la pàgina usarà `getDisplayMedia()` perquè Chrome mostre el seu selector natiu.

## Experiència d’usuari

La finestra principal afegirà una secció **Què vols gravar?** abans del micròfon:

```text
Què vols gravar?

(●) Tota la pantalla principal
    Sense passos addicionals

( ) Una pantalla concreta
    Triaràs el monitor en Chrome

( ) Una pestanya de Chrome
    Vídeo i àudio només d’eixa pestanya
```

El mode inicial continuarà sent **Tota la pantalla principal** per conservar el flux existent i permetre gravar casos complets de Bizneo sense passos addicionals.

El botó principal mostrarà:

- **Gravar conferència** en el mode de pantalla principal.
- **Triar pantalla i gravar** en el mode de monitor.
- **Triar pestanya i gravar** en el mode de pestanya.

El micròfon continuarà desactivat per defecte i serà independent del mode de vídeo. Els selectors 720p/1080p i 30/60 FPS continuaran disponibles.

## Fluxos de gravació

### Tota la pantalla principal

Es conserva el flux actual:

1. Validar Chrome, FFmpeg i el helper WASAPI.
2. Iniciar la captura d’àudio de l’arbre de processos de Chrome.
3. Iniciar FFmpeg amb `gdigrab desktop` i, si està activat, DirectShow per al micròfon.
4. Minimitzar la UI i gravar.
5. Finalitzar i combinar en MP4 H.264/AAC.

Este mode no obri cap pestanya auxiliar.

### Una pantalla concreta

1. Conference Recorder crea la sessió i inicia un servidor HTTP temporal en una adreça aleatòria de `127.0.0.1`.
2. Obri en Chrome la pàgina local de selecció amb un token de sessió aleatori.
3. L’usuari prem **Seleccionar pantalla** i Chrome mostra el selector natiu.
4. La pàgina demana vídeo sense àudio del sistema i comprova que `displaySurface` siga `monitor`.
5. Si l’usuari tria una finestra o pestanya, la pàgina explica l’error i permet repetir la selecció.
6. Quan el monitor està preparat, Conference Recorder inicia l’àudio de l’arbre de Chrome i el micròfon opcional.
7. La pàgina comença `MediaRecorder` i envia fragments WebM ordenats al servidor local.
8. En finalitzar, FFmpeg converteix el vídeo WebM a H.264, incorpora l’àudio de Chrome i mescla el micròfon opcional.

La selecció pot ser qualsevol monitor, inclòs el principal. No s’inclou la captura d’una finestra individual en esta versió perquè no és un dels tres modes demanats.

### Una pestanya de Chrome

1. S’obri la mateixa pàgina local en mode pestanya.
2. L’usuari prem **Seleccionar pestanya** i tria una pestanya en la secció corresponent del selector natiu de Chrome.
3. La pàgina comprova que `displaySurface` siga `browser` i que el flux incloga una pista d’àudio.
4. Si no s’ha activat **Compartir també l’àudio**, no comença la gravació i es mostra com repetir la selecció correctament.
5. El WebM conté el vídeo i l’àudio exactes de la pestanya. En este mode no s’inicia el helper WASAPI de l’arbre complet de Chrome, evitant que entren altres pestanyes.
6. Si el micròfon està activat, es captura en un fitxer temporal separat.
7. FFmpeg converteix el vídeo a H.264, usa l’àudio de la pestanya com a font principal i mescla el micròfon opcional.

La pàgina controladora demanarà a Chrome excloure la pestanya actual del selector quan l’API ho permeta. També demanarà mantindre la reproducció local de l’àudio perquè l’usuari continue escoltant la conferència. Si Chrome suprimeix la reproducció, la pàgina connectarà una única vegada la pista capturada a un `AudioContext` local.

## Arquitectura

### Model de captura

`models.py` incorporarà:

- `CaptureMode.PRIMARY_SCREEN`
- `CaptureMode.SELECTED_MONITOR`
- `CaptureMode.CHROME_TAB`

`RecordingConfig` inclourà el mode. El PID de Chrome continuarà sent obligatori perquè Chrome és necessari en els tres fluxos: com a font d’àudio en pantalla/monitor i com a navegador capturat en pestanya.

`RecordingPaths` afegirà temporals específics:

- `.browser.webm` per al vídeo seleccionat en Chrome.
- `.microphone.wav` per al micròfon quan el vídeo prové del navegador.

Els temporals que no corresponen al mode seleccionat no es crearan.

### Pont local de captura

Un nou mòdul `browser_capture.py` serà responsable de:

- Crear un `ThreadingHTTPServer` vinculat només a `127.0.0.1` i un port lliure assignat pel sistema.
- Generar un token de sessió criptogràfic de 256 bits.
- Servir la pàgina HTML/JavaScript de captura.
- Validar el token en totes les peticions.
- Rebre metadades de la font seleccionada.
- Coordinar les ordres `start`, `stop` i `abort`.
- Rebre fragments WebM amb números de seqüència i escriure’ls en ordre.
- Informar el `Recorder` quan el navegador està preparat, ha començat, ha acabat o ha fallat.
- Tancar el servidor i els sockets en tots els camins d’eixida.

La pàgina viurà en `src/bizneo_recorder/assets/browser_capture.html` i s’inclourà explícitament en el paquet PyInstaller.

### Protocol local

El protocol serà deliberadament reduït i específic d’una sessió:

```text
GET  /capture/<token>          pàgina de selecció
POST /api/<token>/ready        font, displaySurface, àudio disponible
GET  /api/<token>/command      espera curta de start/stop/abort
POST /api/<token>/chunk/<seq>  fragment WebM ordenat
POST /api/<token>/complete     gravació del navegador tancada
POST /api/<token>/error        error local i diagnòstic acotat
```

La pàgina enviarà cada fragment només després de rebre confirmació del fragment anterior. El servidor acceptarà únicament el número de seqüència esperat; una repetició del mateix fragment obtindrà una resposta idempotent i qualsevol salt serà rebutjat. Això evita corrupció per peticions fora d’ordre.

### Localització de Chrome

`processes.py` ampliarà la detecció actual per obtindre també la ruta de l’executable del procés arrel amb `QueryFullProcessImageNameW`. Conference Recorder obrirà la URL local executant eixa ruta; així no depén del navegador predeterminat de Windows.

### FFmpeg i finalització

`ffmpeg.py` mantindrà el flux actual de pantalla principal i afegirà:

- Captura de micròfon a WAV sense vídeo.
- Finalització d’un WebM de monitor amb WAV de Chrome i micròfon opcional.
- Finalització d’un WebM de pestanya amb el seu àudio intern i micròfon opcional.
- Escalat proporcional i farciment a 720p o 1080p.
- Conversió a H.264 `veryfast`, AAC 192 kb/s i `+faststart`.

Els modes seleccionats en Chrome necessiten recodificar el vídeo perquè `MediaRecorder` genera WebM. La pantalla principal continuarà codificant-se una sola vegada i usarà `-c:v copy` durant la mescla final.

## Coordinació i estat

`Recorder` continuarà sent l’únic propietari del cicle de vida. Per als modes de navegador usarà estos estats interns:

```text
IDLE
  -> WAITING_FOR_SOURCE
  -> PREPARING_NATIVE_AUDIO
  -> RECORDING
  -> FINALIZING
  -> IDLE
```

La UI només iniciarà el temporitzador quan el navegador confirme que `MediaRecorder` ha començat. Cancel·lar el selector tornarà a `IDLE` sense crear un MP4 ni mostrar un error alarmant.

En parar:

1. S’ordena al navegador tancar `MediaRecorder` i enviar l’últim fragment.
2. Es valida el WebM complet.
3. Es paren el helper de Chrome i el micròfon, quan existisquen.
4. FFmpeg genera `.part.mp4`.
5. L’eixida correcta promou atòmicament el parcial a `.mp4`.
6. Només després s’eliminen els temporals i es tanca el pont local.

## Seguretat i privacitat

- El servidor escolta exclusivament en `127.0.0.1`, mai en la xarxa local.
- Cada sessió usa un token no reutilitzable generat amb `secrets.token_urlsafe(32)` o equivalent.
- No s’habilita CORS; la pàgina i l’API comparteixen el mateix origen local.
- Es limiten la mida de cada fragment, els mètodes, les rutes i el cos dels errors.
- No es registra l’URL, el títol ni el contingut de la pestanya seleccionada.
- Cap vídeo, àudio, telemetria o diagnòstic ix de l’ordinador.
- El servidor s’apaga al final de cada sessió o després d’un temps límit sense selecció.

## Errors i recuperació

- **Selector cancel·lat:** retorn silenciós a l’estat preparat.
- **Font incorrecta:** instrucció en la pàgina local i botó per repetir.
- **Pestanya sense àudio compartit:** no es grava; es demana activar l’opció d’àudio.
- **Pestanya controladora tancada:** s’aturen les fonts natives i es conserven els temporals útils.
- **Chrome deixa de compartir:** l’esdeveniment `ended` finalitza o marca la sessió com interrompuda.
- **Fragment perdut o fora d’ordre:** s’aborta la finalització i es conserva el WebM parcial.
- **Servidor local ocupat o bloquejat:** es mostra un error de loopback amb una acció per reintentar.
- **Chrome es tanca:** es paren totes les fonts i es conserven els temporals.
- **Error de conversió:** WebM, WAV de Chrome i WAV del micròfon es mantenen per recuperació.

La UI no mostrarà traces tècniques completes; conservarà un diagnòstic breu i accionable.

## Proves

El desenvolupament seguirà TDD.

### Proves unitàries

- Validació dels tres `CaptureMode` i les rutes temporals de cada mode.
- Detecció de la ruta executable de Chrome.
- Ordres FFmpeg per a cada mode amb i sense micròfon.
- Transicions del `Recorder`, cancel·lació i errors durant la selecció.
- Textos, estat del botó i visibilitat dels controls en la UI.

### Proves del pont HTTP

- Vinculació exclusiva a loopback.
- Rebuig de token incorrecte, mètode no admés, fragment excessiu i seqüència invàlida.
- Escriptura ordenada i idempotència d’un reintent.
- Temps límit, `stop`, `abort`, `complete` i tancament net.
- Capçalera WebM no buida abans de finalitzar.

### Verificació real

- Pantalla principal a 1080p/30 amb àudio de Chrome.
- Monitor seleccionat a 720p/60 amb àudio de Chrome.
- Pestanya seleccionada amb vídeo i àudio exclusius de la pestanya.
- Repetició de cada mode amb micròfon activat almenys una vegada.
- Cancel·lació del selector i selecció deliberada d’una font incorrecta.
- Finalització des del botó de l’aplicació i des de l’opció de deixar de compartir de Chrome.
- Inspecció amb `ffprobe`: un stream H.264, un stream AAC, resolució/FPS i duració coherent.
- Revisió visual del portable i reconstrucció del ZIP final.

## Documentació i paquet

S’actualitzaran `README.md`, `docs/usage.md`, `docs/architecture.md`, `docs/portable-readme.txt` i `docs/verification.md`.

`scripts/build-portable.ps1` inclourà l’asset HTML, validarà els nous fitxers i continuarà generant `Conference-Recorder-Portable.zip`. La carpeta arrel del projecte no rebrà fitxers nous; el codi, l’asset, les proves i els temporals quedaran en les carpetes internes corresponents.

Este document substitueix només les limitacions anteriors sobre selecció de monitor i pestanya. La captura d’una finestra individual, altres navegadors, webcam, anotacions i edició de vídeo continuen fora d’abast.
