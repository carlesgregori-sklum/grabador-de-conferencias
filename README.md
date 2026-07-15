# Conference Recorder

Aplicació Windows portable per gravar una de tres fonts: **tota la pantalla principal**, **un monitor concret** o **una pestanya de Chrome**. L’àudio prové de Chrome i el micròfon és opcional i està desactivat per defecte.

No necessita cap extensió. Els modes de monitor i pestanya usen el selector natiu de Chrome; tota la captura i la codificació es mantenen en local. Requereix Windows 10 build 20348 o posterior i Chrome obert.

## Desenvolupament

```powershell
python -m unittest discover -s tests -t . -v
python -m ruff check src tests scripts
python -m compileall -q src tests scripts
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

La guia d’ús està en [`docs/usage.md`](docs/usage.md), l’organització tècnica en [`docs/architecture.md`](docs/architecture.md) i les comprovacions en [`docs/verification.md`](docs/verification.md).
