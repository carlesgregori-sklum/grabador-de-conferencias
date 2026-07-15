# Uso del Grabador de conferencias

## Inicio rápido

1. Descomprime `Grabador-de-conferencias-Portable.zip` en una carpeta local.
2. Conserva juntos `Grabador de conferencias.exe`, `_runtime` y `tools`.
3. Abre Chrome y prepara la conferencia o el caso de Bizneo.
4. Ejecuta `Grabador de conferencias.exe` y comprueba **Chrome listo**.
5. Elige `Pantalla completa`, `Elegir pantalla` o `Pestaña de Chrome`.
6. Activa **Incluir micrófono** únicamente si quieres grabar también tu voz.
7. Revisa calidad y carpeta de destino.
8. Pulsa la acción principal. Si elegiste monitor o pestaña, completa el selector nativo de Chrome.
9. Cuando termines, vuelve a la aplicación y pulsa **Finalizar y guardar**.

El destino inicial es `Vídeos\Grabador de conferencias`. Los archivos se llaman, por ejemplo, `Grabacion-2026-07-15-153010.mp4`. El botón **Cambiar** permite elegir otra carpeta antes de empezar.

## Fuentes de captura

| Modo | Vídeo | Audio principal |
|---|---|---|
| Pantalla completa | Pantalla principal y cursor, sin selector | Todo el audio del árbol de procesos de Chrome |
| Elegir pantalla | Monitor completo elegido en Chrome | Todo el audio del árbol de procesos de Chrome |
| Pestaña de Chrome | Solo la pestaña elegida | Solo el audio compartido por esa pestaña |

En **Elegir pantalla**, entra en la sección de pantallas completas del selector. Si eliges una ventana o una pestaña, la página explica el error y permite repetir.

En **Pestaña de Chrome**, entra en la sección de pestañas y activa **Compartir también el audio**. Si falta esa opción, la aplicación permite repetir la selección. No es necesaria ninguna extensión.

Cerrar o cancelar el selector devuelve la aplicación a su estado inicial con un mensaje claro. Dejar de compartir desde Chrome detiene la sesión de forma controlada y conserva los temporales si no puede generarse el MP4.

## Micrófono opcional

El micrófono está desactivado por defecto. La aplicación no enumera dispositivos hasta que el usuario activa la opción. El micrófono seleccionado se mezcla con el audio principal sin sustituirlo.

Si no aparece:

1. Revisa **Configuración > Privacidad y seguridad > Micrófono**.
2. Activa el acceso para aplicaciones de escritorio.
3. Conecta el dispositivo y pulsa **Actualizar**.

## Calidad

La configuración inicial es **Full HD 1080p · 30 FPS**, adecuada para conferencias y demostraciones de Bizneo.

| Opción | Uso recomendado |
|---|---|
| HD 720p | Archivo más ligero y menor carga del equipo |
| Full HD 1080p | Texto y detalles más nítidos |
| 30 FPS | Conferencias, formación y tutoriales |
| 60 FPS | Demostraciones con mucho movimiento; usa más CPU y espacio |

## Estados visuales

- **LISTO PARA GRABAR:** Chrome y las opciones necesarias están preparados.
- **PREPARANDO CAPTURA:** se está iniciando FFmpeg o el selector nativo.
- **GRABANDO:** el orbe y el cronómetro indican una sesión activa.
- **GUARDANDO VÍDEO:** se están combinando vídeo y audio; no cierres la aplicación.
- **VÍDEO GUARDADO:** el MP4 se ha creado correctamente.

Las órbitas, tarjetas, onda y acción principal cambian con el estado, pero no bloquean la captura ni añaden pasos.

## Privacidad

La grabación, los fragmentos temporales y la codificación son locales. La página auxiliar se comunica únicamente con `127.0.0.1` mediante un identificador aleatorio de sesión. No envía vídeo, audio, URL, títulos, diagnósticos ni telemetría.

## Resolución de problemas

### Chrome no está abierto

Abre Chrome y pulsa **Comprobar**. Chrome debe permanecer abierto durante la grabación.

### La pestaña no incluye audio

Cancela y vuelve a elegir **Pestaña de Chrome**. Activa **Compartir también el audio** en el selector.

### Windows no es compatible

La captura de audio exclusiva por proceso requiere Windows 10 build 20348 o posterior. Ejecuta `Grabador de conferencias.exe --self-test` para obtener un diagnóstico.

### Quedan archivos temporales

Los archivos `.capture.mkv`, `.browser.webm`, `.chrome.wav`, `.microphone.wav` o `.part.mp4` indican una interrupción. Consérvalos: pueden permitir recuperar vídeo o audio. Solo se eliminan después de crear correctamente el MP4.

### Windows muestra SmartScreen

El ejecutable no tiene una firma comercial. Usa **Más información > Ejecutar de todas formas** únicamente si confías en el ZIP recibido.

## Verificación y mantenimiento

```powershell
python -m unittest discover -s tests -t . -v
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1 -ValidateOnly
```

El build compila el helper nativo, incorpora FFmpeg y el selector, crea un paquete PyInstaller `onedir`, ejecuta los autodiagnósticos, valida la estructura y genera el ZIP.
