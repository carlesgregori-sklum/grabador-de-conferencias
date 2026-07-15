# Chrome Conference Audio Design

## Objectiu

Convertir Bizneo Recorder en una aplicació de conferències minimalista que grave la pantalla principal i l’àudio reproduït exclusivament per Google Chrome. El micròfon de l’usuari serà opcional i estarà desactivat per defecte.

La interfície mostrarà el nom **Conference Recorder**, però el paquet Python `bizneo_recorder` es conservarà per evitar una migració interna que no aporta valor a esta funcionalitat.

## Abast

### Inclòs

- Captura de la pantalla principal amb el cursor.
- Captura de l’àudio del procés arrel de Chrome i de tots els seus processos descendents.
- Mescla opcional del micròfon seleccionat amb l’àudio de Chrome.
- Micròfon desactivat per defecte i sense obligació de seleccionar-ne cap.
- Detecció automàtica de Chrome abans de començar.
- Perfils de vídeo existents: 720p/1080p i 30/60 FPS.
- Minimització de la finestra mentre es grava.
- Finalització segura en MP4 i conservació de temporals quan falla algun procés.
- Paquet Windows portable sense instal·lació ni configuració d’un dispositiu d’àudio virtual.

### Fora d’abast

- Transcripció amb Whisper.
- Captura d’altres navegadors o selecció arbitrària d’aplicacions.
- Captura de l’àudio general de Windows.
- Captura d’una pestanya concreta de Chrome.
- Captura de webcam, anotacions o edició del vídeo.
- Gravació de diverses pantalles.

## Compatibilitat

La captura per procés usarà `AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS` i el mode `PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE` de Windows. Microsoft documenta esta API a partir de Windows 10 build 20348. L’equip de desenvolupament actual usa Windows build 26200 i és compatible.

Referències oficials:

- <https://learn.microsoft.com/en-us/windows/win32/api/audioclientactivationparams/ns-audioclientactivationparams-audioclient_process_loopback_params>
- <https://learn.microsoft.com/en-us/samples/microsoft/windows-classic-samples/applicationloopbackaudio-sample/>

Conference Recorder validarà la versió de Windows en el diagnòstic. En versions anteriors a build 20348 mostrarà un error clar i no permetrà començar una gravació.

## Arquitectura

### Components

```text
Conference Recorder (Python/Tkinter)
├── Chrome process discovery
│   └── localitza el procés arrel chrome.exe i el seu PID
├── Recorder lifecycle
│   ├── inicia i para la captura de pantalla
│   ├── inicia i para la captura d’àudio de Chrome
│   └── finalitza i neteja els fitxers temporals
├── FFmpeg
│   ├── codifica la pantalla
│   ├── captura el micròfon opcional via DirectShow
│   └── combina vídeo, Chrome i micròfon en l’MP4 final
└── Chrome audio helper (.NET Framework, executable adjacent)
    └── WASAPI process loopback per a l’arbre de processos de Chrome
```

### Capturador natiu d’àudio

S’afegirà un executable auxiliar x64 compilat des de codi font inclòs en el repositori. El helper usarà les interfícies oficials de Windows Audio per capturar l’arbre del PID rebut i escriurà PCM estèreo de 16 bits a 44,1 kHz en un WAV temporal.

El helper:

- Rebrà el PID de Chrome i la ruta WAV per arguments.
- Inicialitzarà `VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK` en mode `includetree`.
- Escriurà silenci durant períodes sense àudio per conservar la línia temporal.
- Comunicarà que està preparat abans que comence la captura de pantalla.
- Acceptarà una ordre de parada per entrada estàndard i tancarà correctament la capçalera WAV.
- Tornarà un codi d’eixida diferent de zero i un diagnòstic en `stderr` quan falle.

El helper es compilarà amb el compilador C# de .NET Framework disponible en Windows. El binari compilat s’inclourà en `tools/` al costat de FFmpeg; l’usuari final no necessitarà instal·lar SDKs ni dependències addicionals.

### Detecció de Chrome

Un mòdul Python enumerarà els processos de Windows amb Tool Help. Identificarà processos `chrome.exe`, construirà les relacions pare-fill i seleccionarà com a arrel el procés de Chrome que no tinga un altre `chrome.exe` com a pare.

En el cas poc habitual de trobar diverses arrels independents, se seleccionarà la que continga més processos descendents. La interfície mostrarà que Chrome està detectat sense exposar PIDs ni detalls tècnics.

Chrome ha d’estar obert abans de començar. Si el procés arrel desapareix durant la gravació, el helper finalitzarà amb error; el gravador conservarà els temporals i informarà que Chrome es va tancar.

## Flux de gravació

### Inici

1. L’aplicació valida la versió de Windows, FFmpeg i el helper d’àudio.
2. Detecta el procés arrel de Chrome.
3. Si el micròfon està activat, valida la selecció; si està desactivat, no enumera ni obri cap micròfon.
4. Reserva rutes úniques per al vídeo final i els temporals.
5. Inicia el helper d’àudio de Chrome i espera el seu senyal de preparació amb un temps límit curt.
6. Inicia FFmpeg per capturar la pantalla i, opcionalment, el micròfon.
7. Canvia a estat de gravació, inicia el temporitzador i minimitza la finestra.

Si el helper no arriba a estar preparat, FFmpeg no s’inicia i l’usuari rep un error accionable.

### Finalització

1. La interfície torna a primer pla i bloqueja els controls.
2. S’envia una parada ordenada a FFmpeg i al helper d’àudio.
3. Es comprova que el vídeo temporal i el WAV de Chrome siguen vàlids.
4. FFmpeg genera el `.part.mp4` final:
   - Sense micròfon: vídeo + àudio de Chrome.
   - Amb micròfon: vídeo + mescla a volum unitari de Chrome i micròfon.
5. Una eixida correcta promou atòmicament `.part.mp4` a `.mp4`.
6. Només després de l’èxit s’eliminen els temporals intermedis.

La combinació final copiarà el vídeo ja codificat i només codificarà l’àudio a AAC, de manera que l’espera de finalització siga curta.

## Model de dades

`RecordingConfig` canviarà perquè el micròfon siga opcional i inclourà explícitament el PID arrel de Chrome. La validesa serà:

- `chrome_process_id` ha de ser positiu.
- `microphone=None` significa que no s’ha de capturar ni mesclar el micròfon.
- Resolució i FPS conserven les validacions actuals.

Les rutes temporals formaran un conjunt per sessió: captura de pantalla, WAV de Chrome, MP4 parcial i MP4 final. Una estructura dedicada evitarà construir noms de fitxer dispersos entre mòduls.

## Interfície

La finestra es reduirà visualment a les decisions reals de l’usuari:

```text
Conference Recorder
Grava una conferència de Chrome en un MP4.

● Chrome detectat

[ ] Incloure el meu micròfon
    [ selector de micròfon ]      només quan està activat

Opcions
    Resolució: Full HD 1080p
    Fluïdesa:  30 FPS

[        Gravar conferència        ]
              00:00

[Obrir carpeta]     estat o últim resultat
```

Principis:

- L’àudio de Chrome és implícit i no necessita un selector.
- El micròfon està desactivat per defecte.
- Els controls de qualitat queden en una secció secundària compacta i conserven 1080p/30 FPS com a valor recomanat.
- El botó principal domina la jerarquia visual.
- La pantalla d’espera distingeix clarament “Chrome no està obert”, “Preparant”, “Gravant” i “Finalitzant”.
- El botó d’inici queda desactivat fins que Chrome i els components locals estiguen disponibles.
- La navegació amb teclat, els estats de focus i el contrast es conservaran.

El directori d’eixida visible passarà a `Vídeos\Conference Recorder` i els fitxers usaran el prefix `Conference-YYYY-MM-DD-HHMMSS.mp4`.

## Errors i recuperació

- **Chrome no està obert:** estat informatiu i botó per tornar a comprovar.
- **Windows no compatible:** missatge que indica la build mínima 20348.
- **Helper absent o corrupte:** instrucció de conservar completa la carpeta portable.
- **Micròfon activat però no disponible:** no es pot començar fins a seleccionar-ne un.
- **Un procés acaba inesperadament:** s’aturen els altres processos i es conserven els temporals.
- **Error de combinació:** es conserva la captura de pantalla, el WAV de Chrome i, si existeix, l’àudio del micròfon.
- **Tancament de la finestra mentre grava:** es demana confirmació i, si s’accepta, es completa el mateix flux de finalització segura.

Els missatges de la UI seran curts; els últims diagnòstics tècnics s’inclouran en el detall de l’error per facilitar suport.

## Privacitat

- Tota la captura i codificació és local.
- Només s’inclou l’àudio de Chrome i, quan l’usuari ho activa explícitament, el micròfon seleccionat.
- L’aplicació no puja vídeos, àudio ni telemetria.
- No s’activa el micròfon en segon pla quan l’interruptor està desmarcat.

## Proves i verificació

El desenvolupament seguirà TDD.

### Proves unitàries

- Detecció de l’arrel de Chrome i selecció determinista entre diverses arrels.
- Configuració vàlida sense micròfon i amb micròfon.
- Generació de totes les rutes temporals sense col·lisions.
- Ordres FFmpeg per a vídeo sense micròfon, vídeo amb micròfon i combinació final en ambdós modes.
- Transicions del recorder quan el helper està preparat, falla, acaba abans d’hora o es para correctament.
- Restauració dels controls de la UI després d’èxit i error.

### Proves del helper

- Validació d’arguments i PID.
- Creació d’un WAV amb capçalera i format correctes.
- Parada ordenada per entrada estàndard.
- Codi d’eixida i diagnòstic quan no es pot activar process loopback.

### Verificació real

- Gravar un senyal reproduït en Chrome amb el micròfon desactivat i confirmar que l’MP4 conté H.264 i AAC.
- Reproduir simultàniament un so en una altra aplicació i confirmar que no apareix en la captura de Chrome.
- Repetir amb micròfon activat i confirmar que les dues fonts són audibles.
- Verificar els perfils 1080p/30 i 720p/60 amb `ffprobe`.
- Construir el ZIP portable, descomprimir-lo en una carpeta neta i executar el diagnòstic.
- Revisar visualment la UI, el redimensionament fix, el teclat, els estats desactivats, la minimització i els missatges d’error.

Les mostres amb pantalla o veu real s’eliminaran després de validar els streams.

## Documentació i paquet

S’actualitzaran:

- `README.md`: nou objectiu i ordres principals.
- `docs/usage.md`: flux de conferència, Chrome, micròfon opcional i privacitat.
- `docs/architecture.md`: helper natiu, detecció de processos i nova finalització.
- `docs/portable-readme.txt`: guia curta inclosa en el ZIP.
- `docs/verification.md`: commands, resultats reals i hashes del paquet final.
- `scripts/build-portable.ps1`: compilació i inclusió del helper, validacions i ZIP.
- `scripts/smoke-recording.py` i `scripts/verify-recording.ps1`: nous modes i comprovació de streams.

El codi font del helper viurà en una carpeta interna dedicada i no afegirà fitxers solts a l’arrel. `outputs/` continuarà reservat per als artefactes finals i `work/` per a construcció i mostres temporals.
