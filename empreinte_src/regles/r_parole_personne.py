"""R-PAROLE-PERSONNE : ce que chaque personne a dit en séance (doc. 1, 1.5.4 ; cahier 3.1.5 et 4.2
« Ce que cette personne a dit » ; mesures `an-amendements-cr.md`, 5 et 6).

Une ligne par paragraphe de compte rendu **attribué** à une personne (R-ORATEUR : identifiant
connu et nom affiché concordant ; un paragraphe publié sous l'identifiant d'une autre personne,
comme « Mme Alice Rufo » sous celui de François Ruffin, n'est pas attribué), au texte non vide.

- `preside` : la présidence de séance est gardée mais marquée — présider n'est pas intervenir
  dans le débat ; la fiche la montre à part ;
- `interruption` : exclamation depuis les bancs (code de la source), marquée ;
- qualité de l'orateur (R-QUALITE) et son origine (écrite par le compte rendu, ou déduite des
  fonctions à la date) ;
- sujet (R-SUJET : le point d'ordre du jour sous le créneau) et dossier quand il est établi ;
- `extrait` : les 300 premiers caractères du texte, espaces resserrés (`extrait_tronque` le dit) ;
- `source_url` : le lien public **au paragraphe** (ancre `id_syceron` de la page du compte
  rendu) ;
- `periode` (R-PERIODE) : la période de position de la personne à la date, si elle siège.

La règle ne compte rien par personne ; le compte des paroles est l'affaire de la fiche."""

NOM = "R-PAROLE-PERSONNE"
VERSION = 1
DEPEND = ("R-ORATEUR", "R-QUALITE", "R-SUJET", "R-PERIODE")
SORTIES = ("parole_personne",)
DESCRIPTION = (
    "Une prise de parole est un paragraphe du compte rendu de séance attribué à une personne : "
    "son identifiant est publié et le nom affiché correspond à son état civil. Chaque prise de "
    "parole est servie avec sa date, la qualité de l'orateur (écrite par le compte rendu, ou "
    "déduite de ses fonctions ce jour-là), le sujet (le point de l'ordre du jour, sous le créneau "
    "des questions), le texte discuté quand il est établi, un extrait des 300 premiers caractères "
    "et le lien direct vers le paragraphe sur le site de l'Assemblée. La présidence de séance est "
    "marquée à part : présider n'est pas intervenir dans le débat.")

LONGUEUR_EXTRAIT = 300
FIN_OUVERTE = "'9999-12-31'"


def appliquer(ctx):
    ctx.ecrire("parole_personne", f"""
        WITH a AS (
            SELECT a.acteur, a.compte_rendu, a.id_syceron, a.seance, a.date, a.preside, a.interruption,
                   trim(regexp_replace(i.texte, '\\s+', ' ', 'g')) AS texte, i.ordre_absolu_seance,
                   coalesce(i.prov_url, a.source_url) AS source_url
            FROM intervention_attribuee a
            JOIN an_comptes_rendus__intervention i USING (compte_rendu, id_syceron)
            WHERE a.acteur IS NOT NULL),
        per AS (
            SELECT a.compte_rendu, a.id_syceron, p.periode
            FROM a JOIN periode_position p ON p.acteur = a.acteur AND p.debut <= a.date
                                         AND coalesce(p.fin, {FIN_OUVERTE}) >= a.date)
        SELECT a.acteur, a.compte_rendu, a.id_syceron, a.date,
               q.qualite, q.qualite_source, q.raison_non_etablie AS raison_qualite,
               a.preside, a.interruption,
               s.sujet, s.statut AS statut_sujet, s.creneau, s.type_sujet, s.dossier, s.lien_dossier,
               left(a.texte, {LONGUEUR_EXTRAIT}) AS extrait, length(a.texte) > {LONGUEUR_EXTRAIT} AS extrait_tronque,
               length(a.texte) AS longueur, per.periode, q.gouvernement_a_la_date,
               a.seance, a.ordre_absolu_seance, a.source_url
        FROM a
        LEFT JOIN qualite_orateur q USING (compte_rendu, id_syceron)
        LEFT JOIN sujet_intervention s USING (compte_rendu, id_syceron)
        LEFT JOIN per USING (compte_rendu, id_syceron)
        WHERE a.texte IS NOT NULL AND a.texte <> ''
        ORDER BY a.acteur, a.date, a.compte_rendu, a.ordre_absolu_seance""")
    attr = ctx.un("SELECT count(*) FROM intervention_attribuee WHERE acteur IS NOT NULL")
    r = ctx.x("""SELECT count(*), count(*) FILTER (qualite IS NOT NULL),
                        count(*) FILTER (sujet IS NOT NULL), count(*) FILTER (dossier IS NOT NULL),
                        count(*) FILTER (source_url IS NOT NULL),
                        count(*) FILTER (NOT preside), count(*) FILTER (NOT preside AND qualite_source = 'compte_rendu')
                 FROM parole_personne""")[0]
    return {"paragraphe_attribue_au_texte_non_vide": (r[0], attr), "qualite_etablie": (r[1], r[0]),
            "qualite_ecrite_hors_presidence": (r[6], r[5]),
            "sujet_publie": (r[2], r[0]), "dossier_etabli": (r[3], r[0]), "lien_au_paragraphe": (r[4], r[0])}
