# Grabador de conferencias

Aplicación portable para Windows que graba una de tres fuentes: **la pantalla principal completa**, **un monitor elegido por el usuario** o **una pestaña de Chrome**. El audio procede de Chrome y el micrófono es opcional; está desactivado por defecto.

La versión 3.0 incorpora una interfaz oscura y animada, completamente en castellano, pensada para que un equipo de RRHH pueda utilizarla sin formación técnica. No necesita Python, FFmpeg instalado, permisos de administrador ni extensiones de Chrome.

## Descargar para Windows

**[Descargar Grabador de conferencias 3.0.1](https://github.com/carlesgregori-sklum/grabador-de-conferencias/releases/download/v3.0.1/Grabador-de-conferencias-Portable.zip)**

Descomprime el ZIP completo y ejecuta `Grabador de conferencias.exe`. No descargues ni muevas solo el `.exe`: necesita las carpetas `_runtime` y `tools` incluidas en el paquete.

## Entrega a RRHH

1. Comparte `Grabador-de-conferencias-Portable.zip`.
2. El usuario debe descomprimir el ZIP completo en una carpeta local.
3. Debe conservar juntos `Grabador de conferencias.exe`, `_runtime` y `tools`.
4. Abre Chrome, ejecuta el programa y elige qué quiere grabar.

Windows puede mostrar SmartScreen porque el ejecutable no tiene una firma comercial. La aplicación requiere Windows 10 build 20348 o posterior y Google Chrome abierto.

## Modos de captura

| Opción | Vídeo | Audio principal |
|---|---|---|
| Pantalla completa | Pantalla principal y cursor, sin selector | Audio del árbol de procesos de Chrome |
| Elegir pantalla | Monitor completo elegido en el selector nativo | Audio del árbol de procesos de Chrome |
| Pestaña de Chrome | Pestaña elegida | Audio compartido por esa pestaña |

El micrófono puede mezclarse con cualquiera de los tres modos. La carpeta y la calidad se eligen antes de grabar.

## Privacidad

La captura y la codificación se realizan en local. El selector auxiliar se comunica únicamente con `127.0.0.1` mediante un token aleatorio de sesión. No se envían vídeo, audio, URL, títulos, diagnósticos ni telemetría a Internet.

## Desarrollo

```powershell
python -m unittest discover -s tests -t . -v
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

La guía completa está en [`docs/usage.md`](docs/usage.md), la organización técnica en [`docs/architecture.md`](docs/architecture.md) y los resultados de comprobación en [`docs/verification.md`](docs/verification.md).
