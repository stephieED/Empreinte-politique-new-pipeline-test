"""Dépaquetage d'une archive reçue (étape E2, correction P2).

On sort chaque fichier membre **à l'octet près**, sans rien interpréter ni filtrer. Le
membre est identifié par l'uid de son nom de fichier, pas par son dossier (doc. 2, 2.4).
"""
from __future__ import annotations

import hashlib
import os
import tarfile
import zipfile
import zlib
from dataclasses import dataclass
from typing import Iterator


@dataclass
class Membre:
    uid: str
    chemin: str        # chemin dans l'archive
    octets: bytes
    taille: int
    crc32: int
    empreinte: str     # SHA-256 des octets exacts


def uid_du_chemin(chemin: str) -> str:
    nom = os.path.basename(chemin)
    for ext in (".json", ".xml", ".sql", ".csv", ".txt", ".dat"):
        if nom.lower().endswith(ext):
            return nom[: -len(ext)]
    return nom


def _membre(uid: str, chemin: str, octets: bytes) -> Membre:
    return Membre(uid=uid, chemin=chemin, octets=octets, taille=len(octets),
                  crc32=zlib.crc32(octets) & 0xFFFFFFFF,
                  empreinte=hashlib.sha256(octets).hexdigest())


def depaqueter(chemin_archive: str, format_: str, uid_fixe: str | None = None) -> Iterator[Membre]:
    """Rend les membres un par un (mémoire bornée par le plus gros membre)."""
    if format_ == "zip":
        with zipfile.ZipFile(chemin_archive) as z:
            for info in z.infolist():
                if info.is_dir():
                    continue
                octets = z.read(info)          # vérifie le CRC : un zip abîmé lève une erreur
                yield _membre(uid_du_chemin(info.filename), info.filename, octets)
    elif format_ in ("tar", "liste_tar"):
        with tarfile.open(chemin_archive, mode="r:*") as t:
            for info in t:
                if not info.isfile():
                    continue
                f = t.extractfile(info)
                octets = f.read() if f else b""
                yield _membre(uid_du_chemin(info.name), info.name, octets)
    elif format_ in ("fichier", "api_json"):
        with open(chemin_archive, "rb") as f:
            octets = f.read()
        uid = uid_fixe or uid_du_chemin(chemin_archive)
        yield _membre(uid, os.path.basename(chemin_archive), octets)
    else:
        raise ValueError(f"format d'archive inconnu : {format_}")


def depaqueter_tar_flux(chemin_archive: str, garder, prefixe: str = "") -> Iterator[Membre]:
    """Archive tar compressée lue **en flux**, sans index : seuls les membres pour lesquels
    `garder(chemin, octets)` est vrai sont rendus, leur chemin précédé de `prefixe`. La liste des
    entrées déjà lues est vidée au fil de l'eau (l'archive globale du JO en compte 9,6 millions :
    gardée, elle montait à 6,8 Go de mémoire)."""
    with tarfile.open(chemin_archive, mode="r|*") as t:
        for info in t:
            t.members = []
            if not info.isfile():
                continue
            f = t.extractfile(info)
            octets = f.read() if f else b""
            if garder(info.name, octets):
                yield _membre(uid_du_chemin(info.name), prefixe + info.name, octets)


def verifier_archive(chemin_archive: str, format_: str) -> str | None:
    """Contrôle d'intégrité (E1). Rend un message d'erreur, ou None si l'archive est lisible."""
    try:
        if format_ == "zip":
            with zipfile.ZipFile(chemin_archive) as z:
                mauvais = z.testzip()
                if mauvais:
                    return f"zip : CRC faux sur {mauvais}"
                if not any(not i.is_dir() for i in z.infolist()):
                    return "zip vide"
        elif format_ in ("tar", "liste_tar"):
            with tarfile.open(chemin_archive, mode="r:*") as t:
                for _ in t:
                    pass
        elif format_ == "tar_flux":
            # Lue de bout en bout, sans garder la liste des entrées (archive globale du JO :
            # 9,6 millions d'entrées, 5,7 Go de mémoire en mode indexé).
            for _ in depaqueter_tar_flux(chemin_archive, lambda c, o: False):
                pass
        return None
    except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError, zlib.error) as e:
        return f"archive illisible : {type(e).__name__}: {e}"
