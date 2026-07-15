# Conference Recorder

Aplicació Windows portable per gravar **tota la pantalla principal** amb l’àudio reproduït exclusivament per Google Chrome. El micròfon és opcional i està desactivat per defecte.

La captura de Chrome usa el Process Loopback oficial de Windows i inclou l’arbre de processos del navegador sense gravar notificacions ni altres aplicacions. Requereix Windows 10 build 20348 o posterior.

## Desenvolupament

```powershell
python -m unittest discover -s tests -t . -v
ruff check src tests scripts
python -m compileall -q src scripts tests
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
```

La guia d’ús està en [`docs/usage.md`](docs/usage.md), l’organització tècnica en [`docs/architecture.md`](docs/architecture.md) i les comprovacions reals en [`docs/verification.md`](docs/verification.md).
