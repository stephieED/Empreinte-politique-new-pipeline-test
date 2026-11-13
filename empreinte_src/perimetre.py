"""Périmètre publié (cahier 4.1, sans budgets ni mandats locaux ; décision du 07/11/2026).

Un seul endroit dit quelles législatures ont une fiche et une activité servie, et de quels points
d'accès viennent les faits de chacune. Les composeurs, les règles et les contrôles le lisent ici :
étendre le périmètre, c'est changer ce module, pas chercher les « XVIIe » dans le code.

| Objet | Périmètre (cahier 4.1) |
| --- | --- |
| Législatures, groupes, lignées | XIVe à XVIIe |
| Scrutins, amendements, dossiers, questions | XIVe à XVIIe |
| Prises de parole en séance | XVe à XVIIe |
| Gouvernements, actes réglementaires | depuis la XIVe (20/06/2012 ; décision du 13/11/2026) |
"""
from __future__ import annotations

# Législatures publiées : une fiche chacune, et l'activité de l'Assemblée lue pour chacune.
LEGISLATURES = (14, 15, 16, 17)
# Prises de parole en séance : à partir de cette législature (cahier 4.1 : « XVe → XVIIe »).
PAROLES_DEPUIS = 15
LEGISLATURES_PAROLES = tuple(n for n in LEGISLATURES if n >= PAROLES_DEPUIS)
# Gouvernements publiés : ceux qui traversent ces législatures (d'Ayrault II à aujourd'hui).
# Décision du 13/11/2026 (« on commence à la même période que la 14e leg ») : la XIVe, et non
# 2007 (Fillon I) comme le disait le cahier 4.1 ; le Journal officiel à partir de la même date.
LEGISLATURES_GOUVERNEMENTS = LEGISLATURES

# Archive des acteurs de chaque législature : AMO20 pour la XIVe, AMO30 ensuite (même contenu,
# nom de fichier différent à la source).
_ACTEURS = {14: "an-amo20-l14"}


def point(famille: str, legislature: int) -> str | None:
    """Point d'accès (config/points_acces.yaml) d'une famille de l'Assemblée pour une législature.
    `None` quand la source n'existe pas (comptes rendus de la XIVe : hors périmètre)."""
    if famille == "acteurs":
        return _ACTEURS.get(legislature, f"an-amo30-l{legislature}")
    if famille == "syceron" and legislature < PAROLES_DEPUIS:
        return None
    return f"an-{famille}-l{legislature}"


def points(famille: str, legislatures=None) -> list[str]:
    """Points d'accès d'une famille pour des législatures (toutes celles du périmètre par défaut)."""
    legs = LEGISLATURES if legislatures is None else legislatures
    return [p for p in (point(famille, n) for n in sorted(set(legs))) if p]


def romain(n: int) -> str:
    """Rend `n` en chiffres romains, écrits avec les seuls X, IX, V, IV et I : juste jusqu'à 39."""
    v = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    s, x = "", int(n)
    for k, r in v:
        while x >= k:
            s, x = s + r, x - k
    return s


def nom_legislature(n: int) -> str:
    """Rend le nom d'une législature : « XVIIe législature », « Ire législature » pour la première."""
    return f"{romain(n)}{'re' if n == 1 else 'e'} législature"


def plage(legislatures=None) -> str:
    """« XIVe à la XVIIe » : la plage écrite dans les textes servis (« de la XIVe à la XVIIe législature »)."""
    legs = sorted(LEGISLATURES if legislatures is None else legislatures)
    if len(legs) == 1:
        return f"{romain(legs[0])}e"
    return f"{romain(legs[0])}e à la {romain(legs[-1])}e"
