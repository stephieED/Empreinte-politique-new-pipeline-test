"""R-LIGNEE : les lignées de groupe, leur numéro acquis et leur adresse (cahier 4.1, 4.3 et 6.1 ;
doc. 1, 1.2.2 et 1.5.2 ; doc. 5, Q22).

Une **lignée** est une suite de maillons (R-CONTINUITE-GROUPE) reliés par R-FILIATION (verdict
`suite`, décision comprise) : les maillons reliés, de proche en proche, forment une lignée. Un
maillon que rien ne relie à un prédécesseur commence une lignée (y compris un maillon dont la
filiation est `a_trancher` : il est publié comme sa propre lignée en attendant la décision,
défaut de Q22, et la table le dit).

**Numéro acquis** (`lig:NNNNNN`, registre `ctx.registre.lignees`, `empreinte_src/identites.py`) :
chaque lignée forme un groupe d'identifiants de source, ses organes `("an", "PO…")`. Un organe
déjà attribué garde son numéro ; une lignée nouvelle reçoit le suivant ; deux lignées réunies
(fusion, ou décision) gardent le plus ancien. Si des organes d'une même lignée enregistrée se
retrouvent dans deux lignées calculées (scission constatée après une décision), la lignée qui
garde le plus ancien organe garde le numéro ; l'autre reçoit un numéro neuf, et le registre
garde la trace (`jusqu_au`, motif `scission_constatee`). Sans registre, la règle échoue : elle
ne fabrique jamais de numéro de passage.

**Adresse** : inscrite une fois, à la première attribution, et jamais changée : forme lisible
du nom le plus récent de la lignée à cette date (`socialistes-et-apparentes`) ; si elle est
prise, on ajoute la première législature de la lignée, puis son numéro. Une lignée absorbée
garde son adresse, qui devient une redirection vers la lignée retenue (`lignee_adresse`).

**Publiée** : une lignée qui a un maillon dans les législatures des fiches de groupe
(`LEGISLATURES_AVEC_FICHE`, XIVe à XVIIe, cahier 4.1). Les maillons plus anciens (XIIe et XIIIe,
dans l'archive des acteurs) servent au calcul des filiations ; ils restent dans les tables et ne
sont pas affichés.
"""
from collections import defaultdict

import pyarrow as pa

from .r_identite import slug

NOM = "R-LIGNEE"
VERSION = 1
DEPEND = ("R-FILIATION", "R-CONTINUITE-GROUPE")
SORTIES = ("lignee", "lignee_maillon", "lignee_adresse")
DESCRIPTION = (
    "Une lignée réunit les groupes successifs d'une même famille : les groupes d'une législature "
    "qui n'en font qu'un, puis, d'une législature à l'autre, ceux que la règle de filiation relie. "
    "Chaque lignée reçoit une adresse qui ne change plus, même quand le groupe change de nom ; "
    "quand deux lignées se réunissent, l'ancienne adresse renvoie vers la lignée réunie. Les "
    "fiches de lignée couvrent les groupes de la XIVe législature à aujourd'hui.")

LEGISLATURES_AVEC_FICHE = (14, 15, 16, 17)


def appliquer(ctx):
    """Applique R-LIGNEE : réunit les maillons reliés par une filiation en lignées, leur donne un
    numéro acquis et une adresse dans le registre des lignées (`ctx.registre.lignees`, complété en
    mémoire), puis écrit `lignee`, `lignee_maillon` et `lignee_adresse` (voir la description du
    module). Lève `RuntimeError` sans registre ou sans génération (`ctx.generation`). Rend la
    couverture, `{nom: (numérateur, dénominateur)}` : `lignees_publiees`,
    `maillons_affiches_sans_filiation_en_attente`, `scissions_constatees`."""
    if ctx.registre is None:
        raise RuntimeError(
            "R-LIGNEE : aucun registre (ctx.registre est None). Le numéro et l'adresse d'une lignée "
            "sont acquis et viennent du registre de l'entrepôt : passer "
            "Contexte(..., registre=RegistreIdentites(<entrepôt>), generation=<n>).")
    if ctx.generation is None:
        raise RuntimeError("R-LIGNEE : génération inconnue (ctx.generation est None).")
    reg = ctx.registre.lignees
    gen = ctx.generation

    organes = ctx.x("""SELECT maillon, organe, legislature, debut, rang FROM maillon
                       ORDER BY debut, maillon, rang""")
    par_maillon: dict[str, list] = defaultdict(list)
    debut_maillon: dict[str, str] = {}
    for m, o, _, d, _ in organes:
        par_maillon[m].append(o)
        debut_maillon.setdefault(m, d)
    parent = {m: m for m in par_maillon}

    def racine(x):
        """Rend la racine du maillon `x` dans la forêt `parent` (union-find), en raccourcissant le
        chemin au passage : chaque maillon visité pointe ensuite vers son grand-parent."""
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in ctx.x("SELECT maillon_avant, maillon_apres FROM filiation WHERE verdict = 'suite'"):
        if a in parent and b in parent:
            ra, rb = racine(a), racine(b)
            if ra != rb:
                parent[max(ra, rb, key=lambda m: (debut_maillon[m], m))] = \
                    min(ra, rb, key=lambda m: (debut_maillon[m], m))
    composantes: dict[str, list] = defaultdict(list)
    for m in sorted(par_maillon, key=lambda m: (debut_maillon[m], m)):
        composantes[racine(m)].append(m)

    # Numéros acquis : un groupe d'identifiants par lignée calculée.
    groupes = {r: sorted(("an", o) for m in ms for o in par_maillon[m]) for r, ms in composantes.items()}
    reg.attribuer(list(groupes.values()), gen)
    lig_de = {}
    scissions = 0
    pris: dict[str, str] = {}
    # La lignée qui garde le plus ancien organe garde le numéro ; une autre qui l'aurait aussi
    # reçu (scission constatée) en reçoit un neuf.
    for r in sorted(composantes, key=lambda r: (debut_maillon[r], r)):
        lig = reg.numero(*groupes[r][0]) if len(groupes[r]) == 1 else \
            min({reg.numero(*k) for k in groupes[r]})
        if lig in pris:
            lig = reg.detacher(groupes[r], gen, "scission_constatee")
            scissions += 1
        pris[lig] = r
        lig_de[r] = lig

    # Libellés : nom le plus récent (dernier organe du dernier maillon).
    info = {m: x for m, *x in ctx.x("""
        SELECT maillon, any_value(legislature), min(debut_maillon), any_value(fin_maillon),
               arg_max(sigle, rang), arg_max(libelle, rang), any_value(position_maillon),
               list(organe ORDER BY rang), list(sigle ORDER BY rang), list(libelle ORDER BY rang),
               any_value(nb_organes)
        FROM maillon GROUP BY 1""")}
    lignes_l, lignes_m = [], []
    for r, ms in composantes.items():
        lig = lig_de[r]
        dernier = ms[-1]
        leg = [info[m][0] for m in ms]
        affiches = [m for m in ms if info[m][0] in LEGISLATURES_AVEC_FICHE]
        nom = info[dernier][4]
        adresse = reg.adresse(lig)
        if adresse is None:
            base = ctx.un(f"SELECT {slug('?')}", [nom or info[dernier][3] or lig])
            for essai in (base, f"{base}-{min(leg)}", f"{base}-{lig.split(':')[1]}"):
                if reg.inscrire(lig, essai, gen):
                    adresse = essai
                    break
        fin = None if any(info[m][2] is None for m in ms) else max(info[m][2] for m in ms)
        lignes_l.append({
            "lignee": lig, "adresse": adresse, "nom": nom, "sigle": info[dernier][3],
            "debut": info[ms[0]][1], "fin": fin, "en_cours": fin is None,
            "premiere_legislature": min(leg), "derniere_legislature": max(leg),
            "nb_maillons": len(ms), "nb_maillons_affiches": len(affiches),
            "debut_affiche": info[affiches[0]][1] if affiches else None,
            "publiee": bool(affiches) and adresse is not None,
            "raison_non_publiee": None if affiches and adresse else
            ("aucun_groupe_depuis_la_xive" if not affiches else "adresse_non_inscrite"),
            "maillon_racine": r})
        for k, m in enumerate(ms, 1):
            lignes_m.append({
                "lignee": lig, "maillon": m, "legislature": info[m][0], "rang_dans_lignee": k,
                "affiche": info[m][0] in LEGISLATURES_AVEC_FICHE, "debut": info[m][1], "fin": info[m][2],
                "sigle": info[m][3], "libelle": info[m][4], "position_maillon": info[m][5],
                "organes": info[m][6], "sigles": info[m][7], "libelles": info[m][8],
                "nb_organes": info[m][9]})
    ctx.con.register("_lg_l", pa.Table.from_pylist(lignes_l))
    ctx.con.register("_lg_m", pa.Table.from_pylist(lignes_m))
    ctx.ecrire("lignee", "SELECT * FROM _lg_l ORDER BY debut, lignee")
    ctx.ecrire("lignee_maillon", """
        SELECT m.*,
               (SELECT list(f.maillon_avant ORDER BY f.maillon_avant) FROM filiation f
                 WHERE f.maillon_apres = m.maillon AND f.verdict = 'suite') AS predecesseurs,
               (SELECT list(f.maillon_avant ORDER BY f.maillon_avant) FROM filiation f
                 WHERE f.maillon_apres = m.maillon AND f.verdict = 'a_trancher') AS filiation_a_trancher
        FROM _lg_m m ORDER BY m.lignee, m.rang_dans_lignee""")
    adr = [{"adresse": a["adresse"], "lignee_inscrite": a["per"], "lignee": reg.resoudre(a["per"]),
            "depuis": a["depuis"]} for a in reg.adresses]
    actives = {l["lignee"]: l["adresse"] for l in lignes_l}
    for a in adr:
        a["statut"] = "active" if actives.get(a["lignee"]) == a["adresse"] else "redirection"
    schema = pa.schema([("adresse", pa.string()), ("lignee_inscrite", pa.string()),
                        ("lignee", pa.string()), ("depuis", pa.int32()), ("statut", pa.string())])
    ctx.con.register("_lg_a", pa.Table.from_pylist(adr, schema=schema))
    ctx.ecrire("lignee_adresse", "SELECT * FROM _lg_a ORDER BY adresse")
    for t in ("_lg_l", "_lg_m", "_lg_a"):
        ctx.con.unregister(t)

    publiees = sum(1 for l in lignes_l if l["publiee"])
    attente = ctx.un("""SELECT count(DISTINCT maillon) FROM lignee_maillon
                        WHERE affiche AND len(filiation_a_trancher) > 0""")
    affiches = ctx.un("SELECT count(*) FROM lignee_maillon WHERE affiche")
    return {"lignees_publiees": (publiees, len(lignes_l)),
            "maillons_affiches_sans_filiation_en_attente": (affiches - attente, affiches),
            "scissions_constatees": (scissions, len(lignes_l))}
