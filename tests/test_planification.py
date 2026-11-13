"""Second déclenchement : seule une génération écrite depuis le début de la nuit (20 h UTC)
l'arrête ; une mise à jour faite dans la journée n'empêche jamais la nuit."""
import datetime as dt

from empreinte_src.planification import a_faire, debut_de_nuit

UTC = dt.timezone.utc


def t(j, h, m=0):
    return dt.datetime(2026, 11, j, h, m, tzinfo=UTC)


def test_debut_de_nuit():
    assert debut_de_nuit(t(6, 20, 30)) == t(6, 20)
    assert debut_de_nuit(t(7, 6, 25)) == t(6, 20)
    assert debut_de_nuit(t(7, 19, 59)) == t(6, 20)


def test_une_mise_a_jour_de_la_journee_n_empeche_pas_la_nuit():
    # Cas du 06/11/2026 : génération écrite à 16 h 44, déclenchements à 20 h 30 et 23 h 30.
    assert a_faire("2026-11-06T16:44:00+00:00", t(6, 20, 30))
    assert a_faire("2026-11-06T16:44:00+00:00", t(6, 23, 30))


def test_le_second_declenchement_s_arrete_si_la_nuit_a_ecrit():
    assert not a_faire("2026-11-06T20:52:00+00:00", t(6, 23, 30))
    assert a_faire("2026-11-06T20:52:00+00:00", t(7, 20, 30))      # nuit suivante
    assert a_faire(None, t(6, 20, 30))


def test_manifeste_illisible_la_nuit_se_fait(monkeypatch, capsys):
    """Issue #41 (rouverte) : une erreur de l'API à la planification ne supprime pas la nuit."""
    from empreinte_src import planification
    appels = []

    def illisible(depot):
        appels.append(depot)
        raise RuntimeError("lecture du manifeste distant impossible : HTTP 502")
    monkeypatch.setattr(planification, "manifeste_distant", illisible)
    monkeypatch.setattr("sys.argv", ["planification", "--depot", "o/d", "--pause", "0"])
    planification.main()
    out = capsys.readouterr()
    assert out.out.strip() == "true" and len(appels) == 3 and "HTTP 502" in out.err
