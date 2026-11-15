"""Regroupements pour l'affichage (issues #75 à #89 ; doc. 1, 1.7.2).

L'interface montre parfois moins de cases que la source n'a de codes : une légende de onze
commissions pour 37 commissions saisies au fond (#88), neuf sorts d'un texte (#89)… Un tel
regroupement est une lecture propre à l'affichage d'aujourd'hui, et il peut changer. Forme
commune, fixée avec la propriétaire le 14/11/2026 :

- **la table est une décision** (`references/regroupement/<nom>.yaml`), validée en fusionnant :
  chaque entrée met un code de la source (`champ` = `valeur`) dans une case (`groupe`,
  `libelle`) ; l'ordre des cases est celui de leur première apparition, ou celui de leur champ
  `ordre` quand la table le donne ; un code est rangé par la première entrée qui lui correspond ;
- **elle est servie à part**, dans `regroupements.json.gz` : pour chaque regroupement, ses cases
  dans l'ordre, et chaque code présent dans le corpus avec sa case et l'entrée qui l'y a mis.
  Les fiches ne changent pas : elles gardent les codes de la source, à leur granularité
  d'origine. Changer un regroupement ne demande ni recollecte ni réécriture des fiches ;
- **un code qui n'entre dans aucune case** est servi sans case (`groupe` vide) et A7 le nomme :
  jamais rangé par défaut.

Chaque regroupement a sa **source** (`SOURCES`) : la requête qui rend les codes présents dans le
corpus, avec les champs que ses entrées peuvent viser."""
from __future__ import annotations

from ..composition import CONTRAT
from ..perimetre import LEGISLATURES

NOM = "regroupements"
VERSION = 1
DEPEND = ("R-MATIERE", "R-QUALITE", "R-SUJET")

# nom du regroupement → (tables lues, requête des codes présents, champs du code par priorité).
# La requête rend une ligne par code : les champs visés par les entrées, et `libelle_source`. Le
# code servi est le premier champ non vide.
SOURCES = {
    # #88 : la commission saisie au fond (R-MATIERE), ou, sans commission, le statut de la matière
    "commission_saisie": (("matiere", "an_acteurs__organe"), """
        SELECT m.commission, any_value(o.type_organe) AS type_commission, m.statut AS matiere_statut,
               any_value(m.libelle) AS libelle_source
        FROM matiere m LEFT JOIN an_acteurs__organe o ON o.uid = m.commission
        WHERE CAST(m.legislature AS VARCHAR) IN ({legs})
        GROUP BY m.commission, m.statut""", ("commission", "matiere_statut")),
    # #87 : la nature d'une prise de parole (R-SUJET v2) : genre du point, créneau, type de sujet
    "nature_parole": (("sujet_intervention",), """
        SELECT DISTINCT genre_point, code_creneau, type_sujet, NULL::VARCHAR AS libelle_source
        FROM sujet_intervention""", ("genre_point", "code_creneau", "type_sujet")),
    # #75 : la qualité de l'orateur (R-QUALITE) ; une qualité non établie reste hors des cases
    "qualite_orateur": (("qualite_orateur",), """
        SELECT qualite, NULL::VARCHAR AS libelle_source
        FROM qualite_orateur WHERE qualite IS NOT NULL GROUP BY qualite""", ("qualite",)),
}


def _par_nom(decisions: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for d in decisions:
        out.setdefault(d.get("nom"), []).append(d)
    for entrees in out.values():
        # ordre du fichier : « regroupement/x.yaml#3 »
        entrees.sort(key=lambda d: (str(d.get("fichier", "")).split("#")[0],
                                    int(str(d.get("fichier", "#0")).rsplit("#", 1)[-1] or 0)))
    return out


def composer(ctx, ecr):
    """Sert chaque regroupement décidé dans `regroupements.json.gz` (voir la description)."""
    tables = []
    for nom, entrees in sorted(_par_nom(ctx.decisions.get("regroupement", [])).items()):
        groupes: list[list] = []
        for e in entrees:
            if e.get("groupe") not in [g[0] for g in groupes]:
                groupes.append([e.get("groupe"), e.get("libelle"), e.get("ordre")])
        # ordre de la légende : le champ `ordre` s'il est donné, sinon l'ordre d'apparition
        groupes.sort(key=lambda g: (g[2] is None, g[2] if g[2] is not None else 0))
        groupes = [[g, lib, k] for k, (g, lib, _) in enumerate(groupes, 1)]
        codes, raison, champs = [], None, []
        source = SOURCES.get(nom)
        if source is None:
            raison = "aucune source connue pour ce regroupement"
        elif not all(ctx.existe(t) for t in source[0]):
            raison = "tables absentes cette nuit : " + ", ".join(t for t in source[0] if not ctx.existe(t))
        else:
            _, sql, champs_code = source
            champs = list(champs_code)
            legs = ", ".join(f"'{n}'" for n in LEGISLATURES)
            res = ctx.con.execute(sql.format(legs=legs))
            cols = [c[0] for c in res.description]
            for ligne in sorted(res.fetchall(), key=lambda l: tuple(str(x) for x in l)):
                r = dict(zip(cols, ligne))
                champ = next((c for c in champs_code if r.get(c) is not None), champs_code[-1])
                e = next((e for e in entrees if r.get(e.get("champ")) is not None
                          and str(r.get(e.get("champ"))) == str(e.get("valeur"))), None)
                ligne_code = [champ, r.get(champ), r.get("libelle_source"), e.get("groupe") if e else None,
                              f"{e.get('champ')} = {e.get('valeur')}" if e else None]
                if ligne_code not in codes:            # plusieurs lignes de la source, un même code
                    codes.append(ligne_code)
        d0 = entrees[0]
        tables.append({
            "nom": nom, "titre": d0.get("titre"), "description": d0.get("description"),
            "decision": str(d0.get("fichier", "")).split("#")[0], "date": str(d0.get("date")),
            # le code d'une valeur est son premier champ non vide, dans cet ordre
            "champs": champs,
            "groupes": {"colonnes": ["groupe", "libelle", "ordre"], "lignes": groupes},
            "codes": {"colonnes": ["champ", "code", "libelle_source", "groupe", "par"], "lignes": codes},
            "raison": raison})
    if tables:
        ecr.ecrire("regroupements.json.gz", {"contrat": CONTRAT, "publication": ecr.id_publication,
                                             "genere_le": ecr.genere_le, "regroupements": tables})
