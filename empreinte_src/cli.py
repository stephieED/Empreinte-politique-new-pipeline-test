"""Ligne de commande. Chaque sous-commande correspond à une tâche du workflow (doc. 2, 2.15)."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time

import yaml

from .entrepot import Entrepot, maintenant
from .mesures import Mesures


def _config(chemin):
    with open(chemin) as f:
        return yaml.safe_load(f)


def _version_code():
    try:
        return subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return os.environ.get("GITHUB_SHA", "inconnue")[:12]


def _panne_depuis(entrepot: Entrepot, point: str) -> str | None:
    """Date du premier échec depuis le dernier relevé réussi (pour une alerte stable)."""
    depuis = None
    for r in entrepot._releves:
        if r["point_acces"] != point:
            continue
        if r["issue"] in ("nouveau", "inchange"):
            depuis = None
        elif depuis is None:
            depuis = r["debut"]
    return depuis


def _dernier_reussi(entrepot: Entrepot, point: str) -> str | None:
    """Date du dernier relevé complet réussi d'un point, ou None s'il n'y en a jamais eu (#33)."""
    r = entrepot.dernier_releve(point, complet_seulement=True)
    return r["debut"] if r else None


def cmd_preparer(a):
    cfg = _config(a.config)
    ids = {p["id"] for p in cfg["points_acces"]}
    inconnus = [p for p in (a.points or []) if p not in ids]
    if inconnus:
        sys.exit(f"Points d'accès inconnus : {', '.join(inconnus)}. Connus : {', '.join(sorted(ids))}")
    if a.mode not in ("quotidien", "complet", "essai"):
        sys.exit(f"Mode inconnu : {a.mode}")
    print(json.dumps({"mode": a.mode, "points": a.points or sorted(ids)}, ensure_ascii=False))


def cmd_collecter(a):
    from .collecte import collecter
    from .transport import Transport
    cfg = _config(a.config)
    params = cfg.get("parametres", {})
    mesures = Mesures()
    debut = maintenant()
    e = Entrepot(a.entrepot, segment_max=params.get("segment_max_octets", 90 << 20),
                 morceau_max=params.get("morceau_blob_octets", 64 << 20))
    t = Transport(params["user_agent"], dossier_tmp=a.tmp,
                  budget_s=params.get("budget_telechargement_s", 1800),
                  # Budget propre à un point (archives closes trop grosses pour 30 min, #32), seulement
                  # dans un relevé qui le nomme (`--points`) : la nuit garde 30 min par fichier et ne
                  # peut pas passer des heures sur une archive close (décision du 13/11/2026).
                  budgets_par_url={p["url"]: p["budget_s"] for p in cfg["points_acces"]
                                   if p.get("budget_s") and p.get("url") and p["id"] in (a.points or [])},
                  # Échéance de toute la collecte, avant la limite de la tâche (330 min) : la collecte
                  # se termine et l'acquis est déposé, au lieu d'être perdu (#38).
                  fin_collecte=time.monotonic() + params.get("duree_collecte_max_s", 270 * 60))
    if a.mode == "complet":
        for r in e._releves:            # relecture forcée : on oublie les ETag
            r["etag"] = r["last_modified"] = None
    releves = collecter(e, t, cfg, mesures, points=a.points)
    with mesures.etape("clore"):
        man = e.clore(_version_code())
    for r in releves:
        if r["issue"] in ("echec", "suspect"):
            r["panne_depuis"] = _panne_depuis(e, r["point_acces"])
            r["dernier_releve_reussi"] = _dernier_reussi(e, r["point_acces"])
    rapport = {"generation": man["generation"], "base": man["base"], "mode": a.mode,
               "debut": debut, "fin": maintenant(), "code": man["code"],
               "releves": releves, "mesures": mesures.etapes,
               **({"rattrapage_erreur": a.rattrapage_erreur} if getattr(a, "rattrapage_erreur", None) else {}),
               "entrepot_octets": sum(f["taille"] for f in man["fichiers"].values()),
               "entrepot_fichiers": len(man["fichiers"])}
    with open(a.rapport, "w") as f:
        json.dump(rapport, f, indent=1, ensure_ascii=False, default=str)
    _resume(rapport, mesures.pic())


def cmd_calculer(a):
    """E3 (lire) puis export plat. Les étapes E4 à E6 arrivent avec la tranche 3."""
    from .export import exporter
    from .lecture import Lecture, lecteurs
    cfg = _config(a.config)
    mesures = Mesures()
    with open(a.rapport) as f:
        rapport = json.load(f)
    e = Entrepot(a.entrepot)
    l = Lecture(e, a.z2, cfg)
    for mod in lecteurs():
        with mesures.etape("E3", lecteur=mod.NOM) as m:
            b = l.executer(mod)
            m.update(lues=b["lues"], illisibles=b["illisibles"])
    with mesures.etape("export") as m:
        ex = exporter(a.z2, lecteurs(), os.path.join(a.sortie, "export"))
        m.update(faits=ex.get("total"))
    gen = e.generation_base
    # E4 relier, E5 composer, E6 contrôler.
    from .composition import Ecrivain, composeurs
    from .controles import Controles
    from .liaison import Contexte, relier
    import shutil
    from .identites import RegistreIdentites
    registre = RegistreIdentites(a.entrepot)
    ligne_avant = len(registre.attributions)
    ctx = Contexte(a.z2, a.z3, dossier_decisions=a.decisions, generation=gen,
                   date_reference=(rapport.get("debut") or "")[:10] or None, registre=registre)
    with mesures.etape("E4") as m:
        bilan_regles = relier(ctx)
        m["regles"] = len(bilan_regles)
    # Le registre enrichi part avec la candidate ; la tâche `ecrire` le dépose dans l'entrepôt.
    import shutil as _sh
    registre.dossier_sortie = os.path.join(a.sortie, "registres")
    os.makedirs(registre.dossier_sortie, exist_ok=True)
    registre.sauver()
    for n in os.listdir(registre.dossier):
        _sh.copy2(os.path.join(registre.dossier, n), os.path.join(registre.dossier_sortie, n))
    nouvelles_attributions = len(registre.attributions) - ligne_avant
    site = os.path.join(a.sortie, "site")
    shutil.rmtree(site, ignore_errors=True)
    pannes = {r["point_acces"]: r.get("panne_depuis") or r.get("debut")
              for r in rapport.get("releves", []) if r.get("issue") in ("echec", "suspect")}
    # Faits publiés écrits au fil de l'eau (mémoire : ≈ 2 millions sur le périmètre complet).
    ecr = Ecrivain(site, f"g{gen:06d}", pannes=pannes,
                   releves_reussis={p: _dernier_reussi(e, p) for p in pannes},
                   chemin_faits=os.path.join(a.sortie, "export", "faits-publies.parquet"))
    with mesures.etape("E5") as m:
        for c in composeurs():
            c.composer(ctx, ecr)
        manifeste_site = ecr.clore()
        nb_publies = ecr.ecrire_faits_publies()      # les contrôles relisent le fichier
        m.update(fiches=len(manifeste_site["fiches"]), faits_publies=nb_publies)
    from importlib.resources import files
    shutil.copy(str(files("empreinte_src").joinpath("site/index.html")), os.path.join(site, "index.html"))
    with open(os.path.join(site, "publication.json"), "w") as f:
        json.dump({"id": f"g{gen:06d}"}, f)
    with mesures.etape("E6"):
        ctrl = Controles(ecr.racine, levees=ctx.decisions.get("levee_controle", []))
        ctrl.c2_liens({f["fiche"] for f in manifeste_site["fiches"]})
        ctrl.c4_interdits()
        # Forme des fichiers servis contre le schéma commité (#43) ; à côté de la configuration.
        ctrl.c4_forme(os.path.join(os.path.dirname(a.config) or ".", "schema_fichiers.yaml"))
        ctrl.c5_couverture(rapport.get("releves", []))
        # Un fichier modifié cette nuit explique la perte de ses faits, sauf si le lecteur n'a pas
        # pu le lire : la perte vient alors de nous, pas de la source, et C1 doit la voir (#39).
        uids_illisibles = {u.split("@")[0] for _, u, _ in l.illisibles}
        # « Cette nuit » = depuis la génération de la dernière publication, pas seulement la courante :
        # après une nuit écrite mais non publiée (13/11/2026, refusée par C4), la mise à jour suivante
        # se compare à la publication d'avant, et les fichiers changés la nuit refusée doivent encore
        # expliquer leurs pertes (9 points de l'ordre du jour faussement perdus, essai 43521640358).
        m_pub = re.search(r"faits-publies-g(\d+)\.parquet$", a.faits_precedents or "")
        depuis = int(m_pub.group(1)) if m_pub else gen - 1
        changes = {r["uid"].split("@")[0] for r in e._index
                   if r["vu_du"] is not None and r["vu_du"] > depuis} - uids_illisibles
        retirees = dict(ctx.x("""SELECT 'candidat/' || adresse, raison_non_publie FROM candidat
                                 WHERE NOT publie AND adresse IS NOT NULL
                                   AND statut IN ('retiree', 'non_listee')""")) if ctx.existe("candidat") else {}
        ctrl.c1_c6_comparer(a.faits_precedents or None, os.path.join(a.sortie, "export", "faits-publies.parquet"),
                            uids_changes_a_la_source=changes, fiches_retirees=retirees)
        ctrl.a9_valeurs_videes(a.faits_precedents or None,
                               os.path.join(a.sortie, "export", "faits-publies.parquet"))
        # C3, C7 et avertissements : tables des règles et faits publiés de la candidate.
        ctrl.preparer(ctx.con, os.path.join(a.sortie, "export", "faits-publies.parquet"),
                      {f["fiche"] for f in manifeste_site["fiches"]}, manifeste_site["fiches"])
        ctrl.c3_laisses_de_cote()
        ctrl.c7_personnes()
        ctrl.a1_hors_modele(ctx.decisions.get("fiche_hors_modele", []))
        nb_a2 = int(cfg.get("parametres", {}).get("verification_croisee", 20) or 0)
        if nb_a2:
            from .verification import recuperateur
            import time as _t
            t0 = _t.monotonic()
            ctrl.a2_verification_croisee(gen, recuperateur(cfg["parametres"]["user_agent"]), nb_a2)
            if getattr(ctrl, "bilan_a2", None):
                ctrl.bilan_a2["duree_s"] = round(_t.monotonic() - t0, 1)
        ctrl.a3_totaux()
        ctrl.a4_double_affichage()
        ctrl.a5_famille_a_zero()
        ctrl.a6_couverture()
        ctrl.a8_mandats_ouverts()
        ctrl.a9_liste_des_candidats()
        ctrl.a7_non_resolues(ctx.decisions)          # en dernier : il vérifie les levées sans objet
    controles = ctrl.bilan()
    rapport["calcul"] = {"lecture": l.bilan, "export": ex, "mesures": mesures.etapes,
                         "generation": gen, "regles": bilan_regles,
                         "registre": {"attributions": len(registre.attributions),
                                      "nouvelles": nouvelles_attributions},
                         "publication": {"id": f"g{gen:06d}", "fiches": manifeste_site["fiches"],
                                         "faits_publies": nb_publies},
                         "controles": controles}
    for an in controles["anomalies"]:
        if an["bloquant"]:
            anomalies_txt = "\n".join(f"- {x}" for x in an["exemples"])
            rapport.setdefault("anomalies", []).append({
                "cle": f"controle:{an['controle']}",
                "texte": (f"**Publication refusée** : {an['titre']} ({an['nb_objets']} objets).\n\n"
                          f"{anomalies_txt}\n\nPour l'autoriser quand même, une décision "
                          f"`decisions/levee_controle/<nom>.yaml` avec `type: levee_controle`, "
                          f"`empreinte: {an['empreinte']}` et un `motif`.")})
    # Avertissements : publication maintenue, une issue par avertissement (décomptes et
    # identifiants seulement).
    par_code: dict[str, list] = {}
    for an in controles["anomalies"]:
        if an["controle"].startswith("A"):
            par_code.setdefault(an["controle"], []).append(an)
    for code, ans in sorted(par_code.items()):
        blocs = []
        for an in ans:
            # `exemples`, pas `ex` : `ex` est le bilan de l'export, relu plus bas.
            exemples = "\n".join(f"- {x}" for x in an["exemples"])
            suite = f"\n- … ({an['nb_objets'] - len(an['exemples'])} autres)" if an["nb_objets"] > len(an["exemples"]) else ""
            blocs.append(f"**{an['titre']}** ({an['nb_objets']}).\n\n{exemples}{suite}")
        rapport.setdefault("anomalies", []).append({
            "cle": f"avertissement:{code}",
            "texte": "Avertissement (la publication n'est pas bloquée).\n\n" + "\n\n".join(blocs)})
    anomalies = rapport.setdefault("anomalies", [])
    illisibles = [b for b in l.bilan if b["illisibles"]]
    if illisibles:
        anomalies.append({"cle": "lecture:illisibles", "texte": "Membres illisibles à la lecture :\n\n"
                          + "\n".join(f"- `{b['lecteur']}` : {b['illisibles']} ({'; '.join(b['exemples_illisibles'][:2])})"
                                      for b in illisibles)})
    if ex.get("cles_en_double"):
        anomalies.append({"cle": "export:doublons",
                          "texte": f"{ex['cles_en_double']} clés de fait en double dans l'export."})
    with open(a.rapport, "w") as f:
        json.dump(rapport, f, indent=1, ensure_ascii=False, default=str)
    lignes = ["", "## Lecture et export", "", "| Lecteur | Versions | Lues | Illisibles |",
              "| --- | ---: | ---: | ---: |"]
    lignes += [f"| {b['lecteur']} | {b['versions']:,} | {b['lues']:,} | {b['illisibles']:,} |"
               for b in l.bilan]
    lignes += ["", f"Export : {ex.get('total', 0):,} faits, {ex.get('cles_en_double', 0)} clés en double.",
               f"Fiches : {len(manifeste_site['fiches'])} ; faits publiés : {nb_publies:,}.",
               "Contrôles : " + ("publication autorisée" if controles["publication_autorisee"]
                                  else "**publication refusée** (" + ", ".join(controles["bloquantes"]) + ")"),
               mesures.pic()]
    texte = "\n".join(lignes)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(texte + "\n")


def cmd_superposer(a):
    """Rattrapage : superpose l'acquis d'une nuit non écrite à la copie de travail."""
    import shutil
    src = a.depuis
    for racine, _, noms in os.walk(src):
        for n in noms:
            rel = os.path.relpath(os.path.join(racine, n), src)
            cible = os.path.join(a.entrepot, rel)
            os.makedirs(os.path.dirname(cible), exist_ok=True)
            shutil.copy2(os.path.join(racine, n), cible)
    os.makedirs(os.path.join(a.entrepot, "rattrapage"), exist_ok=True)
    shutil.copy2(os.path.join(src, "manifeste.json"),
                 os.path.join(a.entrepot, "rattrapage", "manifeste.json"))
    with open(os.path.join(src, "manifeste.json")) as f:
        print(f"nuit rattrapée : génération {json.load(f)['generation']}")


def cmd_restaurer(a):
    from .distant import restaurer
    man = restaurer(a.depot, a.entrepot, avec_blobs=a.avec_blobs, avec_membres=a.avec_membres)
    print(f"génération restaurée : {man['generation'] if man else 0}")


def cmd_ecrire(a):
    from .distant import publier
    with open(a.rapport) as f:
        rapport = json.load(f)
    # Registre des identités enrichi par le calcul (acquis, P1) : vérifié en ajout seul, puis
    # recopié dans l'entrepôt avant l'écriture.
    registres = os.path.join(os.path.dirname(a.rapport), "registres")
    if os.path.isdir(registres):
        import shutil
        import pyarrow.parquet as pq
        from .identites import verifier_ajout_seul, RegistreModifie
        # Registres en ajout seul : personnes, lignées de groupe et adresses des lignées.
        en_ajout_seul = (("attribution.parquet", ("per", "source", "uid", "depuis")),
                         ("lignee_attribution.parquet", ("per", "source", "uid", "depuis")),
                         ("lignee_adresse.parquet", ("adresse", "per", "depuis")))
        try:
            for nom, cles in en_ajout_seul:
                ancien_p = os.path.join(a.entrepot, "registres", nom)
                nouveau_p = os.path.join(registres, nom)
                if os.path.exists(ancien_p):
                    if not os.path.exists(nouveau_p):
                        raise RegistreModifie(f"{nom} absent de la candidate")
                    verifier_ajout_seul(pq.read_table(ancien_p).to_pylist(),
                                        pq.read_table(nouveau_p).to_pylist(), cles)
            os.makedirs(os.path.join(a.entrepot, "registres"), exist_ok=True)
            for n in os.listdir(registres):
                shutil.copy2(os.path.join(registres, n), os.path.join(a.entrepot, "registres", n))
            Entrepot(a.entrepot).actualiser_fichiers([f"registres/{n}" for n in sorted(os.listdir(registres))])
        except RegistreModifie as e:
            rapport.setdefault("anomalies", []).append(
                {"cle": "registre", "texte": f"Registre des identités modifié, non écrit : {e}"})
    try:
        res = publier(a.depot, a.entrepot)
        rapport["ecriture"] = res
        sortie = os.path.dirname(a.rapport)
        export = os.path.join(sortie, "export")
        calcul = rapport.get("calcul") or {}
        autorisee = (calcul.get("controles") or {}).get("publication_autorisee")
        if autorisee and os.path.exists(os.path.join(export, "faits.parquet")):
            from .distant import publier_export, publier_site
            rapport["ecriture_export"] = publier_export(a.depot, export, res["generation"])
            rapport["ecriture_site"] = publier_site(a.depot, os.path.join(sortie, "site"), res["generation"])
        else:
            rapport["publication_refusee"] = ("calcul absent ou échoué" if not calcul else
                                              "contrôles bloquants : " + ", ".join(calcul["controles"]["bloquantes"]))
    except Exception as e:
        rapport["echec_ecriture"] = str(e)
    with open(a.rapport, "w") as f:
        json.dump(rapport, f, indent=1, ensure_ascii=False, default=str)
    if "echec_ecriture" in rapport:
        sys.exit(f"Écriture refusée : {rapport['echec_ecriture']}")
    env = rapport["ecriture"]["envois"]
    print(f"génération {rapport['ecriture']['generation']} écrite : {len(env)} actifs, "
          f"{sum(x['octets'] for x in env) / 1e6:.1f} Mo")


def cmd_schema(a):
    """Réécrit les colonnes du schéma d'après les fichiers servis d'un calcul (#43)."""
    from .schema import reecrire_colonnes
    site = a.site
    sous = os.path.join(site, "donnees")
    if os.path.isdir(sous):                       # <sortie>/site/donnees/<publication>/
        site = os.path.join(sous, sorted(os.listdir(sous))[-1])
    print(json.dumps(reecrire_colonnes(a.schema, site), ensure_ascii=False, indent=1))


def cmd_alerter(a):
    from .alertes import sujets_du_rapport, synchroniser
    if a.rapport and os.path.exists(a.rapport):
        with open(a.rapport) as f:
            rapport = json.load(f)
    else:
        rapport = {"anomalies": [{"cle": "execution", "texte":
                   "La mise à jour s'est arrêtée avant de produire son rapport. Voir l'exécution : "
                   + os.environ.get("URL_EXECUTION", "?")}]}
    print(json.dumps(synchroniser(a.depot, sujets_du_rapport(rapport)), ensure_ascii=False))


def cmd_reconstruire(a):
    """Démonstration de P2 : le contenu exact d'une archive reçue, membre par membre."""
    e = Entrepot(a.entrepot)
    import hashlib
    membres = e.membres_du_releve(a.releve)
    octets = e.lire_plusieurs(m["empreinte"] for m in membres)
    ok = sum(1 for m in membres if m["empreinte"] in octets
             and hashlib.sha256(octets[m["empreinte"]]).hexdigest() == m["empreinte"])
    print(f"{ok} membres sur {len(membres)} retrouvés à l'octet près")
    sys.exit(0 if ok == len(membres) else 1)


def _resume(rapport, pic=""):
    """Résumé lisible dans la page de l'exécution GitHub."""
    lignes = [f"## Mise à jour — génération {rapport['generation']}", "",
              "| Point d'accès | Issue | Octets reçus | Nouvelles versions | Retraits | Durée (s) | Message |",
              "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
    for r in rapport["releves"]:
        msg = (r.get("message") or "").splitlines()[0][:80] if r.get("message") else ""
        lignes.append(f"| {r['point_acces']} | {r['issue']} | {r.get('octets_recus') or 0:,} | "
                      f"{r.get('nb_nouvelles_versions') or 0:,} | {r.get('nb_retraits') or 0:,} | "
                      f"{r.get('duree_s') or ''} | {msg} |")
    lignes += ["", f"Entrepôt : {rapport['entrepot_fichiers']} fichiers, "
               f"{rapport['entrepot_octets'] / 1e6:.1f} Mo."] + ([pic] if pic else [])
    texte = "\n".join(lignes)
    print(texte)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(texte + "\n")


def cmd_rapport_mesures(a):
    """Rapport de mesures (commande, section 5) : relit le rapport de chaque nuit (artefact `rapport`)."""
    from . import rapport_mesures as rm
    nuits = rm.charger(a.cache) if a.hors_ligne else rm.recuperer(a.depot, a.cache)
    texte = rm.rendre(rm.mesurer_toutes(nuits), a.depot)
    with open(a.sortie, "w") as f:
        f.write(texte)
    print(f"{len(nuits)} nuits → {a.sortie}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="empreinte")
    sp = p.add_subparsers(dest="cmd", required=True)
    commun = argparse.ArgumentParser(add_help=False)
    commun.add_argument("--entrepot", default="entrepot")
    commun.add_argument("--config", default="config/points_acces.yaml")
    commun.add_argument("--rapport", default="sortie/rapport.json")
    commun.add_argument("--depot", default=os.environ.get("GITHUB_REPOSITORY"))

    s = sp.add_parser("preparer", parents=[commun]); s.set_defaults(f=cmd_preparer)
    s.add_argument("--mode", default="quotidien"); s.add_argument("--points", nargs="*")
    s = sp.add_parser("collecter", parents=[commun]); s.set_defaults(f=cmd_collecter)
    s.add_argument("--mode", default="quotidien"); s.add_argument("--points", nargs="*")
    s.add_argument("--tmp", default=None)
    s.add_argument("--rattrapage-erreur", default=None,
                   help="erreur de la recherche d'un acquis à rattraper (tâche preparer), mise au rapport")
    s = sp.add_parser("calculer", parents=[commun]); s.set_defaults(f=cmd_calculer)
    s.add_argument("--z2", default="z2"); s.add_argument("--sortie", default="sortie")
    s.add_argument("--z3", default="z3"); s.add_argument("--decisions", default="decisions")
    s.add_argument("--faits-precedents", default=None)
    s = sp.add_parser("superposer", parents=[commun]); s.set_defaults(f=cmd_superposer)
    s.add_argument("--depuis", required=True)
    s = sp.add_parser("restaurer", parents=[commun]); s.set_defaults(f=cmd_restaurer)
    s.add_argument("--avec-blobs", action="store_true"); s.add_argument("--avec-membres", action="store_true")
    s = sp.add_parser("ecrire", parents=[commun]); s.set_defaults(f=cmd_ecrire)
    s = sp.add_parser("schema", parents=[commun]); s.set_defaults(f=cmd_schema)
    s.add_argument("--site", required=True, help="dossier site d'un calcul (sortie/site)")
    s.add_argument("--schema", default="config/schema_fichiers.yaml")
    s = sp.add_parser("alerter", parents=[commun]); s.set_defaults(f=cmd_alerter)
    s = sp.add_parser("reconstruire", parents=[commun]); s.set_defaults(f=cmd_reconstruire)
    s.add_argument("--releve", required=True)
    s = sp.add_parser("rapport-mesures", parents=[commun]); s.set_defaults(f=cmd_rapport_mesures)
    s.add_argument("--cache", required=True, help="dossier où garder les rapports téléchargés")
    s.add_argument("--sortie", required=True, help="fichier Markdown à écrire")
    s.add_argument("--hors-ligne", action="store_true", help="ne relire que le cache")
    a = p.parse_args(argv)
    os.makedirs(os.path.dirname(a.rapport) or ".", exist_ok=True)
    a.f(a)


if __name__ == "__main__":
    main()
