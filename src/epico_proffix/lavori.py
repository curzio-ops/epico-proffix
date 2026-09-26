"""Codici lavoro AGENDA (L + anno a due cifre + progressivo).

Forma normalizzata: progressivo di almeno tre cifre (``L26001``, ``L26163``, ``L261234``).
Proffix usa anche la forma compatta senza zeri iniziali (``L261`` = ``L26001``, ``L2610`` = ``L26010``):
verificato sul server epico dall'AGENDA.
"""

import re

_CODICE = re.compile(r"^L(\d{2})(\d{1,4})$")


def normalizza_codice_lavoro(codice: str) -> str | None:
    """Forma normalizzata del codice, oppure None se non è un codice lavoro."""
    m = _CODICE.match((codice or "").strip().upper())
    if not m:
        return None
    anno, progressivo = m.group(1), int(m.group(2))
    if progressivo == 0:
        return None
    return f"L{anno}{progressivo:03d}"


def varianti_codice_lavoro(codice: str) -> list[str]:
    """Forme con cui lo stesso lavoro può comparire in Proffix: normalizzata e compatta."""
    normale = normalizza_codice_lavoro(codice)
    if normale is None:
        return []
    compatta = f"L{normale[1:3]}{int(normale[3:])}"
    return [normale] if compatta == normale else [normale, compatta]
