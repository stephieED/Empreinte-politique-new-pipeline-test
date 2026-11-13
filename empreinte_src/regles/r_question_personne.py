"""R-QUESTION-PERSONNE : les questions posées par chaque député (cahier 3.1.6 et 4.2 « Ce que cette
personne a dit » ; lecteur `an_questions`).

Une ligne par question : écrite (`QE`), au gouvernement (`QG`), orale sans débat (`QOSD`), avec
son auteur tel que publié, le ministère interrogé (organe et libellé publiés) et le dernier
ministère attributaire, la rubrique, l'analyse, les dates de question et de réponse, la clôture.

- Une question au gouvernement n'a pas de date de question publiée : elle est posée et reçoit sa
  réponse le même jour, en séance ; `date` est alors la date de la réponse (`date_nature` le dit).
  Elle ne porte aucune référence de séance : son rapprochement avec une prise de parole est
  l'affaire de R-QAG (tranche suivante).
- Une question sans réponse a `date_reponse` vide (jamais une date inventée).
- **Adresse publique** : `https://www.assemblee-nationale.fr/dyn/{leg}/questions/{uid}`, vérifiée
  le 06/11/2026 (`QANR5L17QE5268` : page de la question n° 5268 ; un identifiant inventé répond
  404) ; la vérification croisée (A2) en relit un échantillon chaque nuit."""

NOM = "R-QUESTION-PERSONNE"
VERSION = 2
DEPEND = ()
SORTIES = ("question_personne",)
DESCRIPTION = (
    "Les questions écrites, les questions au gouvernement et les questions orales sans débat sont "
    "lues dans les données de l'Assemblée, avec leur auteur, le ministère interrogé, la rubrique et "
    "les dates de question et de réponse. Une question au gouvernement est posée et reçoit sa "
    "réponse le même jour, en séance : sa date est celle de la séance. Une question sans réponse "
    "reste sans date de réponse. Le lien vers la page publique d'une question n'est servi que "
    "lorsqu'il figure dans les données.")

TYPES = {"QE": "ecrite", "QG": "au_gouvernement", "QOSD": "orale_sans_debat"}


def appliquer(ctx):
    """Applique R-QUESTION-PERSONNE : écrit `question_personne`, les questions posées par chaque
    député (voir la description du module). Rend la couverture, `{nom: (numérateur, dénominateur)}`
    : `question_avec_auteur`, `date_etablie`, `ministere_interroge_publie`, `rubrique_publiee`,
    `reponse_publiee`, `adresse_publique_verifiable`."""
    cas = " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in TYPES.items())
    ctx.ecrire("question_personne", f"""
        SELECT q.auteur AS acteur, q.uid AS question, CASE q.type {cas} END AS type, q.type AS type_code,
               coalesce(q.date_question, CASE WHEN q.type = 'QG' THEN q.date_reponse END) AS date,
               CASE WHEN q.date_question IS NOT NULL THEN 'question_publiee_au_jo'
                    WHEN q.type = 'QG' AND q.date_reponse IS NOT NULL THEN 'seance_de_la_reponse' END AS date_nature,
               q.ministere_interroge AS ministere, q.ministere_interroge_libelle AS ministere_libelle,
               q.ministere_interroge_abrege AS ministere_abrege,
               q.ministeres_attributaires[-1].organe AS ministere_attributaire,
               q.ministeres_attributaires[-1].libelle AS ministere_attributaire_libelle,
               q.rubrique, q.tete_analyse, q.analyses, q.date_reponse,
               q.libelle_cloture AS cloture, q.date_cloture,
               q.auteur_groupe AS groupe_source, q.legislature, q.numero,
               coalesce(q.prov_url, 'https://www.assemblee-nationale.fr/dyn/' || q.legislature || '/questions/' || q.uid)
                   AS source_url,
               CASE WHEN q.legislature IS NULL AND q.prov_url IS NULL THEN 'legislature_inconnue' END AS raison_source_url
        FROM an_questions__question q
        WHERE q.auteur IS NOT NULL
        ORDER BY q.auteur, date, q.uid""")
    r = ctx.x("""SELECT count(*), count(*) FILTER (date IS NOT NULL), count(*) FILTER (ministere_libelle IS NOT NULL),
                        count(*) FILTER (rubrique IS NOT NULL), count(*) FILTER (date_reponse IS NOT NULL),
                        count(*) FILTER (source_url IS NOT NULL)
                 FROM question_personne""")[0]
    n = ctx.un("SELECT count(*) FROM an_questions__question")
    return {"question_avec_auteur": (r[0], n), "date_etablie": (r[1], r[0]),
            "ministere_interroge_publie": (r[2], r[0]), "rubrique_publiee": (r[3], r[0]),
            "reponse_publiee": (r[4], r[0]), "adresse_publique_verifiable": (r[5], r[0])}
