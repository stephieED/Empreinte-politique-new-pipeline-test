"""Lecteur du JO, version 2 : travaux préparatoires d'une loi (issue #35). Texte réel de la loi
n° 2026-1015 (livraison du JO du 03/11/2026), recopié."""
from lxml import etree

from empreinte_src.lecteurs.jo_actes import _travaux

TP = """<TEXTE_VERSION><TP><CONTENU><div align="left">
<p>(1) Travaux préparatoires : loi n° 2026-1015.</p>
<p>Assemblée nationale :</p>
<p>Proposition de loi n° 1817 ;</p>
<p>Rapport de M. Max Mathiasin, au nom de la commission des lois, n° 2810 ;</p>
<p>Discussion et adoption, après engagement de la procédure accélérée, le 28 mai 2026 (TA n° 290).</p>
<p>Sénat :</p>
<p>Proposition de loi, adoptée par l'Assemblée nationale, n° 672 (2025-2026) ;</p>
<p>Rapport de M. Louis Vogel, au nom de la commission des lois, n° 55 (2026-2027) ;</p>
<p>Texte de la commission n° 56 (2026-2027) ;</p>
<p>Discussion et adoption le 20 octobre 2026 (TA n° 11, 2026-2027).</p>
</div></CONTENU></TP></TEXTE_VERSION>"""


def test_travaux_preparatoires_lus_ligne_a_ligne():
    lignes = _travaux(etree.fromstring(TP), "jorf:X", "20261103-000000", "u")
    vu = [(l["chambre"], l["nature"], l["numero"], l["numero_ta"], l["session"]) for l in lignes]
    assert vu == [("AN", "proposition_de_loi", "1817", None, None),
                  ("AN", "rapport", "2810", None, None),
                  ("AN", "discussion", None, "290", None),
                  ("SN", "proposition_de_loi", "672", None, "2025-2026"),
                  ("SN", "rapport", "55", None, "2026-2027"),
                  ("SN", "texte_commission", "56", None, "2026-2027"),
                  ("SN", "discussion", None, "11", None)]
    assert [l["rang"] for l in lignes] == list(range(7))


def test_sans_travaux_preparatoires():
    assert _travaux(etree.fromstring("<TEXTE_VERSION><TP><CONTENU/></TP></TEXTE_VERSION>"), "a", "l", "u") == []


# Version 3 (issue #146) : loi 2019-284, texte réel recopié (archive globale du JO) ; le bloc TP
# est vide, les travaux sont publiés à la fin du bloc des signataires.
SIGNATAIRES = """<TEXTE_VERSION><SIGNATAIRES><CONTENU>
<p>Fait à Paris, le 8 avril 2019.</p>
<div align="left"><p>Emmanuel Macron</p><p>Par le Président de la République :</p></div>
<p>(1) Travaux préparatoires : loi n° 2019-284.</p>
<p>Sénat :</p>
<p>Projet de loi n° 582 (2016-2017) ;</p>
<p>Discussion et adoption (procédure d'examen simplifié), le 22 mars 2018 (TA n° 79, 2017-2018).</p>
<p>Assemblée nationale :</p>
<p>Projet de loi, adopté par le Sénat, n° 810 ;</p>
<p>Rapport de M. Bruno Joncour, au nom de la commission des affaires étrangères, n° 1365 ;</p>
<p>Discussion et adoption le 29 mars 2019 (TA n° 251).</p>
</CONTENU></SIGNATAIRES><TP><CONTENU/></TP></TEXTE_VERSION>"""


def test_travaux_lus_dans_les_signataires_quand_le_bloc_tp_est_vide():
    lignes = _travaux(etree.fromstring(SIGNATAIRES), "jorf:X", "l", "u")
    vu = [(l["chambre"], l["nature"], l["numero"], l["numero_ta"], l["bloc"]) for l in lignes]
    assert vu == [("SN", "projet_de_loi", "582", None, "SIGNATAIRES"),
                  ("SN", "discussion", None, "79", "SIGNATAIRES"),
                  ("AN", "projet_de_loi", "810", None, "SIGNATAIRES"),
                  ("AN", "rapport", "1365", None, "SIGNATAIRES"),
                  ("AN", "discussion", None, "251", "SIGNATAIRES")]
    # Les signataires eux-mêmes (« Par le Président de la République : ») ne sont pas lus.
    assert all(l["chambre"] in ("SN", "AN") for l in lignes)


def test_travaux_dans_les_signataires_sans_annonce_ni_bloc_tp():
    """Loi 2015-275 : ni bloc TP, ni « Travaux préparatoires » ; le premier intitulé de chambre
    ouvre les travaux. « (TA, n° 671) » (loi 2016-113) est un texte adopté."""
    x = ("<TEXTE_VERSION><SIGNATAIRES><CONTENU>Fait à Paris, le 13 mars 2015.\nLaurent Fabius\n"
         "Sénat :\nProjet de loi, n° 493 (2011-2012) ;\nAssemblée nationale :\n"
         "Projet de loi, adopté par le Sénat, n° 1181 ;\nDiscussion et adoption le 28 janvier 2016 (TA, n° 671)."
         "</CONTENU></SIGNATAIRES></TEXTE_VERSION>")
    lignes = _travaux(etree.fromstring(x), "a", "l", "u")
    assert [(l["chambre"], l["numero"], l["numero_ta"]) for l in lignes] == [
        ("SN", "493", None), ("AN", "1181", None), ("AN", None, "671")]


def test_signataires_sans_travaux():
    x = ("<TEXTE_VERSION><SIGNATAIRES><CONTENU>Fait à Paris, le 21 octobre 2019.\nEmmanuel Macron\n"
         "Par le Président de la République :\nLe Premier ministre,\nEdouard Philippe"
         "</CONTENU></SIGNATAIRES><TP><CONTENU/></TP></TEXTE_VERSION>")
    assert _travaux(etree.fromstring(x), "a", "l", "u") == []


def test_legislature_nommee_par_le_jo():
    """Loi 2020-839 (ligne) et loi 2012-1474 (intitulé de chambre) : la législature que le JO
    nomme est gardée ; sinon, rien n'est déduit."""
    x = ("<TEXTE_VERSION><TP><CONTENU>(1) Travaux préparatoires : loi n° 2020-839.\n"
         "Assemblée nationale :\nProposition de loi n° 4348 (quatorzième législature) ;\n"
         "Rapport de M. André Chassaigne, au nom de la commission des affaires sociales, n° 4403 ;\n"
         "Proposition de loi, rejetée par le Sénat, n° 967 (quinzième législature) ;\n"
         "Assemblée nationale (treizième législature) :\nProjet de loi n° 4080 ;\n"
         "Sénat :\nProjet de loi n° 454 (2011-2012)</CONTENU></TP></TEXTE_VERSION>")
    lignes = _travaux(etree.fromstring(x), "a", "l", "u")
    assert [(l["chambre"], l["numero"], l["legislature"], l["bloc"]) for l in lignes] == [
        ("AN", "4348", 14, "TP"), ("AN", "4403", None, "TP"), ("AN", "967", 15, "TP"),
        ("AN", "4080", 13, "TP"), ("SN", "454", None, "TP")]
