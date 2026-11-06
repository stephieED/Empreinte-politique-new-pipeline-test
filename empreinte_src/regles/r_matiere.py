"""R-MATIERE : la matière d'un dossier = la commission saisie au fond à l'Assemblée (doc. 1, 1.6 ;
cahier 4.6, « matière d'un texte » ; mesures `an-scrutins-dossiers.md`, 4.3).

Lue dans les actes de saisine au fond (`SaisieComFond_Type`) : la saisine est « à l'Assemblée »
quand son étape est une étape de l'Assemblée (code `AN…`) **et** que l'organe saisi est une
commission de l'Assemblée (commission permanente `COMPER` ou spéciale `CNPS`). Jamais devinée
depuis l'intitulé.

- une seule commission de l'Assemblée saisie au fond → `assemblee` ;
- aucune saisine au fond à l'Assemblée, mais une au Sénat (code `SN…`) → `senat_seulement`,
  « Saisi au Sénat seulement » (décision du 04/11/2026, doc. 5, Q19) ;
- sinon → `non_etablie`, avec sa raison (`aucune_saisine_au_fond`, `plusieurs_commissions`, ou
  `saisine_incoherente` : étape du Sénat mais commission de l'Assemblée, ou l'inverse)."""

NOM = "R-MATIERE"
VERSION = 1
DEPEND = ()
SORTIES = ("matiere",)
DESCRIPTION = (
    "La matière d'un texte est la commission de l'Assemblée saisie au fond, lue dans le dossier "
    "législatif ; elle n'est jamais devinée depuis le titre. Un texte saisi au fond au seul Sénat "
    "est dit « saisi au Sénat seulement ». Sans saisine au fond, ou si plusieurs commissions de "
    "l'Assemblée ont été saisies au fond, la matière n'est pas établie.")

COMMISSIONS_AN = "('COMPER', 'CNPS')"


def appliquer(ctx):
    ctx.ecrire("matiere", f"""
        WITH s AS (
            SELECT a.dossier, a.uid AS acte, a.code, a.organe, left(a.date, 10) AS date,
                   o.type_organe, coalesce(o.libelle, o.libelle_abrege) AS libelle_organe,
                   o.prov_url AS organe_url,
                   a.code LIKE 'AN%' AS etape_an, a.code LIKE 'SN%' AS etape_sn,
                   o.type_organe IN {COMMISSIONS_AN} AS commission_an
            FROM an_dossiers__acte a LEFT JOIN an_acteurs__organe o ON o.uid = a.organe
            WHERE a.type_acte = 'SaisieComFond_Type'),
        par_dossier AS (
            SELECT dossier,
                   list(DISTINCT organe) FILTER (WHERE etape_an AND commission_an) AS an,
                   any_value(libelle_organe) FILTER (WHERE etape_an AND commission_an) AS libelle_an,
                   min(date) FILTER (WHERE etape_an AND commission_an) AS date_an,
                   list(DISTINCT organe) FILTER (WHERE etape_sn AND NOT coalesce(commission_an, false)) AS sn,
                   count(*) FILTER (WHERE (etape_an AND NOT coalesce(commission_an, false))
                                     OR (etape_sn AND coalesce(commission_an, false))) AS incoherentes
            FROM s GROUP BY 1)
        SELECT d.uid AS dossier,
               CASE WHEN len(p.an) = 1 THEN p.an[1] END AS commission,
               CASE WHEN len(p.an) = 1 THEN 'assemblee'
                    WHEN coalesce(len(p.an), 0) = 0 AND len(p.sn) >= 1 AND p.incoherentes = 0
                         THEN 'senat_seulement'
                    ELSE 'non_etablie' END AS statut,
               CASE WHEN len(p.an) = 1 THEN p.libelle_an
                    WHEN coalesce(len(p.an), 0) = 0 AND len(p.sn) >= 1 AND p.incoherentes = 0
                         THEN 'Saisi au Sénat seulement'
                    ELSE 'Matière non établie' END AS libelle,
               CASE WHEN len(p.an) > 1 THEN 'plusieurs_commissions'
                    WHEN coalesce(len(p.an), 0) = 0 AND coalesce(p.incoherentes, 0) > 0 THEN 'saisine_incoherente'
                    WHEN coalesce(len(p.an), 0) = 0 AND coalesce(len(p.sn), 0) = 0 THEN 'aucune_saisine_au_fond'
               END AS raison,
               CASE WHEN len(p.an) = 1 THEN p.date_an END AS date_saisine,
               CASE WHEN coalesce(len(p.an), 0) = 0 THEN p.sn END AS commissions_senat,
               d.legislature, d.procedure_libelle, d.prov_url AS source_url
        FROM an_dossiers__dossier d LEFT JOIN par_dossier p ON p.dossier = d.uid""")
    n = ctx.un("SELECT count(*) FROM matiere")
    an = ctx.un("SELECT count(*) FROM matiere WHERE statut = 'assemblee'")
    sn = ctx.un("SELECT count(*) FROM matiere WHERE statut = 'senat_seulement'")
    return {"matiere_assemblee": (an, n), "senat_seulement": (sn, n),
            "matiere_assemblee_ou_senat": (an + sn, n)}
