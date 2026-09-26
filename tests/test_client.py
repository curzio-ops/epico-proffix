import json
from decimal import Decimal

import httpx
import pytest

from epico_proffix import ClientProffix, ConfigurazioneProffix, ErroreAccessoProffix
from epico_proffix.client import sha256

CONFIG = ConfigurazioneProffix(
    url_base="https://proffix.test/pxapi/v4", database="PXEPICO", utente="API", password="pw", password_api="api"
)


class ServerFinto:
    def __init__(self, documenti: list[dict] | None = None, scade_dopo: int | None = None) -> None:
        self.richieste: list[httpx.Request] = []
        self.documenti = documenti or []
        self.sessioni = 0
        self.scade_dopo = scade_dopo
        self.get_con_sessione = 0

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.richieste.append(req)
        if req.url.path == "/pxapi/v4/PRO/Login" and req.method == "POST":
            corpo = json.loads(req.content)
            if corpo["Passwort"] != sha256("pw") or req.headers["PxApiKey"] != sha256("api"):
                return httpx.Response(401, text="no")
            self.sessioni += 1
            return httpx.Response(201, headers={"PxSessionId": f"s{self.sessioni}"})
        if req.url.path == "/pxapi/v4/PRO/Login" and req.method == "DELETE":
            return httpx.Response(204)
        assert req.method == "GET"
        self.get_con_sessione += 1
        if self.scade_dopo is not None and self.get_con_sessione == self.scade_dopo:
            return httpx.Response(401)
        if req.url.path == "/pxapi/v4/AUF/Dokument":
            limit, offset = int(req.url.params["Limit"]), int(req.url.params["Offset"])
            return httpx.Response(200, text=json.dumps(self.documenti[offset : offset + limit]))
        if req.url.path == "/pxapi/v4/AUF/Dokument/100493":
            return httpx.Response(200, text='{"DokumentNr": 100493, "TotalSW": 1290.05, "TotalInklusivSW": 1394.55}')
        return httpx.Response(404)


async def test_accesso_con_hash_e_importi_decimali():
    server = ServerFinto()
    async with ClientProffix(CONFIG, transport=httpx.MockTransport(server)) as px:
        doc = await px.documento(100493)
    assert doc["TotalSW"] == Decimal("1290.05")
    assert isinstance(doc["TotalInklusivSW"], Decimal)
    login = server.richieste[0]
    assert json.loads(login.content)["Datenbank"] == {"Name": "PXEPICO"}
    assert server.richieste[1].headers["PxSessionId"] == "s1"
    assert server.richieste[-1].method == "DELETE"  # logout alla chiusura


async def test_credenziali_errate():
    cfg = ConfigurazioneProffix(**{**CONFIG.__dict__, "password": "sbagliata"})
    async with ClientProffix(cfg, transport=httpx.MockTransport(ServerFinto())) as px:
        with pytest.raises(ErroreAccessoProffix):
            await px.documento(1)


async def test_nuovo_accesso_se_la_sessione_scade():
    server = ServerFinto(scade_dopo=1)
    async with ClientProffix(CONFIG, transport=httpx.MockTransport(server)) as px:
        assert (await px.documento(100493))["DokumentNr"] == 100493
    assert server.sessioni == 2


async def test_paginazione():
    server = ServerFinto(documenti=[{"DokumentNr": i} for i in range(25)])
    async with ClientProffix(CONFIG, transport=httpx.MockTransport(server)) as px:
        pagine = [p async for p in px.pagine("/AUF/Dokument", per_pagina=10)]
    assert [len(p) for p in pagine] == [10, 10, 5]


async def test_solo_lettura():
    async with ClientProffix(CONFIG, transport=httpx.MockTransport(ServerFinto())) as px:
        with pytest.raises(ValueError):
            await px.leggi("/PRO/Login")
        assert not hasattr(px, "scrivi")
        assert not any(n in dir(px) for n in ("post", "put", "patch", "delete"))


def test_documento_inesistente_da_none():
    import asyncio

    async def prova():
        async with ClientProffix(CONFIG, transport=httpx.MockTransport(ServerFinto())) as px:
            return await px.documento(999)

    assert asyncio.run(prova()) is None
