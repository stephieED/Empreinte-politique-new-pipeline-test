import os
import zipfile

import pytest

EXTRAITS = os.path.join(os.path.dirname(__file__), "extraits")


@pytest.fixture
def extrait_agenda():
    return os.path.join(EXTRAITS, "agenda_l17_extrait.zip")


@pytest.fixture
def pa_agenda():
    return {"id": "an-agenda-l17", "source": "an", "type": "agenda", "format": "zip",
            "url": "http://exemple.invalid/Agenda.json.zip"}


def zip_avec(chemin, membres: dict):
    with zipfile.ZipFile(chemin, "w") as z:
        for n, b in membres.items():
            z.writestr(n, b)
    return chemin
