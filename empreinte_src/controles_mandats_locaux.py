"""A10 — Mandats locaux : élus homonymes non rattachés (décision Q53 du 23/11/2026, « Ne pas
rattacher, alerter »).

Quand le nom, le prénom et la date de naissance d'un candidat désignent, dans un fichier du
Répertoire national des élus où une personne n'a qu'un siège, deux collectivités différentes,
R-MANDAT-LOCAL ne rattache aucun des deux élus et l'écrit dans `mandat_local_ambigu`. Cet
avertissement (non bloquant) les nomme : un candidat et des collectivités, jamais un indice. Il
se règle par une décision (`references/elu_local/`), jamais d'office.

Module à part de `controles.py` pour ne pas toucher un fichier que d'autres chantiers modifient ;
il s'appuie sur les mêmes outils (`_a`, `_x`, `_avertir`) de l'objet `Controles`.
"""


def a10_elus_ambigus(ctrl) -> None:
    if not ctrl._a("mandat_local_ambigu"):
        return
    objets = [f"{c or per} : {n} élus de même nom, prénom et naissance ({naiss}) dans le fichier « {f} » "
              f"({coll}) ; aucun n'est rattaché"
              for per, c, naiss, f, n, coll in ctrl._x("""
                  SELECT per, candidat, naissance, fichier, collectivites_distinctes, collectivites
                  FROM mandat_local_ambigu ORDER BY candidat, fichier""")]
    ctrl._avertir("A10", "Mandats locaux : homonymes non rattachés", objets,
                  detail="Le Répertoire national des élus n'a pas d'identifiant de personne ; un candidat "
                         "n'est rattaché que si son nom, son prénom et sa date de naissance désignent un "
                         "seul élu. Une décision `elu_local` tranche.")
