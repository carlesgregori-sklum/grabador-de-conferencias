# Bizneo Recorder

Aplicació portàtil per gravar la pantalla principal Full HD i un micròfon en un MP4. Està pensada per crear explicacions breus de fluxos de Bizneo sense instal·lar un editor de vídeo.

## Desenvolupament

```powershell
python -m unittest discover -s tests -t . -v
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

La documentació d’ús està en [`docs/usage.md`](docs/usage.md) i l’organització tècnica en [`docs/architecture.md`](docs/architecture.md).

