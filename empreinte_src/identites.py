"""Registre des identités (zone ZI, doc. 1, 1.3.4 ; correction P1).

L'attribution d'un identifiant interne `per:NNNNNN` est **acquise** : une fois donnée, elle
ne change plus, quel que soit l'ordre de lecture des sources ou l'arrivée d'une nouvelle.

- un (source, uid) déjà attribué garde son numéro ;
- une personne nouvelle reçoit le numéro suivant ; quand plusieurs arrivent ensemble, elles
  sont numérotées dans l'ordre de leur plus petit identifiant de source (pas dans l'ordre de
  lecture), pour que le résultat ne dépende pas de l'ordre ;
- deux personnes reconnues comme une seule gardent le numéro le plus ancien ; l'autre
  devient un alias (table `fusion`) ;
- un rapprochement reconnu faux clôt l'attribution et donne un numéro neuf ;
- le registre ne fait que croître : seule `jusqu_au` peut être remplie après coup.

Le même mécanisme donne aux **lignées de groupe** un numéro acquis `lig:NNNNNN` (classe
`RegistreLignees`, fichiers `lignee_*` du même dossier) : une lignée est l'ensemble des organes
de groupe (`("an", "PO…")`) que R-LIGNEE réunit ; deux lignées réunies par une fusion gardent le
numéro le plus ancien. Son adresse publique est inscrite une fois et ne change plus, même quand
la lignée change de nom ; une lignée absorbée garde la sienne, qui redirige vers la lignée
retenue. Les colonnes `per`, `per_absorbe`, `per_retenu` portent alors un numéro `lig:`.
"""
from __future__ import annotations

import json
import os

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA_ATTRIBUTION = pa.schema([
    ("per", pa.string()), ("source", pa.string()), ("uid", pa.string()),
    ("depuis", pa.int32()), ("jusqu_au", pa.int32()), ("motif", pa.string()),
])
SCHEMA_FUSION = pa.schema([
    ("per_absorbe", pa.string()), ("per_retenu", pa.string()),
    ("generation", pa.int32()), ("decision", pa.string()),
])


class RegistreModifie(Exception):
    """Le registre a perdu ou modifié une ligne : publication refusée (contrôle C1)."""


def per(n: int) -> str:
    return f"per:{n:06d}"


class RegistreIdentites:
    PREFIXE = "per"
    FICHIERS = {"attribution": "attribution.parquet", "fusion": "fusion.parquet",
                "compteur": "compteur.json"}

    def __init__(self, dossier: str):
        self.racine = dossier
        self.dossier = os.path.join(dossier, "registres")
        os.makedirs(self.dossier, exist_ok=True)
        self.attributions = self._lire(self.FICHIERS["attribution"])
        self.fusions = self._lire(self.FICHIERS["fusion"])
        p = os.path.join(self.dossier, self.FICHIERS["compteur"])
        self.compteur = json.load(open(p))[self.PREFIXE] if os.path.exists(p) else 0
        self._ouvertes = {(a["source"], a["uid"]): a for a in self.attributions
                          if a["jusqu_au"] is None}
        self._alias = {f["per_absorbe"]: f["per_retenu"] for f in self.fusions}
        self._lignees = None

    @property
    def lignees(self) -> "RegistreLignees":
        """Registre des lignées de groupe, rangé à côté (mêmes `registres/`, fichiers `lignee_*`)."""
        if self._lignees is None:
            self._lignees = RegistreLignees(self.racine)
        return self._lignees

    def _numero(self, n: int) -> str:
        return f"{self.PREFIXE}:{n:06d}"

    def _lire(self, nom):
        p = os.path.join(self.dossier, nom)
        return pq.read_table(p).to_pylist() if os.path.exists(p) else []

    # -- consultation ----------------------------------------------------------------------
    def resoudre(self, p: str) -> str:
        """Suit les alias jusqu'au numéro retenu."""
        vus = set()
        while p in self._alias and p not in vus:
            vus.add(p)
            p = self._alias[p]
        return p

    def numero(self, source: str, uid: str) -> str | None:
        a = self._ouvertes.get((source, uid))
        return self.resoudre(a["per"]) if a else None

    # -- attribution -----------------------------------------------------------------------
    def attribuer(self, groupes, generation: int, motif_nouveau="nouvelle_personne",
                  decision: str | None = None) -> dict:
        """`groupes` : une liste d'ensembles de (source, uid), chacun désignant une personne
        selon R-IDENTITE. Rend {(source, uid): per} pour tous les identifiants reçus."""
        groupes = [sorted(set(g)) for g in groupes if g]
        connus, nouveaux = [], []
        for g in groupes:
            pers = sorted({self.resoudre(self._ouvertes[i]["per"]) for i in g if i in self._ouvertes})
            (connus if pers else nouveaux).append((g, pers))
        # Les personnes nouvelles sont numérotées dans un ordre qui ne dépend pas de la lecture.
        nouveaux.sort(key=lambda gp: gp[0][0])
        for g, _ in nouveaux:
            self.compteur += 1
            p = self._numero(self.compteur)
            for (s, u) in g:
                self._ajouter(p, s, u, generation, motif_nouveau)
        for g, pers in connus:
            retenu = pers[0]                      # le plus ancien numéro
            for autre in pers[1:]:
                if self.resoudre(autre) != retenu:
                    f = {"per_absorbe": autre, "per_retenu": retenu, "generation": generation,
                         "decision": decision}
                    self.fusions.append(f)
                    self._alias[autre] = retenu
            for (s, u) in g:
                if (s, u) not in self._ouvertes:
                    self._ajouter(retenu, s, u, generation, "rapprochement" if not decision else "decision")
        return {i: self.numero(*i) for g in groupes for i in g}

    def separer(self, source: str, uid: str, generation: int, decision: str) -> str:
        """Un rapprochement reconnu faux : on clôt l'attribution et on donne un numéro neuf."""
        a = self._ouvertes.pop((source, uid))
        a["jusqu_au"] = generation
        self.compteur += 1
        p = self._numero(self.compteur)
        self._ajouter(p, source, uid, generation, "decision")
        return p

    def _ajouter(self, p, s, u, generation, motif):
        a = {"per": p, "source": s, "uid": u, "depuis": generation, "jusqu_au": None, "motif": motif}
        self.attributions.append(a)
        self._ouvertes[(s, u)] = a

    # -- persistance -----------------------------------------------------------------------
    def sauver(self):
        pq.write_table(pa.Table.from_pylist(self.attributions, schema=SCHEMA_ATTRIBUTION),
                       os.path.join(self.dossier, self.FICHIERS["attribution"]))
        pq.write_table(pa.Table.from_pylist(self.fusions, schema=SCHEMA_FUSION),
                       os.path.join(self.dossier, self.FICHIERS["fusion"]))
        with open(os.path.join(self.dossier, self.FICHIERS["compteur"]), "w") as f:
            json.dump({self.PREFIXE: self.compteur}, f)
        if self._lignees is not None:
            self._lignees.sauver()


SCHEMA_ADRESSE = pa.schema([("adresse", pa.string()), ("per", pa.string()), ("depuis", pa.int32())])


class RegistreLignees(RegistreIdentites):
    """Numéros acquis des lignées de groupe (`lig:NNNNNN`) et leurs adresses publiques."""
    PREFIXE = "lig"
    FICHIERS = {"attribution": "lignee_attribution.parquet", "fusion": "lignee_fusion.parquet",
                "compteur": "lignee_compteur.json", "adresse": "lignee_adresse.parquet"}

    def __init__(self, dossier: str):
        super().__init__(dossier)
        self.adresses = self._lire(self.FICHIERS["adresse"])
        self._par_adresse = {a["adresse"]: a for a in self.adresses}

    @property
    def lignees(self):
        raise AttributeError("un registre de lignées n'a pas de sous-registre")

    def adresse(self, lig: str) -> str | None:
        """Adresse inscrite pour ce numéro (la première inscrite, jamais changée)."""
        for a in self.adresses:
            if a["per"] == lig:
                return a["adresse"]
        return None

    def titulaire(self, adresse: str) -> str | None:
        """Lignée à laquelle une adresse renvoie aujourd'hui (alias suivis)."""
        a = self._par_adresse.get(adresse)
        return self.resoudre(a["per"]) if a else None

    def inscrire(self, lig: str, adresse: str, generation: int) -> bool:
        """Inscrit l'adresse d'une lignée qui n'en a pas ; refuse une adresse déjà prise."""
        if self.adresse(lig) is not None or adresse in self._par_adresse:
            return False
        a = {"adresse": adresse, "per": lig, "depuis": generation}
        self.adresses.append(a)
        self._par_adresse[adresse] = a
        return True

    def detacher(self, cles, generation: int, motif: str) -> str:
        """Des organes enregistrés dans une lignée en forment désormais une autre : leurs
        attributions sont closes (`jusqu_au`) et ils reçoivent ensemble un numéro neuf."""
        self.compteur += 1
        p = self._numero(self.compteur)
        for s, u in cles:
            a = self._ouvertes.pop((s, u), None)
            if a is not None:
                a["jusqu_au"] = generation
            self._ajouter(p, s, u, generation, motif)
        return p

    def sauver(self):
        super().sauver()
        pq.write_table(pa.Table.from_pylist(self.adresses, schema=SCHEMA_ADRESSE),
                       os.path.join(self.dossier, self.FICHIERS["adresse"]))


def verifier_ajout_seul(ancien: list[dict], nouveau: list[dict], cles=("per", "source", "uid", "depuis")):
    """Lève RegistreModifie si une ligne de l'ancien registre a disparu ou changé
    (seule `jusqu_au` peut passer de vide à une valeur)."""
    index = {tuple(r[k] for k in cles): r for r in nouveau}
    perdues, modifiees = [], []
    for r in ancien:
        k = tuple(r[c] for c in cles)
        n = index.get(k)
        if n is None:
            perdues.append(k)
            continue
        for c, v in r.items():
            if c == "jusqu_au" and v is None:
                continue
            if n.get(c) != v:
                modifiees.append((k, c))
    if perdues or modifiees:
        raise RegistreModifie(f"lignes perdues : {perdues[:5]} ; modifiées : {modifiees[:5]}")
