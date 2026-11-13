"""Entrepôt (zones Z0 et Z1, doc. 1, 1.1 et 1.3).

Copie de travail locale, dans un dossier :

    manifeste.json            génération, date, empreinte de chaque fichier de l'entrepôt
    index.parquet             une ligne par version de membre (Z1)
    releves.parquet           le journal des relevés (Z0)
    generations.parquet       génération -> date, version du code
    blobs/blobs-gNNNNNN-KKK.parquet   octets exacts des membres, rangés par empreinte
    membres/membres-gNNNNNN.parquet   liste des membres de chaque archive reçue (P2)
    registres/...             registre des identités (ZI, voir identites.py)

Règles tenues ici :
- une nouvelle version n'est créée que si l'empreinte des octets change ;
- seul un relevé complet et non suspect fait constater un retrait (doc. 2, 2.4) ;
- un point d'accès « delta » (le JO livre des ajouts) ne fait jamais constater de retrait ;
- un 304 prolonge vu_jusqu_au des membres présents ;
- les octets ne sont jamais interprétés ni filtrés (correction P2).

La synchronisation avec les *releases* GitHub est dans `distant.py` ; seule la tâche
`ecrire` l'appelle (correction P3).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from dataclasses import dataclass, field

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA_INDEX = pa.schema([
    ("point_acces", pa.string()), ("source", pa.string()), ("type", pa.string()),
    ("uid", pa.string()), ("version", pa.int32()), ("empreinte", pa.string()),
    ("chemin", pa.string()), ("taille", pa.int64()), ("etat", pa.string()),
    ("vu_du", pa.int32()), ("vu_jusqu_au", pa.int32()), ("releve_id", pa.string()),
])
SCHEMA_BLOBS = pa.schema([
    ("empreinte", pa.string()), ("morceau", pa.int32()), ("nb_morceaux", pa.int32()),
    ("octets", pa.large_binary()),
])
SCHEMA_MEMBRES = pa.schema([
    ("releve_id", pa.string()), ("uid", pa.string()), ("chemin", pa.string()),
    ("taille", pa.int64()), ("crc32", pa.int64()), ("empreinte", pa.string()),
])
CHAMPS_RELEVE = [
    "releve_id", "generation", "point_acces", "source", "url", "debut", "fin", "issue",
    "complet", "suspect", "statut_http", "etag", "last_modified", "content_length", "taille",
    "empreinte", "octets_recus", "tentatives", "reprises", "duree_s", "nb_membres",
    "nb_nouvelles_versions", "nb_inchanges", "nb_retraits", "nb_reapparitions",
    "nb_doublons", "date_source", "curseur", "message",
]
PRESENT, RETIRE = "present", "retire_a_la_source"
_CHAMPS_INDEX = tuple(SCHEMA_INDEX.names)
# Champs aux valeurs très répétées : une seule chaîne en mémoire pour toutes les lignes.
_REPETES = ("point_acces", "source", "type", "etat", "releve_id")


class Ligne:
    """Une ligne de l'index, compacte : ≈ 0,6 Ko au lieu de 1,7 Ko pour un dictionnaire (mesuré le
    13/11/2026 : 1,36 Go pour 815 000 lignes, avant les 870 000 fichiers de l'archive globale du
    JO). Elle se lit comme un dictionnaire (`r["uid"]`, `r["etat"] = …`)."""
    __slots__ = _CHAMPS_INDEX

    def __init__(self, **kw):
        for k in _CHAMPS_INDEX:
            setattr(self, k, kw.get(k))

    def __getitem__(self, k):
        return getattr(self, k)

    def __setitem__(self, k, v):
        setattr(self, k, v)

    def get(self, k, defaut=None):
        return getattr(self, k, defaut)

    def keys(self):
        return _CHAMPS_INDEX

    def __eq__(self, autre):
        return isinstance(autre, Ligne) and all(self[k] == autre[k] for k in _CHAMPS_INDEX)


def maintenant() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_fichier(chemin: str) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


@dataclass
class Bilan:
    nouvelles: int = 0
    inchanges: int = 0
    retraits: int = 0
    reapparitions: int = 0
    doublons: int = 0
    membres: int = 0
    exemples: dict = field(default_factory=dict)


class Entrepot:
    def __init__(self, dossier: str, segment_max: int = 90 << 20, morceau_max: int = 64 << 20):
        self.dossier = dossier
        self.segment_max = segment_max
        self.morceau_max = morceau_max
        for d in ("blobs", "membres", "registres"):
            os.makedirs(os.path.join(dossier, d), exist_ok=True)
        self.manifeste = self._lire_json("manifeste.json") or {
            "generation": 0, "cree_le": None, "fichiers": {}, "precedent": None}
        self.generation_base = self.manifeste["generation"]
        self.generation = self.generation_base + 1      # celle que cette exécution produit
        self._interne: dict[str, str] = {}
        self._index = self._lire_index()
        self._releves = self._lire_table("releves.parquet")
        self._empreintes_connues = {r["empreinte"] for r in self._index}
        self._derniere = {}                              # (point, uid) -> position dans _index
        for i, r in enumerate(self._index):
            self._derniere[(r["point_acces"], r["uid"])] = i
        self._blobs_buffer: list[dict] = []
        self._blobs_taille = 0
        self._blobs_fichiers: list[str] = []
        self._membres: list[dict] = []
        self._membres_ecrivain = None

    def _i(self, v):
        """Chaîne partagée pour une valeur répétée (point d'accès, type, état, relevé)."""
        return v if v is None else self._interne.setdefault(v, v)

    # -- lecture ------------------------------------------------------------------------
    def _lire_json(self, nom):
        p = os.path.join(self.dossier, nom)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
        return None

    def _lire_table(self, nom) -> list[dict]:
        p = os.path.join(self.dossier, nom)
        return pq.read_table(p).to_pylist() if os.path.exists(p) else []

    def _lire_index(self) -> list[Ligne]:
        p = os.path.join(self.dossier, "index.parquet")
        if not os.path.exists(p):
            return []
        t = pq.read_table(p)
        cols = {c: t.column(c).to_pylist() if c in t.column_names else [None] * t.num_rows
                for c in _CHAMPS_INDEX}
        del t
        for c in _REPETES:
            cols[c] = [self._i(v) for v in cols[c]]
        rows = [Ligne(**dict(zip(_CHAMPS_INDEX, vals))) for vals in zip(*(cols[c] for c in _CHAMPS_INDEX))]
        rows.sort(key=lambda r: (r["point_acces"], r["uid"], r["version"]))
        return rows

    def dernier_releve(self, point_acces: str, complet_seulement=False) -> dict | None:
        for r in reversed(self._releves):
            if r["point_acces"] == point_acces and (r["complet"] or not complet_seulement):
                if r["issue"] in ("nouveau", "inchange"):
                    return r
        return None

    def presents(self, point_acces: str) -> dict[str, dict]:
        out = {}
        for (p, uid), i in self._derniere.items():
            if p == point_acces and self._index[i]["etat"] == PRESENT:
                out[uid] = self._index[i]
        return out

    # -- écriture d'un relevé -----------------------------------------------------------
    def enregistrer_releve(self, releve: dict):
        r = {k: releve.get(k) for k in CHAMPS_RELEVE}
        r["generation"] = self.generation
        self._releves.append(r)

    # -- identifiant stable d'un membre ---------------------------------------------------
    @staticmethod
    def uid_stable(pa_cfg: dict, uid_base: str, chemin: str) -> str:
        """L'uid d'un membre. Si le point d'accès déclare `qualifier_uid` (une expression dont
        le groupe `q` lit le dossier du membre, sans l'horodatage de livraison), l'uid est
        qualifié par ce dossier : un même identifiant rangé dans deux dossiers d'une archive
        (plan et version d'un texte du JO) donne deux membres stables d'une livraison à l'autre."""
        motif = pa_cfg.get("qualifier_uid")
        if motif:
            m = re.search(motif, chemin)
            if m:
                return f"{uid_base}@{m.group('q').replace('/', '-')}"
        return uid_base

    def requalifier(self, pa_cfg: dict) -> int:
        """Réapplique la règle d'uid à tout l'historique d'un point d'accès, depuis les chemins
        gardés (correction P2 : un découpage corrigé atteint l'historique sans recollecte).
        Rend le nombre d'uid changés."""
        lignes = [r for r in self._index if r["point_acces"] == pa_cfg["id"]]
        changes = 0
        for r in lignes:
            nouveau = self.uid_stable(pa_cfg, r["uid"].split("@")[0], r["chemin"])
            if nouveau != r["uid"]:
                r["uid"] = nouveau
                changes += 1
        # Versions renumérotées par uid, dans l'ordre où elles ont été vues.
        par_uid: dict[str, list] = {}
        for r in lignes:
            par_uid.setdefault(r["uid"], []).append(r)
        for rs in par_uid.values():
            rs.sort(key=lambda r: (r["vu_du"], r["version"]))
            for k, r in enumerate(rs, 1):
                r["version"] = k
        self._index.sort(key=lambda r: (r["point_acces"], r["uid"], r["version"]))
        self._derniere = {(r["point_acces"], r["uid"]): i for i, r in enumerate(self._index)}
        self.manifeste.setdefault("qualifiants", {})[pa_cfg["id"]] = pa_cfg.get("qualifier_uid")
        return changes

    def qualifiant_a_jour(self, pa_cfg: dict) -> bool:
        return self.manifeste.get("qualifiants", {}).get(pa_cfg["id"]) == pa_cfg.get("qualifier_uid")

    def versionner(self, pa_cfg: dict, releve_id: str, membres, complet: bool,
                   delta: bool = False) -> Bilan:
        """Range les membres d'une archive reçue. `membres` est un itérable de Membre."""
        point, gen = pa_cfg["id"], self.generation
        bilan = Bilan()
        vus: dict[str, str] = {}
        for m in membres:
            uid = self.uid_stable(pa_cfg, m.uid, m.chemin)
            if uid in vus:                    # même uid deux fois dans l'archive
                bilan.doublons += 1
                uid = f"{uid}@{hashlib.sha1(m.chemin.encode()).hexdigest()[:8]}"
            vus[uid] = m.empreinte
            bilan.membres += 1
            self._membres.append({"releve_id": releve_id, "uid": uid, "chemin": m.chemin,
                                  "taille": m.taille, "crc32": m.crc32, "empreinte": m.empreinte})
            if len(self._membres) >= 50_000:
                self._vider_membres()
            i = self._derniere.get((point, uid))
            der = self._index[i] if i is not None else None
            if der is not None and der["etat"] == PRESENT and der["empreinte"] == m.empreinte:
                der["vu_jusqu_au"] = gen
                bilan.inchanges += 1
                continue
            if der is not None and der["etat"] == RETIRE:
                bilan.reapparitions += 1
            self._ajouter_blob(m.empreinte, m.octets)
            self._ajouter_version(pa_cfg, uid, m.empreinte, m.chemin, m.taille, PRESENT,
                                  releve_id, (der["version"] + 1) if der else 1)
            bilan.nouvelles += 1
            if len(bilan.exemples.setdefault("nouvelles", [])) < 5:
                bilan.exemples["nouvelles"].append(uid)
        if complet and not delta:
            for uid, der in self.presents(point).items():
                if uid not in vus:
                    self._ajouter_version(pa_cfg, uid, der["empreinte"], der["chemin"],
                                          der["taille"], RETIRE, releve_id, der["version"] + 1)
                    bilan.retraits += 1
                    if len(bilan.exemples.setdefault("retraits", [])) < 5:
                        bilan.exemples["retraits"].append(uid)
        return bilan

    def _vider_membres(self, fin: bool = False):
        """Liste des membres reçus (P2), écrite au fil de l'eau par lots : l'archive globale du JO
        en apporte 870 000 d'un coup."""
        if self._membres:
            if self._membres_ecrivain is None:
                self._membres_ecrivain = pq.ParquetWriter(
                    os.path.join(self.dossier, "membres", f"membres-g{self.generation:06d}.parquet"),
                    SCHEMA_MEMBRES, compression="zstd")
            self._membres_ecrivain.write_table(pa.Table.from_pylist(self._membres, schema=SCHEMA_MEMBRES))
            self._membres = []
        if fin and self._membres_ecrivain is not None:
            self._membres_ecrivain.close()
            self._membres_ecrivain = None

    def prolonger(self, point_acces: str):
        """Relevé « inchangé » (304) sur un point dont le dernier relevé était complet."""
        for der in self.presents(point_acces).values():
            der["vu_jusqu_au"] = self.generation

    def _ajouter_version(self, pa_cfg, uid, empreinte, chemin, taille, etat, releve_id, version):
        r = Ligne(point_acces=self._i(pa_cfg["id"]), source=self._i(pa_cfg["source"]),
                  type=self._i(pa_cfg["type"]), uid=uid, version=version, empreinte=empreinte,
                  chemin=chemin, taille=taille, etat=self._i(etat), vu_du=self.generation,
                  vu_jusqu_au=self.generation, releve_id=self._i(releve_id))
        self._index.append(r)
        self._derniere[(pa_cfg["id"], uid)] = len(self._index) - 1

    # -- octets ------------------------------------------------------------------------
    def _ajouter_blob(self, empreinte: str, octets: bytes):
        if empreinte in self._empreintes_connues:
            return
        self._empreintes_connues.add(empreinte)
        n = max(1, -(-len(octets) // self.morceau_max))
        for k in range(n):
            part = octets[k * self.morceau_max:(k + 1) * self.morceau_max]
            self._blobs_buffer.append({"empreinte": empreinte, "morceau": k,
                                       "nb_morceaux": n, "octets": part})
            self._blobs_taille += len(part)
            if self._blobs_taille >= 16 << 20:
                self._vider_blobs()

    def _vider_blobs(self):
        if not self._blobs_buffer:
            return
        if not self._blobs_fichiers or os.path.getsize(self._blobs_fichiers[-1]) > self.segment_max - (24 << 20):
            if getattr(self, "_writer", None):
                self._writer.close()
            nom = os.path.join(self.dossier, "blobs",
                               f"blobs-g{self.generation:06d}-{len(self._blobs_fichiers):03d}.parquet")
            self._blobs_fichiers.append(nom)
            self._writer = pq.ParquetWriter(nom, SCHEMA_BLOBS, compression="zstd",
                                            compression_level=9)
        self._writer.write_table(pa.Table.from_pylist(self._blobs_buffer, schema=SCHEMA_BLOBS))
        self._blobs_buffer, self._blobs_taille = [], 0

    def parcourir(self, empreintes):
        """Rend (empreinte, octets) pour les empreintes demandées, en un seul passage sur les
        fichiers d'octets, groupe de lignes par groupe de lignes (mémoire bornée)."""
        import pyarrow.compute as pc
        voulues = pa.array(sorted(set(empreintes)), type=pa.string())
        if len(voulues) == 0:
            return
        en_cours: dict[str, list] = {}
        for nom in sorted(os.listdir(os.path.join(self.dossier, "blobs"))):
            f = pq.ParquetFile(os.path.join(self.dossier, "blobs", nom))
            for rg in range(f.num_row_groups):
                # D'abord la seule colonne des empreintes : on ne décompresse les octets que
                # des groupes de lignes qui contiennent ce qu'on cherche.
                cles = f.read_row_group(rg, columns=["empreinte"])["empreinte"]
                if not pc.any(pc.is_in(cles, value_set=voulues)).as_py():
                    continue
                t = f.read_row_group(rg)
                t = t.filter(pc.is_in(t["empreinte"], value_set=voulues))
                for r in t.to_pylist():
                    if r["nb_morceaux"] == 1:
                        yield r["empreinte"], r["octets"]
                        continue
                    ms = en_cours.setdefault(r["empreinte"], [])
                    ms.append(r)
                    if len(ms) == r["nb_morceaux"]:
                        ms.sort(key=lambda x: x["morceau"])
                        yield r["empreinte"], b"".join(x["octets"] for x in ms)
                        del en_cours[r["empreinte"]]

    def lire_plusieurs(self, empreintes) -> dict[str, bytes]:
        """Rend {empreinte: octets} en lisant chaque fichier d'octets une seule fois."""
        import pyarrow.compute as pc
        voulues = pa.array(sorted(set(empreintes)), type=pa.string())
        morceaux: dict[str, list] = {}
        for nom in sorted(os.listdir(os.path.join(self.dossier, "blobs"))):
            f = pq.ParquetFile(os.path.join(self.dossier, "blobs", nom))
            for rg in range(f.num_row_groups):
                t = f.read_row_group(rg)
                t = t.filter(pc.is_in(t["empreinte"], value_set=voulues))
                for r in t.to_pylist():
                    morceaux.setdefault(r["empreinte"], []).append(r)
        out = {}
        for emp, ms in morceaux.items():
            ms.sort(key=lambda r: r["morceau"])
            if len(ms) == ms[0]["nb_morceaux"]:
                out[emp] = b"".join(r["octets"] for r in ms)
        return out

    def lire_octets(self, empreinte: str) -> bytes:
        """Rend les octets exacts d'une version (pour la lecture et la reconstruction)."""
        morceaux = []
        for nom in sorted(os.listdir(os.path.join(self.dossier, "blobs"))):
            t = pq.read_table(os.path.join(self.dossier, "blobs", nom),
                              filters=[("empreinte", "=", empreinte)])
            morceaux += t.to_pylist()
            if morceaux and len(morceaux) == morceaux[0]["nb_morceaux"]:
                break
        if not morceaux:
            raise KeyError(empreinte)
        morceaux.sort(key=lambda r: r["morceau"])
        return b"".join(r["octets"] for r in morceaux)

    # -- clôture de la génération --------------------------------------------------------
    def clore(self, version_code: str) -> dict:
        """Écrit les fichiers de la génération et rend le nouveau manifeste.
        Rien n'est envoyé ici : c'est la tâche `ecrire` qui publie (P3)."""
        self._vider_blobs()
        if getattr(self, "_writer", None):
            self._writer.close()
            self._writer = None
        d = self.dossier
        pq.write_table(pa.Table.from_pydict({c: [r[c] for r in self._index] for c in _CHAMPS_INDEX},
                                            schema=SCHEMA_INDEX),
                       os.path.join(d, "index.parquet"), compression="zstd")
        pq.write_table(pa.Table.from_pylist(self._releves), os.path.join(d, "releves.parquet"),
                       compression="zstd")
        self._vider_membres(fin=True)
        gens = self._lire_table("generations.parquet")
        gens.append({"generation": self.generation, "date": maintenant(), "code": version_code})
        pq.write_table(pa.Table.from_pylist(gens), os.path.join(d, "generations.parquet"))
        # La tâche de collecte n'a pas les octets des générations passées : on part de la liste
        # du manifeste précédent et l'on y met à jour ce qui existe ici.
        fichiers = dict(self.manifeste.get("fichiers", {}))
        for racine, _, noms in os.walk(d):
            for n in noms:
                p = os.path.join(racine, n)
                rel = os.path.relpath(p, d)
                if rel.startswith("manifeste") or rel.startswith("rattrapage"):
                    continue
                fichiers[rel] = {"sha256": sha256_fichier(p), "taille": os.path.getsize(p)}
        precedent = self.manifeste.get("sha256_manifeste")
        nouveau = {"generation": self.generation, "base": self.generation_base,
                   "cree_le": maintenant(), "code": version_code,
                   "qualifiants": self.manifeste.get("qualifiants", {}),
                   "fichiers": dict(sorted(fichiers.items())), "precedent": precedent}
        corps = json.dumps(nouveau, sort_keys=True, ensure_ascii=False).encode()
        nouveau["sha256_manifeste"] = hashlib.sha256(corps).hexdigest()
        with open(os.path.join(d, "manifeste.json"), "w") as f:
            json.dump(nouveau, f, indent=1, sort_keys=True, ensure_ascii=False)
        self.manifeste = nouveau
        return nouveau

    def ranger_brute(self, nom: str, chemin: str) -> str:
        """Garde à l'octet une archive reçue dont seule une partie est découpée (archive globale du
        JO, décision du 13/11/2026). Elle est rangée dans `brutes/`, entre au manifeste avec son
        empreinte, et la tâche d'écriture la dépose dans une release à part (`archives-brutes`),
        qui n'est pas rapatriée chaque nuit. Rend son chemin relatif."""
        import shutil
        rel = os.path.join("brutes", nom)
        os.makedirs(os.path.join(self.dossier, "brutes"), exist_ok=True)
        shutil.move(chemin, os.path.join(self.dossier, rel))
        return rel

    def actualiser_fichiers(self, chemins_relatifs: list[str]) -> dict:
        """Le registre des identités est enrichi par la tâche de calcul, après la collecte :
        avant l'écriture, on remet à jour l'empreinte de ces fichiers dans le manifeste, et
        l'empreinte du manifeste lui-même."""
        man = dict(self.manifeste)
        man.pop("sha256_manifeste", None)
        for rel in chemins_relatifs:
            p = os.path.join(self.dossier, rel)
            man["fichiers"][rel] = {"sha256": sha256_fichier(p), "taille": os.path.getsize(p)}
        man["fichiers"] = dict(sorted(man["fichiers"].items()))
        corps = json.dumps(man, sort_keys=True, ensure_ascii=False).encode()
        man["sha256_manifeste"] = hashlib.sha256(corps).hexdigest()
        with open(os.path.join(self.dossier, "manifeste.json"), "w") as f:
            json.dump(man, f, indent=1, sort_keys=True, ensure_ascii=False)
        self.manifeste = man
        return man

    # -- reconstruction (P2) -------------------------------------------------------------
    def membres_du_releve(self, releve_id: str) -> list[dict]:
        out = []
        for nom in sorted(os.listdir(os.path.join(self.dossier, "membres"))):
            t = pq.read_table(os.path.join(self.dossier, "membres", nom),
                              filters=[("releve_id", "=", releve_id)])
            out += t.to_pylist()
        return out
