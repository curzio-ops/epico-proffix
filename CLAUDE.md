# CLAUDE.md — epico-proffix

Client Python **in sola lettura** per la REST-API Proffix V4, usato da epico FATTURA e (in futuro) dall'AGENDA.

Regole:
- Mai scrivere su Proffix: l'unico metodo per i dati è `leggi` (GET). Login/logout sono le sole altre richieste.
- Importi sempre `Decimal`, mai `float`.
- Nessuna credenziale né nome di server nel codice: tutto da variabili d'ambiente.
- Un client per database Proffix (una società = un database).
- Test obbligatori per ogni cambiamento (`uv run pytest`), `ruff check` e `ruff format` puliti.
- Versioni fisse: i progetti che lo usano puntano a un tag `vX.Y.Z` o a un commit, mai a un branch.
- Lingua dei commenti e dei messaggi: italiano.
