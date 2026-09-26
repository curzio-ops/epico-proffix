"""Client in sola lettura per la REST-API Proffix V4."""

from epico_proffix.client import (
    ClientProffix,
    ConfigurazioneProffix,
    ErroreAccessoProffix,
    ErroreProffix,
    decodifica,
)
from epico_proffix.lavori import normalizza_codice_lavoro, varianti_codice_lavoro

__all__ = [
    "ClientProffix",
    "ConfigurazioneProffix",
    "ErroreAccessoProffix",
    "ErroreProffix",
    "decodifica",
    "normalizza_codice_lavoro",
    "varianti_codice_lavoro",
]
