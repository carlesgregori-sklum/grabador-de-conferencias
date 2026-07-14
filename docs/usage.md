# Ús de Bizneo Recorder

## Inici ràpid

1. Descomprimeix `Bizneo-Recorder-Portable.zip` en una carpeta local.
2. Conserva junts `Bizneo Recorder.exe` i la carpeta `tools`.
3. Obri `Bizneo Recorder.exe`.
4. Selecciona el micròfon, la resolució i els FPS.
5. Prem **Començar gravació**.
6. Quan acabes l’explicació, recupera l’aplicació des de la barra de tasques i prem **Finalitzar i guardar**.

El resultat queda a `Vídeos\Bizneo Recorder` amb un nom com `Bizneo-2026-07-14-153010.mp4`.

## Qualitat de gravació

La configuració inicial és **Full HD 1080p · 30 FPS**, recomanada per explicar pantalles de Bizneo amb text nítid i una càrrega moderada.

| Selector | Opcions | Ús recomanat |
|---|---|---|
| Resolució | HD 720p / Full HD 1080p | 720p crea fitxers més lleugers; 1080p conserva millor el text. |
| Fluïdesa | 30 FPS / 60 FPS | 30 FPS és suficient per a tutorials; 60 FPS és més fluid però genera fitxers més grans i exigeix més a l’equip. |

Els selectors queden bloquejats durant la gravació i es reactiven quan el vídeo queda guardat o es produeix un error.

## Perfil tècnic

- Pantalla principal completa, cursor inclòs.
- Resolució final seleccionable: 1280×720 o 1920×1080.
- Fluïdesa seleccionable: 30 o 60 fotogrames per segon.
- Vídeo H.264 i àudio AAC.
- Només el micròfon seleccionat; no grava l’àudio de Windows.

## Privacitat

La captura i la codificació són locals. L’aplicació no puja vídeos ni dades a Internet. El procés de construcció sí que descarrega FFmpeg i PyInstaller; l’aplicació ja construïda no necessita xarxa.

## Resolució de problemes

### No apareix cap micròfon

Obri **Configuració > Privacitat i seguretat > Micròfon** i activa l’accés per a aplicacions d’escriptori. Connecta el dispositiu abans d’obrir el programa i prem **Actualitzar**.

### Windows mostra una advertència en obrir l’executable

L’executable és una aplicació local sense signatura de codi comercial. Verifica que prové del ZIP entregat. Si SmartScreen el bloqueja, usa **Més informació > Executar igualment** només si el fitxer és el lliurat en aquest projecte.

### El fitxer acaba en `.part.mp4`

Indica una interrupció o un error de FFmpeg. No l’esborres: pot ser recuperable. Torna a provar una gravació curta després de revisar el micròfon i l’espai lliure.

### El vídeo va lent

Tanca aplicacions pesades i deixa uns quants GB lliures. El perfil `veryfast` prioritza una gravació fluida en un equip Full HD.

## Verificació i manteniment

```powershell
python -m unittest discover -s tests -t . -v
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

El script de construcció valida que l’executable, FFmpeg, la llicència i la guia estiguen presents abans de crear el ZIP.

