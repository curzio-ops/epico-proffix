# epico-proffix

Client Python **in sola lettura** per la REST-API Proffix V4, condiviso tra epico FATTURA e AGENDA.
Nasce dal client dell'AGENDA (`backend/proffix_client.py`) con queste differenze:

- importi come `Decimal`, mai `float`;
- solo lettura garantita dal codice: l'unico metodo per i dati è `leggi` (GET);
- logout esplicito alla chiusura (`async with`), per non lasciare sessioni aperte;
- verifica del certificato TLS attiva per default;
- un client per database: una società = un database Proffix (PXEPICO, ERUNNA, EMI Harmony);
- codici lavoro normalizzati (`L261` → `L26001`).

```python
from epico_proffix import ClientProffix, ConfigurazioneProffix

async with ClientProffix(ConfigurazioneProffix.da_ambiente("PXEPICO")) as px:
    async for pagina in px.pagine("/AUF/Dokument", campi="DokumentNr,Dokumenttyp,Datum"):
        ...
```

Variabili d'ambiente: `PROFFIX_BASE_URL` (con `/pxapi/v4`), `PROFFIX_USER`, `PROFFIX_PASSWORD`,
`PROFFIX_API_PASSWORD`, `PROFFIX_VERIFY_SSL` (default `true`). Le credenziali restano in Coolify.

## Inventario dei diritti API

```bash
python -m epico_proffix.inventario --database PXEPICO --database <DB ERUNNA> --database <DB EMI>
```

Prova un record per percorso e stampa stato HTTP e nomi dei campi, senza dati.

## Uso da un altro progetto

Si installa da una versione fissa (tag `vX.Y.Z` o commit), mai da un branch:

```toml
dependencies = ["epico-proffix @ git+https://github.com/curzio-ops/epico-proffix@<tag-o-commit>"]
```

Versione 0.1.0 = commit `8167df7`.

## Sviluppo

```bash
uv sync && uv run pytest && uv run ruff check . && uv run ruff format --check .
```
