"""Étapes E1 (relever) et E2 (dépaqueter et versionner), point d'accès par point d'accès.

Chaque point d'accès est isolé : son échec n'arrête pas les autres (doc. 2, 2.2).
"""
from __future__ import annotations

import os
import re
import traceback

from .depaquetage import depaqueter, depaqueter_tar_flux, verifier_archive
from .entrepot import Entrepot, maintenant
from .mesures import Mesures
from .transport import Transport


def releve_vide(entrepot: Entrepot, pa_cfg: dict, k: int = 0) -> dict:
    return {"releve_id": f"g{entrepot.generation:06d}-{pa_cfg['id']}-{k}",
            "point_acces": pa_cfg["id"], "source": pa_cfg["source"], "url": pa_cfg["url"],
            "debut": maintenant(), "issue": "echec", "complet": False, "suspect": False,
            "octets_recus": 0, "nb_membres": 0, "nb_nouvelles_versions": 0, "nb_inchanges": 0,
            "nb_retraits": 0, "nb_reapparitions": 0, "nb_doublons": 0, "message": ""}


def relever_archive(entrepot: Entrepot, transport: Transport, pa_cfg: dict, params: dict,
                    k: int = 0, url: str | None = None, delta: bool = False,
                    conditionnel: bool = True) -> dict:
    """Relève une archive (zip, tar, réponse d'API) et la range dans l'entrepôt."""
    r = releve_vide(entrepot, pa_cfg, k)
    url = url or pa_cfg["url"]
    r["url"] = url
    precedent = entrepot.dernier_releve(pa_cfg["id"]) if conditionnel and not delta else None
    rep = transport.telecharger(url, etag=(precedent or {}).get("etag"),
                                last_modified=(precedent or {}).get("last_modified"))
    r.update(statut_http=rep.statut_http, octets_recus=rep.octets_recus,
             tentatives=rep.tentatives, reprises=rep.reprises, duree_s=round(rep.duree_s, 2),
             etag=rep.entetes.get("etag"), last_modified=rep.entetes.get("last-modified"),
             content_length=rep.entetes.get("content-length"),
             date_source=rep.entetes.get("last-modified"), message=rep.message)
    try:
        if rep.issue == "inchange":
            r["issue"] = "inchange"
            dernier_complet = entrepot.dernier_releve(pa_cfg["id"], complet_seulement=True)
            r["complet"] = bool(dernier_complet)
            r["etag"] = r["etag"] or (precedent or {}).get("etag")
            r["last_modified"] = r["last_modified"] or (precedent or {}).get("last_modified")
            r["date_source"] = r["last_modified"]
            if dernier_complet:
                entrepot.prolonger(pa_cfg["id"])
            return r
        if rep.issue != "nouveau":
            return r
        r["taille"], r["empreinte"] = rep.taille, rep.empreinte
        if pa_cfg.get("taille_min") and rep.taille < pa_cfg["taille_min"]:
            r["issue"], r["suspect"] = "suspect", True
            r["message"] = f"taille {rep.taille} octets sous le plancher {pa_cfg['taille_min']}"
            return r
        erreur = verifier_archive(rep.chemin, pa_cfg["format"])
        if erreur:
            r["message"] = erreur
            return r
        fmt = pa_cfg["format"]
        # Plausibilité : une chute du nombre de membres rend le relevé suspect.
        membres = list(depaqueter(rep.chemin, fmt, pa_cfg.get("uid"))) if fmt != "zip" else None
        nb = len(membres) if membres is not None else _compter_zip(rep.chemin)
        base = entrepot.dernier_releve(pa_cfg["id"], complet_seulement=True)
        seuil = params.get("baisse_suspecte", 0.05)
        if (not delta and base and base.get("nb_membres")
                and nb < base["nb_membres"] * (1 - seuil)):
            r.update(issue="suspect", suspect=True, nb_membres=nb,
                     message=f"{nb} membres contre {base['nb_membres']} au dernier relevé complet")
            return r
        it = membres if membres is not None else depaqueter(rep.chemin, fmt, pa_cfg.get("uid"))
        bilan = entrepot.versionner(pa_cfg, r["releve_id"], it, complet=True, delta=delta)
        r.update(issue="nouveau", complet=True, nb_membres=bilan.membres,
                 nb_nouvelles_versions=bilan.nouvelles, nb_inchanges=bilan.inchanges,
                 nb_retraits=bilan.retraits, nb_reapparitions=bilan.reapparitions,
                 nb_doublons=bilan.doublons, exemples=bilan.exemples)
        return r
    except Exception as e:  # un point d'accès qui casse n'arrête pas les autres
        r.update(issue="echec", complet=False,
                 message=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
        return r
    finally:
        r["fin"] = maintenant()
        if rep.chemin and os.path.exists(rep.chemin):
            os.unlink(rep.chemin)


def _compter_zip(chemin: str) -> int:
    import zipfile
    with zipfile.ZipFile(chemin) as z:
        return sum(1 for i in z.infolist() if not i.is_dir())


def relever_liste_tar(entrepot: Entrepot, transport: Transport, pa_cfg: dict, params: dict,
                      max_livraisons: int | None = None) -> list[dict]:
    """Journal officiel : toutes les livraisons parues depuis la dernière traitée."""
    curseur = None
    for rel in reversed(entrepot._releves):
        if rel["point_acces"] == pa_cfg["id"] and rel.get("curseur") and rel["issue"] == "nouveau":
            curseur = rel["curseur"]
            break
    curseur = curseur or pa_cfg.get("premiere_livraison", "")
    r0 = releve_vide(entrepot, pa_cfg)
    statut, texte, _ = transport.texte(pa_cfg["url"])
    if statut != 200:
        r0.update(message=f"liste : HTTP {statut}", fin=maintenant())
        return [r0]
    motif = re.compile(pa_cfg["motif"])
    noms = sorted({n for n in re.findall(r'href="([^"]+)"', texte) if motif.match(n)})
    a_faire = [n for n in noms if n > curseur]
    if max_livraisons:
        a_faire = a_faire[:max_livraisons]
    out = []
    for k, nom in enumerate(a_faire):
        r = relever_archive(entrepot, transport, pa_cfg, params, k=k,
                            url=pa_cfg["url"] + nom, delta=True, conditionnel=False)
        if r["issue"] == "nouveau":
            r["curseur"] = nom
        out.append(r)
        if r["issue"] != "nouveau":
            break        # on ne saute pas une livraison : la suivante attendra la prochaine nuit
    if not out:
        r0.update(issue="inchange", complet=True, message="aucune livraison nouvelle",
                  curseur=curseur, fin=maintenant())
        out.append(r0)
    return out


_DATE_PUBLI = re.compile(rb"<DATE_PUBLI>(\d{4}-\d\d-\d\d)</DATE_PUBLI>")
_DOSSIERS_JO = ("/texte/version/", "/texte/struct/", "/conteneur/")


def relever_archive_globale(entrepot: Entrepot, transport: Transport, pa_cfg: dict,
                            params: dict) -> dict:
    """Archive globale du Journal officiel (`Freemium_jorf_global_…tar.gz`), relevée **une fois** :
    la suite vient des livraisons quotidiennes. Décision du 13/11/2026 : l'archive reçue est
    gardée à l'octet (`Entrepot.ranger_brute`) ; ne sont découpés que les fichiers que lit le
    lecteur (métadonnées et plan des actes, sommaires des numéros) publiés depuis `depuis`. Chaque
    chemin reçoit l'horodatage de l'archive, comme ceux d'une livraison quotidienne : le lecteur y
    lit la livraison, et les uid sont ceux des livraisons."""
    r = releve_vide(entrepot, pa_cfg)
    deja = [x for x in entrepot._releves if x["point_acces"] == pa_cfg["id"] and x["issue"] == "nouveau"]
    if deja:
        entrepot.prolonger(pa_cfg["id"])
        r.update(issue="inchange", complet=True, curseur=deja[-1].get("curseur"), fin=maintenant(),
                 message=f"archive globale déjà reçue ({deja[-1].get('curseur')}) : la suite vient "
                         "des livraisons quotidiennes")
        return r
    statut, texte, _ = transport.texte(pa_cfg["url"])
    if statut != 200:
        r.update(message=f"liste : HTTP {statut}", fin=maintenant())
        return r
    motif = re.compile(pa_cfg["motif"])
    noms = sorted({n for n in re.findall(r'href="([^"]+)"', texte) if motif.match(n)})
    if not noms:
        r.update(message="aucune archive globale dans la liste", fin=maintenant())
        return r
    nom = noms[-1]
    url = pa_cfg["url"] + nom
    rep = transport.telecharger(url)
    r.update(url=url, statut_http=rep.statut_http, octets_recus=rep.octets_recus,
             tentatives=rep.tentatives, reprises=rep.reprises, duree_s=round(rep.duree_s, 2),
             etag=rep.entetes.get("etag"), last_modified=rep.entetes.get("last-modified"),
             content_length=rep.entetes.get("content-length"),
             date_source=rep.entetes.get("last-modified"), message=rep.message)
    try:
        if rep.issue != "nouveau":
            return r
        r["taille"], r["empreinte"] = rep.taille, rep.empreinte
        erreur = verifier_archive(rep.chemin, "tar_flux")
        if erreur:
            r["message"] = erreur
            return r
        horodatage = re.search(r"(\d{8}-\d{6})", nom).group(1)
        depuis = pa_cfg.get("depuis", "").encode()
        lus = {"vus": 0, "gardes": 0}

        def garder(chemin, octets):
            lus["vus"] += 1
            if not any(d in "/" + chemin for d in _DOSSIERS_JO):
                return False
            m = _DATE_PUBLI.search(octets)
            ok = bool(m) and m.group(1) >= depuis
            lus["gardes"] += ok
            return ok
        bilan = entrepot.versionner(pa_cfg, r["releve_id"],
                                    depaqueter_tar_flux(rep.chemin, garder, horodatage + "/"),
                                    complet=True, delta=True)
        r["archive_brute"] = entrepot.ranger_brute(nom, rep.chemin)
        r.update(issue="nouveau", complet=True, curseur=nom, nb_membres=bilan.membres,
                 nb_nouvelles_versions=bilan.nouvelles, nb_inchanges=bilan.inchanges,
                 nb_retraits=bilan.retraits, nb_reapparitions=bilan.reapparitions,
                 nb_doublons=bilan.doublons, exemples=bilan.exemples,
                 message=f"{lus['vus']} fichiers dans l'archive, {lus['gardes']} découpés "
                         f"(publiés depuis le {pa_cfg.get('depuis')}) ; archive gardée à l'octet")
        return r
    except Exception as e:  # un point d'accès qui casse n'arrête pas les autres
        r.update(issue="echec", complet=False,
                 message=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
        return r
    finally:
        r["fin"] = maintenant()
        if rep.chemin and os.path.exists(rep.chemin):
            os.unlink(rep.chemin)


def collecter(entrepot: Entrepot, transport: Transport, config: dict, mesures: Mesures,
              points: list[str] | None = None) -> list[dict]:
    params = config.get("parametres", {})
    releves = []
    for pa_cfg in config["points_acces"]:
        if not entrepot.qualifiant_a_jour(pa_cfg):
            with mesures.etape("requalifier", point_acces=pa_cfg["id"]) as m:
                m["uid_changes"] = entrepot.requalifier(pa_cfg)
    for pa_cfg in config["points_acces"]:
        if points and pa_cfg["id"] not in points:
            continue
        with mesures.etape("E1-E2", point_acces=pa_cfg["id"]) as m:
            if pa_cfg["format"] == "liste_tar":
                lot = relever_liste_tar(entrepot, transport, pa_cfg, params)
            elif pa_cfg["format"] == "archive_globale":
                lot = [relever_archive_globale(entrepot, transport, pa_cfg, params)]
            elif pa_cfg["format"] == "pe_eurodeputes":     # volet européen (collecte_pe)
                from .collecte_pe import relever_eurodeputes
                lot = [relever_eurodeputes(entrepot, transport, pa_cfg, params)]
            elif pa_cfg["format"] == "pe_votes":            # volet européen, votes (collecte_pe)
                from .collecte_pe import relever_votes
                lot = [relever_votes(entrepot, transport, pa_cfg, params)]
            else:
                lot = [relever_archive(entrepot, transport, pa_cfg, params)]
            for r in lot:
                entrepot.enregistrer_releve(r)
            releves += lot
            m["octets_recus"] = sum(r.get("octets_recus") or 0 for r in lot)
            m["nb_nouvelles_versions"] = sum(r.get("nb_nouvelles_versions") or 0 for r in lot)
            m["issues"] = sorted({r["issue"] for r in lot})
    return releves
