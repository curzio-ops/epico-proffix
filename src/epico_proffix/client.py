"""Client asincrono per la REST-API Proffix V4, in sola lettura.

Solo lettura garantita dal codice: l'unico metodo pubblico per i dati è ``leggi`` (GET).
Le sole richieste non-GET sono login (``POST /PRO/Login``) e logout (``DELETE /PRO/Login``).

Autenticazione (verificata sul server epico dall'AGENDA):
- password utente e password API si inviano come SHA-256 esadecimale;
- ``POST /PRO/Login`` con ``{Benutzer, Passwort, Datenbank: {Name}, Module}`` e header ``PxApiKey``;
- la risposta porta ``PxSessionId`` negli header; va rimandato a ogni richiesta.

Filtri Proffix: uguaglianza ``==``, stringhe tra apici singoli; i campi annidati non sono filtrabili.

Ogni client lavora su un solo database Proffix (una società = un database).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import httpx

log = logging.getLogger("epico_proffix")


class ErroreProffix(Exception):
    """Errore di rete, di protocollo o risposta inattesa."""


class ErroreAccessoProffix(ErroreProffix):
    """Credenziali, password API o database non validi."""


def sha256(testo: str) -> str:
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


def decodifica(testo: str) -> Any:
    """JSON con i numeri decimali come Decimal (mai float: sono importi)."""
    return json.loads(testo, parse_float=Decimal) if testo else None


@dataclass(frozen=True)
class ConfigurazioneProffix:
    url_base: str  # es. https://server:porta/pxapi/v4
    database: str
    utente: str
    password: str = field(repr=False)
    password_api: str = field(repr=False)
    moduli: tuple[str, ...] = ("VOL",)
    verifica_tls: bool = True
    timeout_secondi: float = 60.0

    @classmethod
    def da_ambiente(cls, database: str, prefisso: str = "PROFFIX_") -> ConfigurazioneProffix:
        """Legge ``<prefisso>BASE_URL``, ``USER``, ``PASSWORD``, ``API_PASSWORD``, ``VERIFY_SSL``.

        Il nome del database si passa esplicitamente: ogni società ha il suo.
        """

        def env(nome: str, default: str | None = None) -> str:
            valore = os.environ.get(prefisso + nome, default)
            if valore is None:
                raise ErroreProffix(f"Variabile d'ambiente {prefisso}{nome} mancante")
            return valore

        return cls(
            url_base=env("BASE_URL").rstrip("/"),
            database=database,
            utente=env("USER"),
            password=env("PASSWORD"),
            password_api=env("API_PASSWORD"),
            verifica_tls=env("VERIFY_SSL", "true").strip().lower() in ("1", "true", "yes", "on"),
        )


class ClientProffix:
    def __init__(self, config: ConfigurazioneProffix, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.config = config
        self._chiave_api = sha256(config.password_api)
        self._sessione: str | None = None
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            base_url=config.url_base,
            verify=config.verifica_tls,
            timeout=config.timeout_secondi,
            transport=transport,
        )

    async def __aenter__(self) -> ClientProffix:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.chiudi()

    async def _accedi(self) -> str:
        async with self._lock:
            if self._sessione:
                return self._sessione
            corpo = {
                "Benutzer": self.config.utente,
                "Passwort": sha256(self.config.password),
                "Datenbank": {"Name": self.config.database},
                "Module": list(self.config.moduli),
            }
            try:
                r = await self._http.post("/PRO/Login", json=corpo, headers={"PxApiKey": self._chiave_api})
            except httpx.HTTPError as exc:
                raise ErroreAccessoProffix(f"Proffix non raggiungibile: {exc}") from exc
            if r.status_code not in (200, 201):
                raise ErroreAccessoProffix(f"Accesso Proffix rifiutato ({r.status_code}): {r.text[:200]}")
            sessione = r.headers.get("PxSessionId")
            if not sessione:
                raise ErroreAccessoProffix("Accesso Proffix senza PxSessionId nella risposta")
            self._sessione = sessione
            log.info("Proffix: accesso al database %s", self.config.database)
            return sessione

    async def chiudi(self) -> None:
        """Chiude la sessione Proffix (libera la licenza) e la connessione HTTP."""
        if self._sessione:
            try:
                await self._http.delete(
                    "/PRO/Login", headers={"PxSessionId": self._sessione, "PxApiKey": self._chiave_api}
                )
            except httpx.HTTPError as exc:
                log.warning("Proffix: logout non riuscito: %s", exc)
            self._sessione = None
        await self._http.aclose()

    async def _get(self, percorso: str, parametri: dict[str, Any] | None) -> httpx.Response:
        for tentativo in (1, 2):
            sessione = await self._accedi()
            try:
                r = await self._http.get(
                    percorso, params=parametri, headers={"PxSessionId": sessione, "PxApiKey": self._chiave_api}
                )
            except httpx.HTTPError as exc:
                raise ErroreProffix(f"Proffix GET {percorso}: {exc}") from exc
            if r.status_code == 401 and tentativo == 1:
                log.info("Proffix: sessione scaduta, nuovo accesso")
                self._sessione = None
                continue
            return r
        raise AssertionError("irraggiungibile")

    async def leggi(self, percorso: str, parametri: dict[str, Any] | None = None) -> httpx.Response:
        """GET grezzo: la risposta si interpreta con ``decodifica(r.text)``. Nessun errore sugli stati HTTP."""
        if not percorso.startswith("/") or percorso.upper().startswith("/PRO/LOGIN"):
            raise ValueError(f"Percorso non ammesso: {percorso}")
        return await self._get(percorso, parametri)

    async def leggi_json(self, percorso: str, parametri: dict[str, Any] | None = None) -> Any:
        r = await self.leggi(percorso, parametri)
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise ErroreProffix(f"Proffix GET {percorso}: {r.status_code} {r.text[:200]}")
        return decodifica(r.text)

    async def pagine(
        self,
        percorso: str,
        *,
        campi: str | None = None,
        filtro: str | None = None,
        ordine: str | None = None,
        per_pagina: int = 1000,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Scorre una collezione a pagine (``Limit``/``Offset``)."""
        offset = 0
        while True:
            parametri: dict[str, Any] = {"Limit": per_pagina, "Offset": offset}
            if campi:
                parametri["Felder"] = campi
            if filtro:
                parametri["Filter"] = filtro
            if ordine:
                parametri["Sort"] = ordine
            pagina = await self.leggi_json(percorso, parametri) or []
            if not isinstance(pagina, list):
                raise ErroreProffix(f"Proffix GET {percorso}: attesa una lista")
            if pagina:
                yield pagina
            if len(pagina) < per_pagina:
                return
            offset += per_pagina

    async def documento(self, dokument_nr: int) -> dict[str, Any] | None:
        """Documento del modulo ordini (``AUF/Dokument``): offerte, fatture, note di credito, ..."""
        return await self.leggi_json(f"/AUF/Dokument/{int(dokument_nr)}")
