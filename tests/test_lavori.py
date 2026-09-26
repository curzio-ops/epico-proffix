import pytest

from epico_proffix import normalizza_codice_lavoro, varianti_codice_lavoro


@pytest.mark.parametrize(
    ("codice", "atteso"),
    [
        ("L26001", "L26001"),
        ("L261", "L26001"),
        ("l2610", "L26010"),
        ("L26163", "L26163"),
        ("L26100", "L26100"),
        (" L261234 ", "L261234"),
        ("L26", None),
        ("X26001", None),
        ("L260", None),
        ("", None),
    ],
)
def test_normalizza(codice, atteso):
    assert normalizza_codice_lavoro(codice) == atteso


def test_varianti():
    assert varianti_codice_lavoro("L26001") == ["L26001", "L261"]
    assert varianti_codice_lavoro("L26163") == ["L26163"]
    assert varianti_codice_lavoro("L2610") == ["L26010", "L2610"]
