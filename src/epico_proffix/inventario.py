"""Inventario dei diritti dell'utente API Proffix (§11 punto 4 delle specifiche).

Per ogni percorso prova a leggere un solo record e riporta: stato HTTP, numero di record se
Proffix lo indica, nomi dei campi. Non stampa i dati. Non scrive nulla su Proffix.

Uso sul server (dove ci sono le credenziali, variabili PROFFIX_*):

    python -m epico_proffix.inventario --database PXEPICO --database <DB ERUNNA> --database <DB EMI>

I percorsi oltre ad AUF/Dokument e AUF/Dokumentposition (già usati dall'AGENDA) sono candidati
da verificare: un 404 può voler dire "percorso diverso" oppure "modulo non abilitato".
"""

import argparse
import asyncio
import sys

from epico_proffix.client import ClientProffix, ConfigurazioneProffix, ErroreProffix, decodifica

PERCORSI = [
    ("/AUF/Dokument", "Documenti (offerte, fatture, note di credito) — usato dall'AGENDA"),
    ("/AUF/Dokumentposition", "Posizioni dei documenti, con lavoro (Auftrag) — usato dall'AGENDA"),
    ("/ADR/Adresse", "Indirizzi (clienti e fornitori) — candidato"),
    ("/LAG/Artikel", "Articoli — candidato"),
    ("/DEB/Offenerposten", "Partite aperte debitori — candidato"),
    ("/KRD/Offenerposten", "Partite aperte creditori — candidato"),
    ("/KRD/Kreditor", "Fornitori (creditori) — candidato"),
    ("/PRO/Datei", "File e allegati (PDF) — candidato"),
    ("/PRO/Liste", "Liste di stampa (generazione PDF) — candidato"),
]


async def inventario(config: ConfigurazioneProffix, percorsi: list[tuple[str, str]]) -> list[dict]:
    risultati = []
    async with ClientProffix(config) as px:
        for percorso, descrizione in percorsi:
            riga = {"percorso": percorso, "descrizione": descrizione, "stato": None, "record": None, "campi": []}
            try:
                r = await px.leggi(percorso, {"Limit": 1})
                riga["stato"] = r.status_code
                riga["record"] = r.headers.get("FilteredCount")
                if r.status_code == 200:
                    dati = decodifica(r.text)
                    primo = dati[0] if isinstance(dati, list) and dati else dati
                    if isinstance(primo, dict):
                        riga["campi"] = sorted(primo)
            except ErroreProffix as exc:
                riga["stato"] = f"errore: {exc}"
            risultati.append(riga)
    return risultati


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m epico_proffix.inventario")
    parser.add_argument("--database", action="append", required=True, help="Nome del database Proffix (ripetibile)")
    parser.add_argument("--percorso", action="append", help="Percorso aggiuntivo da provare (ripetibile)")
    args = parser.parse_args()
    percorsi = PERCORSI + [(p, "aggiunto a mano") for p in (args.percorso or [])]
    esito = 0
    for db in args.database:
        print(f"\n=== Database {db} ===")
        try:
            righe = asyncio.run(inventario(ConfigurazioneProffix.da_ambiente(db), percorsi))
        except ErroreProffix as exc:
            print(f"  accesso non riuscito: {exc}")
            esito = 1
            continue
        for r in righe:
            campi = ", ".join(r["campi"][:15]) + (" …" if len(r["campi"]) > 15 else "")
            record = f" · {r['record']} record" if r["record"] else ""
            print(f"  {r['stato']!s:>4}  {r['percorso']:<24} {r['descrizione']}{record}")
            if campi:
                print(f"        campi: {campi}")
    sys.exit(esito)


if __name__ == "__main__":
    main()
