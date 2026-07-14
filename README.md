# Bizneo Recorder

Aplicació portàtil per gravar la pantalla principal i un micròfon en un MP4. Permet triar entre 720p/1080p i 30/60 FPS, i està pensada per crear explicacions breus de fluxos de Bizneo sense instal·lar un editor de vídeo.

## Desenvolupament

```powershell
python -m unittest discover -s tests -t . -v
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

La documentació d’ús està en [`docs/usage.md`](docs/usage.md) i l’organització tècnica en [`docs/architecture.md`](docs/architecture.md).

