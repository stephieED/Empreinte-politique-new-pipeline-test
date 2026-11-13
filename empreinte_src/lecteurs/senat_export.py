"""Sénat : l'export complet `export_sens.zip` (un dump PostgreSQL, `export_sens.sql`, 95 tables ;
mesures `autres-sources.md`, § 4).

Le dump est lu **en flux, table par table** : seules les tables de la liste blanche `LUES` sont
décodées ; les lignes de toutes les autres sont sautées sans être décodées. Les tables de
présence et de participation (`activite_participant`, `activite`, `activite_senateur`,
`activite_delegation`, `activite_loi`, `activites_liees`, `fonact_participant`,
`type_activite*` : règle 3) ne sont **jamais lues** ; les adresses, téléphones, courriels et
comptes de réseaux des sénateurs (`adresse`, `telephone`, `mel`, `senurl`, `sen.senema`) non
plus.

Ce qui est lu (préfixe `senat:` dans les identifiants) :
- `sen` → `identite_source` (`senat:<matricule>`) : état civil, profession, état
  (`ACTIF`/`ANCIEN`/`AUTRE`) ;
- `elusen` (+ `dpt` pour le libellé de la circonscription) → `mandat` de sénateur
  (`senat:elusen:<id>`) : dates de début, d'élection et de fin, cause de début et de fin
  (codes et libellés de `etadebman`/`etafinman`), circonscription, événement ;
- `memgrppol` (+ `typapppol`) → appartenance à un groupe politique (`senat:memgrppol:<id>`),
  avec le **libellé du groupe à la date** lu dans l'historique `libgrppol` (à la date de début
  de l'appartenance, à défaut à sa date de fin : la colonne `date_libelle` dit laquelle) ;
  `fonmemgrppol` (+ `fongrppol`) → fonction dans le groupe (`senat:fonmemgrppol:<id>`) ;
- `memcom` → appartenance à une commission (`senat:memcom:<id>`, libellé à la date lu dans
  `libcom`) ; `fonmemcom` (+ `foncom`) → fonction dans la commission ;
- `senbur` (+ `bur`) → fonction au bureau du Sénat (président, vice-président, questeur,
  secrétaire ; `AUCUNSEN` = « Sénateur », sans fonction : gardé tel quel) ;
- `grppol`, `com` → `organe` ; `libgrppol`, `libcom` → `organe_libelle` (historique daté des
  libellés, pour que les règles puissent recalculer le libellé à n'importe quelle date).

Les appartenances (`mem…`) et les fonctions (`fonmem…`) sont des lignes distinctes, comme à
la source (colonne `nature`) : une fonction « Membre » double souvent l'appartenance ; c'est
aux règles d'en décider.

Pièges de forme : format `COPY … FROM stdin` (tabulations, `\\N` pour le vide, échappements
`\\t`, `\\n`, `\\\\`…) ; libellés complétés d'espaces (`GR AMITIE …      `) ou faits d'espaces
seuls (`foncom.foncomlib` de `MEMBRECOM`) : resserrés, le vide devient `None` ; horodatages
`AAAA-MM-JJ hh:mm:ss` ramenés à la date (l'heure ne porte rien, sauf la date fictive
`1899-12-31 00:50:39` de `libgrppol`, gardée comme date `1899-12-31`).

Aucune adresse publique par ligne n'est donnée par le dump : l'adresse de la fiche d'un
sénateur (`senat.fr/senateur/<nom_prenom><matricule>.html`) ne s'y lit pas et ne se déduit pas
proprement du nom technique (`HUSSON_JEAN_FRANCOIS_C4969`) : `prov_url` reste vide, sauf pour
une commission dont le dump donne la page (`com.orgurlsim`, relative à `www.senat.fr`).
"""
from __future__ import annotations

import io
import re

import pyarrow as pa

NOM = "senat_export"
VERSION = 1
TYPES = ("export_sens",)

LUES = frozenset({"sen", "elusen", "dpt", "etadebman", "etafinman", "memgrppol", "typapppol",
                  "fonmemgrppol", "fongrppol", "grppol", "libgrppol", "memcom", "fonmemcom",
                  "foncom", "com", "libcom", "senbur", "bur"})
# Tables qui ne doivent jamais être lues (règle 3) : contrôle de sûreté de la liste blanche.
JAMAIS = frozenset({"activite", "activite_participant", "activite_senateur",
                    "activite_delegation", "activite_loi", "activites_liees",
                    "fonact_participant", "type_activite", "type_activite_participant",
                    "type_activite_senateur", "adresse", "telephone", "mel", "senurl"})
assert not (LUES & JAMAIS)

S = pa.string()
TABLES = {
    "identite_source": pa.schema([
        ("uid", S), ("matricule", S), ("civilite", S), ("prenom", S), ("nom", S),
        ("nom_majuscules", S), ("nom_technique", S), ("feminin", pa.bool_()),
        ("date_naissance", S), ("date_deces", S), ("etat", S), ("profession", S),
        ("categorie_socio_pro", S), ("categorie_pro", S), ("uri_hatvp", S),
    ]),
    "mandat": pa.schema([
        ("uid", S), ("acteur", S), ("nature", S), ("type_mandat", S), ("type_organe", S),
        ("organe", S), ("appartenance", S), ("qualite_code", S), ("qualite", S),
        ("date_debut", S), ("date_fin", S), ("date_election", S),
        ("cause_debut_code", S), ("cause_debut", S), ("cause_fin_code", S), ("cause_fin", S),
        ("circonscription_code", S), ("circonscription", S), ("tour", S),
        ("libelle_organe", S), ("libelle_organe_court", S), ("date_libelle", S),
        ("etat", S), ("evenement", S), ("observation", S), ("rang", S),
    ]),
    "organe": pa.schema([
        ("uid", S), ("code", S), ("type_organe", S), ("libelle", S), ("libelle_abrege", S),
        ("libelle_long", S), ("sigle", S), ("date_debut", S), ("date_fin", S), ("etat", S),
        ("site_internet", S), ("page_senat", S),
    ]),
    "organe_libelle": pa.schema([
        ("uid", S), ("organe", S), ("date_debut", S), ("date_fin", S), ("libelle", S),
        ("libelle_abrege", S), ("libelle_long", S), ("sigle", S), ("etat", S),
    ]),
}

_COPY = re.compile(rb"^COPY ([a-z_0-9]+) \((.*)\) FROM stdin;$")
_ECHAP = re.compile(r"\\(?:([0-7]{1,3})|x([0-9a-fA-F]{1,2})|(.))")
_SIMPLES = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}


def _desechapper(s: str) -> str:
    if "\\" not in s:
        return s
    def rempl(m):
        """Rend le caractère d'une séquence d'échappement trouvée par `_ECHAP` : octal,
        hexadécimal, lettre de `_SIMPLES`, ou le caractère échappé lui-même."""
        if m.group(1):
            return chr(int(m.group(1), 8))
        if m.group(2):
            return chr(int(m.group(2), 16))
        c = m.group(3)
        return _SIMPLES.get(c, c)
    return _ECHAP.sub(rempl, s)


def tables_du_dump(octets: bytes, voulues=LUES) -> dict[str, list[dict]]:
    """Lit les blocs `COPY` des seules tables voulues ; les autres sont sautées sans décodage."""
    out: dict[str, list[dict]] = {}
    courant, cols = None, None
    sauter = False
    for ligne in io.BytesIO(octets):
        ligne = ligne.rstrip(b"\n")
        if courant is not None or sauter:
            if ligne == b"\\.":
                courant, cols, sauter = None, None, False
                continue
            if sauter:
                continue
            champs = ligne.decode("utf-8").split("\t")
            if len(champs) != len(cols):
                raise ValueError(f"{courant} : {len(champs)} champs pour {len(cols)} colonnes")
            out[courant].append({c: (None if v == "\\N" else _desechapper(v))
                                 for c, v in zip(cols, champs)})
            continue
        if ligne.startswith(b"COPY "):
            m = _COPY.match(ligne)
            if not m:
                raise ValueError(f"ligne COPY illisible : {ligne[:80]!r}")
            nom = m.group(1).decode()
            if nom in voulues:
                courant = nom
                cols = [c.strip() for c in m.group(2).decode().split(",")]
                out.setdefault(nom, [])
            else:
                sauter = True
    if courant is not None or sauter:
        raise ValueError("dump tronqué : bloc COPY sans fin")
    return out


def _v(x):
    """Libellé resserré ; vide ou espaces seuls -> None."""
    if x is None:
        return None
    x = " ".join(x.split())
    return x or None


def _d(x):
    """Horodatage `AAAA-MM-JJ hh:mm:ss` -> `AAAA-MM-JJ`."""
    x = _v(x)
    return x[:10] if x else None


def _sen(m):
    return f"senat:{m.strip()}" if m and m.strip() else None


def _libelle_a_la_date(histo: list[dict], date: str | None, deb, fin):
    """Ligne d'historique en vigueur à `date` (début inclus, fin exclue ; fin vide = en cours)."""
    if not date:
        return None
    for h in histo:
        d0, d1 = _d(h[deb]), _d(h[fin])
        if d0 and d0 <= date and (d1 is None or date < d1):
            return h
    return None


def _par(rows, cle):
    out = {}
    for r in rows:
        out[r[cle]] = r
    return out


def lire(m):
    """Lit le dump du Sénat (`m`, un `MembreLu`) et rend
    `{"identite_source", "mandat", "organe", "organe_libelle"}` (listes de lignes). Un membre qui
    n'est pas un fichier `.sql` rend `{}` ; un dump sans la table `sen` lève `ValueError`.

    `mandat` réunit les mandats de sénateur (`elusen`), les appartenances aux groupes et aux
    commissions (avec le libellé de l'organe à la date), les fonctions dans ces groupes et
    commissions, et les fonctions au bureau (`senbur`). `organe` et `organe_libelle` viennent des
    groupes, des commissions et de l'historique de leurs libellés."""
    if not m.chemin.lower().endswith(".sql"):
        return {}
    t = tables_du_dump(m.octets)
    if "sen" not in t:
        raise ValueError("table `sen` absente du dump")
    g = lambda nom: t.get(nom, [])
    dpt = _par(g("dpt"), "dptnum")
    etadeb = _par(g("etadebman"), "etadebmancod")
    etafin = _par(g("etafinman"), "etafinmancod")
    typapp = _par(g("typapppol"), "typapppolcod")
    fongrp = _par(g("fongrppol"), "fongrppolcod")
    foncom = _par(g("foncom"), "foncomcod")
    bur = _par(g("bur"), "burcod")
    grppol = _par(g("grppol"), "grppolcod")
    com = _par(g("com"), "orgcod")
    hist_grp, hist_com = {}, {}
    for h in g("libgrppol"):
        hist_grp.setdefault(h["grppolcod"], []).append(h)
    for h in g("libcom"):
        hist_com.setdefault(h["orgcod"], []).append(h)

    identites = []
    for s in g("sen"):
        fem = _v(s["senfem"])
        identites.append({
            "uid": _sen(s["senmat"]), "matricule": _v(s["senmat"]), "civilite": _v(s["quacod"]),
            "prenom": _v(s["senprenomuse"]), "nom": _v(s["sennomuse"]),
            "nom_majuscules": _v(s["sennomusecap"]), "nom_technique": _v(s["sennomtec"]),
            "feminin": {"OUI": True, "NON": False}.get(fem),
            "date_naissance": _d(s["sendatnai"]), "date_deces": _d(s["sendatdec"]),
            "etat": _v(s["etasencod"]), "profession": _v(s["sendespro"]),
            "categorie_socio_pro": _v(s["pcscod"]), "categorie_pro": _v(s["catprocod"]),
            "uri_hatvp": _v(s["sendaiurl"]),
        })

    vide = {k: None for k in TABLES["mandat"].names}
    mandats = []
    for e in g("elusen"):
        c = dpt.get(e["dptnum"]) or {}
        deb, fin = etadeb.get(e["etadebmancod"]) or {}, etafin.get(e["etafinmancod"]) or {}
        mandats.append({**vide,
            "uid": f"senat:elusen:{e['eluid']}", "acteur": _sen(e["senmat"]), "nature": "mandat",
            "type_mandat": _v(e["typmancod"]), "date_debut": _d(e["eludatdeb"]),
            "date_fin": _d(e["eludatfin"]), "date_election": _d(e["eludatelu"]),
            "cause_debut_code": _v(e["etadebmancod"]), "cause_debut": _v(deb.get("etadebmanlib")),
            "cause_fin_code": _v(e["etafinmancod"]), "cause_fin": _v(fin.get("etafinmanlil")),
            "circonscription_code": _v(e["dptnum"]), "circonscription": _v(c.get("dptlib")),
            "tour": _v(e["turelucod"]), "etat": _v(e["temvalcod"]),
            "evenement": _v(e["evelil"]) or _v(e["evelib"]),
        })

    def appartenance(r, uid, code, organe, type_organe, histo, cle_deb, cle_fin,
                     col_deb, col_fin, qualite_code, qualite, libs):
        """Rend la ligne `mandat` d'une appartenance à un organe, lue dans la ligne `r` du dump :
        dates (colonnes `col_deb`, `col_fin`), qualité, état, événement, et le libellé de l'organe
        (colonnes `libs`) pris dans l'historique `histo` à la date de début, à défaut à la date de
        fin. L'argument `code` n'est pas utilisé."""
        d0, d1 = _d(r[col_deb]), _d(r[col_fin])
        date_ref = d0 or d1
        h = _libelle_a_la_date(histo, date_ref, cle_deb, cle_fin)
        return {**vide,
            "uid": uid, "acteur": _sen(r["senmat"]), "nature": "appartenance",
            "type_organe": type_organe, "organe": organe,
            "qualite_code": qualite_code, "qualite": qualite, "date_debut": d0, "date_fin": d1,
            "libelle_organe": _v(h[libs[0]]) if h else None,
            "libelle_organe_court": _v(h[libs[1]]) if h else None,
            "date_libelle": date_ref if h else None,
            "etat": _v(r["temvalcod"]), "evenement": _v(r["evelil"]) or _v(r["evelib"]),
            "observation": _v(r.get("eveobs")),
        }

    memgrp = {}
    for r in g("memgrppol"):
        code = _v(r["grppolcod"])
        o = grppol.get(r["grppolcod"]) or {}
        tp = typapp.get(r["typapppolcod"]) or {}
        x = appartenance(r, f"senat:memgrppol:{r['memgrppolid']}", code, f"senat:grppol:{code}",
                         _v(o.get("typorgcod")) or "GRPPOL", hist_grp.get(r["grppolcod"], []),
                         "libgrppoldatdeb", "libgrppoldatfin", "memgrppoldatdeb",
                         "memgrppoldatfin", _v(r["typapppolcod"]), _v(tp.get("typapppollib")),
                         ("evelib", "evelic"))
        memgrp[r["memgrppolid"]] = x
        mandats.append(x)
    memc = {}
    for r in g("memcom"):
        code = _v(r["orgcod"])
        o = com.get(r["orgcod"]) or {}
        x = appartenance(r, f"senat:memcom:{r['memcomid']}", code, f"senat:com:{code}",
                         _v(o.get("typorgcod")), hist_com.get(r["orgcod"], []),
                         "libcomdatdeb", "libcomdatfin", "memcomdatdeb", "memcomdatfin",
                         _v(r["memcomtitsup"]), _v(r["memcomtitsup"]), ("evelib", "evelic"))
        memc[r["memcomid"]] = x
        mandats.append(x)

    def fonction(r, uid, parent, code, libelle, col_deb, col_fin, rang=None):
        """Rend la ligne `mandat` d'une fonction tenue dans un organe, lue dans la ligne `r` du
        dump : l'acteur, l'organe et l'appartenance viennent de la ligne `parent` (vides si elle
        manque), les dates des colonnes `col_deb` et `col_fin`."""
        # Une fonction dont l'appartenance mère manque au dump garde acteur et organe vides.
        parent = parent or {"acteur": None, "type_organe": None, "organe": None, "uid": None}
        return {**vide,
            "uid": uid, "acteur": parent["acteur"], "nature": "fonction",
            "type_organe": parent["type_organe"], "organe": parent["organe"],
            "appartenance": parent["uid"], "qualite_code": code, "qualite": libelle,
            "date_debut": _d(r[col_deb]), "date_fin": _d(r[col_fin]),
            "etat": _v(r["temvalcod"]), "evenement": _v(r["evelil"]) or _v(r["evelib"]),
            "observation": _v(r.get("eveobs")), "rang": rang,
        }

    for r in g("fonmemgrppol"):
        f = fongrp.get(r["fongrppolcod"]) or {}
        mandats.append(fonction(r, f"senat:fonmemgrppol:{r['fonmemgrppolid']}",
                                memgrp.get(r["memgrppolid"]), _v(r["fongrppolcod"]),
                                _v(f.get("fongrppollic")), "fonmemgrppoldatdeb",
                                "fonmemgrppoldatfin"))
    for r in g("fonmemcom"):
        f = foncom.get(r["foncomcod"]) or {}
        mandats.append(fonction(r, f"senat:fonmemcom:{r['fonmemcomid']}",
                                memc.get(r["memcomid"]), _v(r["foncomcod"]),
                                _v(f.get("foncomlic")), "fonmemcomdatdeb", "fonmemcomdatfin",
                                _v(r["fonmemcomrngprt"])))
    for r in g("senbur"):
        b = bur.get(r["burcod"]) or {}
        mandats.append({**vide,
            "uid": f"senat:senbur:{r['senburid']}", "acteur": _sen(r["senmat"]),
            "nature": "fonction", "type_organe": "BUREAU", "qualite_code": _v(r["burcod"]),
            "qualite": _v(b.get("burlic")), "date_debut": _d(r["senburdatdeb"]),
            "date_fin": _d(r["senburdatfin"]), "etat": _v(r["temvalcod"]),
            "evenement": _v(r["evelil"]) or _v(r["evelib"]), "observation": _v(r["eveobs"]),
            "rang": _v(r["senburrngele"]),
        })

    organes, libelles = [], []
    for o in g("grppol"):
        organes.append({
            "uid": f"senat:grppol:{_v(o['grppolcod'])}", "code": _v(o["grppolcod"]),
            "type_organe": _v(o["typorgcod"]), "libelle": _v(o["grppollibcou"]),
            "libelle_abrege": _v(o["grppolliccou"]), "libelle_long": _v(o["grppollilcou"]),
            "sigle": _v(o["grppolcodamelicou"]), "date_debut": _d(o["grppoldatcre"]),
            "date_fin": _d(o["grppoldatfin"]), "etat": _v(o["temvalcod"]),
            "site_internet": _v(o["grppolurlcmp"]), "page_senat": _v(o["grppolurlsim"]),
        })
    for o in g("com"):
        page = _v(o["orgurlsim"])
        organes.append({
            "uid": f"senat:com:{_v(o['orgcod'])}", "code": _v(o["orgcod"]),
            "type_organe": _v(o["typorgcod"]), "libelle": _v(o["evelib"]),
            "libelle_abrege": _v(o["evelic"]), "libelle_long": _v(o["evelil"]),
            "sigle": _v(o["comcodameli"]), "date_debut": _d(o["orgdatcre"]),
            "date_fin": _d(o["orgdatfin"]), "etat": _v(o["temvalcod"]),
            "site_internet": _v(o["orgurlcmp"]), "page_senat": page,
            "prov_url": ("https://www.senat.fr" + page) if page and page.startswith("/") else None,
        })
    for h in g("libgrppol"):
        libelles.append({
            "uid": f"senat:libgrppol:{h['libgrppolid']}",
            "organe": f"senat:grppol:{_v(h['grppolcod'])}",
            "date_debut": _d(h["libgrppoldatdeb"]), "date_fin": _d(h["libgrppoldatfin"]),
            "libelle": _v(h["evelib"]), "libelle_abrege": _v(h["evelic"]),
            "libelle_long": _v(h["evelil"]), "sigle": _v(h["libgrppolcodameli"]),
            "etat": _v(h["temvalcod"]),
        })
    for h in g("libcom"):
        libelles.append({
            "uid": f"senat:libcom:{h['libcomid']}", "organe": f"senat:com:{_v(h['orgcod'])}",
            "date_debut": _d(h["libcomdatdeb"]), "date_fin": _d(h["libcomdatfin"]),
            "libelle": _v(h["evelib"]), "libelle_abrege": _v(h["evelic"]),
            "libelle_long": _v(h["evelil"]), "sigle": _v(h["libcomlibameli"]),
            "etat": _v(h["temvalcod"]),
        })
    return {"identite_source": identites, "mandat": mandats, "organe": organes,
            "organe_libelle": libelles}


EXPORT = {
    "identite_source": {"type": "identite_source", "cle": ["uid"], "ids": {"acteur": "uid"},
                        "date": None},
    "mandat": {"type": "mandat", "cle": ["uid"],
               "ids": {"mandat": "uid", "acteur": "acteur", "organe": "organe"},
               "date": "date_debut"},
    "organe": {"type": "organe", "cle": ["uid"], "ids": {"organe": "uid"}, "date": "date_debut"},
    "organe_libelle": {"type": "organe_libelle", "cle": ["uid"],
                       "ids": {"organe": "organe", "autre": "uid"}, "date": "date_debut"},
}
