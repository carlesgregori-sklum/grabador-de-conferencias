# Grabador de conferencias

Aplicación portable para Windows que permite a equipos de RRHH, formación y soporte registrar conferencias, demostraciones y casos de Bizneo sin instalar herramientas técnicas. Resuelve en un único flujo la captura de vídeo, el audio reproducido por Chrome y, de forma opcional, la voz del usuario; el resultado es un archivo MP4 guardado localmente.

La versión 3.0.1 ofrece una interfaz principal oscura y animada en castellano. No necesita Python, una instalación externa de FFmpeg, permisos de administrador ni extensiones de Chrome.

## Qué permite hacer

- Grabar la pantalla principal completa y su cursor.
- Elegir un monitor completo mediante el selector nativo de Chrome.
- Grabar una pestaña concreta de Chrome con el audio compartido por esa pestaña.
- Mezclar opcionalmente un micrófono con el audio principal.
- Elegir calidad HD 720p o Full HD 1080p y 30 o 60 FPS.
- Cambiar la carpeta de destino y abrirla desde la aplicación.
- Finalizar la captura, combinar las fuentes y guardar un MP4 local.

## Descargar para Windows

[Descargar Grabador de conferencias 3.0.1](https://github.com/carlesgregori-sklum/grabador-de-conferencias/releases/download/v3.0.1/Grabador-de-conferencias-Portable.zip)

Descomprime el ZIP completo y ejecuta `Grabador de conferencias.exe`. No descargues ni muevas solo el `.exe`: necesita las carpetas `_runtime` y `tools` incluidas en el paquete.

## Flujo de uso

1. Abre Chrome y prepara la conferencia o contenido que vas a registrar.
2. Ejecuta `Grabador de conferencias.exe` y comprueba que indica **Chrome listo**.
3. Elige la fuente: pantalla principal, monitor completo o pestaña de Chrome.
4. Activa el micrófono solo si también necesitas grabar tu voz.
5. Revisa calidad y carpeta de destino e inicia la grabación.
6. Si elegiste monitor o pestaña, completa el selector de Chrome. En una pestaña activa **Compartir también el audio**.
7. Al terminar, vuelve a la aplicación y pulsa **Finalizar y guardar**.

El destino inicial es `Vídeos\Grabador de conferencias`. La aplicación genera nombres como `Grabacion-2026-07-15-153010.mp4` y evita sobrescribir archivos de una sesión anterior.

## Modos de captura

| Opción | Vídeo | Audio principal |
|---|---|---|
| Pantalla completa | Pantalla principal y cursor, sin selector | Audio del árbol de procesos de Chrome |
| Elegir pantalla | Monitor completo elegido en el selector nativo | Audio del árbol de procesos de Chrome |
| Pestaña de Chrome | Pestaña elegida | Audio compartido por esa pestaña |

El micrófono puede mezclarse con cualquiera de los tres modos y está desactivado por defecto.

## Requisitos y límites

- Windows 10 build 20348 o posterior y arquitectura x64.
- Google Chrome abierto antes y durante la grabación.
- El paquete portable completo debe permanecer en una misma carpeta.
- No captura una ventana individual, webcam ni audio principal de aplicaciones distintas de Chrome.
- No incluye anotación, edición, subida a Internet, cifrado ni gestión de conservación del vídeo.
- En pantalla o monitor se mezcla el audio audible del árbol de Chrome, no una única pestaña.
- El ejecutable no tiene firma comercial y Windows puede mostrar SmartScreen.

## Privacidad y uso responsable

La captura y la codificación se realizan en local. El selector auxiliar se comunica únicamente con `127.0.0.1` mediante un token aleatorio de sesión. No se envían vídeo, audio, URL, títulos, diagnósticos ni telemetría a Internet.

La aplicación no gestiona consentimiento ni políticas de retención. Antes de grabar, el equipo usuario debe confirmar que la captura está autorizada y aplicar el procedimiento interno correspondiente al almacenamiento, acceso y eliminación del MP4.

## Ayuda y documentación

La guía completa de uso está en [`docs/usage.md`](docs/usage.md). La [documentación técnica](docs/README.md) enlaza arquitectura, operación, mantenimiento y verificación.

Para comprobar una instalación sin abrir la interfaz:

```powershell
& '.\Grabador de conferencias.exe' --self-test
```

La resolución de problemas habituales y el tratamiento de archivos temporales están descritos en [`docs/usage.md`](docs/usage.md).

## Desarrollo

```powershell
python -m unittest discover -s tests -t . -v
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

Los resultados de comprobación publicados se conservan en [`docs/verification.md`](docs/verification.md).
