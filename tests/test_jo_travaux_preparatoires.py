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
