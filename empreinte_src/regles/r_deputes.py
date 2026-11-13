"""R-DEPUTES : les mandats de député, avec la suspension du mandat d'un député entré au
gouvernement (cahier 3.1.1 ; mesures `an-acteurs.md`, 2.3).

Une ligne par mandat ASSEMBLEE de la source. La source n'a pas de champ « suspension » : elle se
lit dans une chaîne de mandats.

1. le mandat d'origine est clos avec la cause « Nomination comme membre du Gouvernement »
   (environ un mois après la nomination) ;
2. le suppléant reçoit un mandat (« remplacement d'un député nommé au Gouvernement »), clos à
   la reprise ; il ne renvoie presque jamais au mandat remplacé (8 fois sur 248) : la règle le
   retrouve par la circonscription et la date (il commence le lendemain de la fin du mandat
   d'origine) ;
3. le mandat de reprise (« reprise de l'exercice du mandat d'un ancien membre du
   Gouvernement ») renvoie au mandat d'origine (`mandat_remplace`, 113 fois sur 113).

Piège : la date de début d'un mandat de reprise (et d'un mandat de suppléant) **recopie** la date
d'élection ; la vraie date d'entrée en fonction est `date_prise_fonction`. La règle prend donc
`debut` = date de prise de fonction (la date publiée est gardée dans `date_debut_source`).

La suspension est portée par le mandat d'origine : `suspendu_du` = lendemain de sa fin,
`suspendu_au` = veille de la prise de fonction de la reprise. Sans mandat de reprise dans la
source, `suspendu_au` reste vide et `suspension_statut = 'sans_reprise'` (toujours ministre, ou
mandat non repris avant la fin de la législature : la source ne le dit pas, la règle non plus).
Un mandat de reprise peut à son tour être suspendu (nouvelle nomination) : chaque mandat porte
sa propre suspension. Être député à une date = avoir une ligne dont la période la contient.
"""

NOM = "R-DEPUTES"
VERSION = 1
DEPEND = ("R-LEGISLATURES",)
SORTIES = ("depute",)
DESCRIPTION = (
    "Un mandat de député est lu dans l'archive de l'Assemblée nationale, avec sa circonscription, "
    "sa date de prise de fonction et sa cause de fin. Un député nommé au gouvernement n'a pas "
    "perdu son mandat : il est suspendu et son suppléant siège à sa place. La source ne le dit "
    "par aucun champ : nous reconstituons la suspension à partir du mandat clos par la "
    "nomination et du mandat de reprise, daté de la prise de fonction publiée (la date de début "
    "de ce mandat recopie celle de l'élection). Sans mandat de reprise, la fin de la suspension "
    "n'est pas connue et reste vide.")

MANDAT = """(SELECT * FROM an_acteurs__mandat
             QUALIFY row_number() OVER (PARTITION BY uid ORDER BY prov_point DESC) = 1)"""
NOMINATION = "Nomination comme membre du Gouvernement"


def appliquer(ctx):
    """Applique R-DEPUTES : écrit `depute`, les mandats de député avec leurs suspensions et
    reprises (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `date_prise_fonction_publiee`,
    `suspension_close_par_une_reprise`, `suppleant_identifie`,
    `reprise_reliee_au_mandat_suspendu`."""
    ctx.x(f"""CREATE OR REPLACE TEMP TABLE _ga_an AS
        SELECT m.uid, m.acteur, TRY_CAST(m.legislature AS INTEGER) AS legislature,
               coalesce(m.date_prise_fonction, m.date_debut) AS debut,
               m.date_debut AS date_debut_source, m.date_prise_fonction, m.date_fin AS fin,
               m.cause_mandat, m.cause_fin, m.circonscription, m.departement, m.num_departement,
               m.num_circo, m.mandat_remplace, m.premiere_election,
               m.prov_url AS source_url, m.prov_uid
        FROM {MANDAT} m WHERE m.type_organe = 'ASSEMBLEE'""")
    ctx.ecrire("depute", f"""
        WITH rep AS (   -- mandat de reprise : renvoie au mandat suspendu de la même personne
            SELECT r.mandat_remplace AS origine, arg_min(r.uid, r.debut) AS uid, min(r.debut) AS debut
            FROM _ga_an r WHERE r.cause_mandat ILIKE 'reprise de l''exercice du mandat%'
              AND r.mandat_remplace IS NOT NULL
            GROUP BY 1),
        sup AS (        -- mandat du suppléant : même circonscription, commence le lendemain
            SELECT o.uid AS origine, list_sort(list(s.uid)) AS uids
            FROM _ga_an o JOIN _ga_an s
              ON o.cause_fin = '{NOMINATION}' AND s.legislature = o.legislature
             AND s.circonscription = o.circonscription AND s.acteur <> o.acteur
             AND s.cause_mandat ILIKE 'remplacement d''un député nommé au Gouvernement%'
             AND s.debut::DATE = o.fin::DATE + 1
            GROUP BY 1)
        SELECT a.acteur, a.legislature, a.uid AS mandat, a.debut, a.fin,
               CASE WHEN a.cause_fin = '{NOMINATION}' AND a.fin IS NOT NULL
                    THEN strftime(a.fin::DATE + 1, '%Y-%m-%d') END AS suspendu_du,
               CASE WHEN a.cause_fin = '{NOMINATION}' AND rep.debut IS NOT NULL
                    THEN strftime(rep.debut::DATE - 1, '%Y-%m-%d') END AS suspendu_au,
               a.circonscription, a.cause_fin,
               CASE WHEN a.cause_fin <> '{NOMINATION}' OR a.cause_fin IS NULL THEN NULL
                    WHEN rep.uid IS NOT NULL THEN 'reprise' ELSE 'sans_reprise' END AS suspension_statut,
               CASE WHEN a.cause_fin = '{NOMINATION}' THEN rep.uid END AS mandat_reprise,
               CASE WHEN a.cause_fin = '{NOMINATION}' AND len(sup.uids) = 1 THEN sup.uids[1] END AS mandat_suppleant,
               CASE WHEN a.cause_mandat ILIKE 'reprise de l''exercice du mandat%' THEN a.mandat_remplace
                    END AS mandat_suspendu,
               a.cause_mandat, a.date_debut_source, a.date_prise_fonction,
               a.departement, a.num_departement, a.num_circo, a.premiere_election,
               a.source_url, a.prov_uid
        FROM _ga_an a LEFT JOIN rep ON rep.origine = a.uid LEFT JOIN sup ON sup.origine = a.uid
        ORDER BY a.legislature, a.acteur, a.debut""")

    nom = ctx.un("SELECT count(*) FROM depute WHERE suspendu_du IS NOT NULL")
    repris = ctx.un("SELECT count(*) FROM depute WHERE suspension_statut = 'reprise'")
    supp = ctx.un("SELECT count(*) FROM depute WHERE mandat_suppleant IS NOT NULL")
    reprises = ctx.un("SELECT count(*) FROM depute WHERE cause_mandat ILIKE 'reprise de l''exercice%'")
    reprises_liees = ctx.un("""SELECT count(*) FROM depute d WHERE cause_mandat ILIKE 'reprise de l''exercice%'
                               AND EXISTS (SELECT 1 FROM depute o WHERE o.mandat = d.mandat_suspendu)""")
    n = ctx.un("SELECT count(*) FROM depute")
    pf = ctx.un("SELECT count(*) FROM depute WHERE date_prise_fonction IS NOT NULL")
    ctx.x("DROP TABLE IF EXISTS _ga_an")
    return {"date_prise_fonction_publiee": (pf, n),
            "suspension_close_par_une_reprise": (repris, nom),
            "suppleant_identifie": (supp, nom),
            "reprise_reliee_au_mandat_suspendu": (reprises_liees, reprises)}
