"""R-ETAPE : l'étape atteinte par un dossier dans chaque législature (doc. 1, 1.5.3 et 1.6 ; cahier
3.1.4 et 4.5, « les textes de la législature »).

L'étape se lit dans ce qui s'est **passé** — un acte daté, au plus tard à la date de référence (la
source publie aussi les réunions et séances à venir) — et dans la **conclusion** des décisions,
jamais dans le code de l'acte : un code qui contient « COM » ne prouve pas l'examen en commission
(la saisine est posée le jour du dépôt). Le code ne sert qu'à savoir dans quelle chambre et à
quelle lecture l'acte a eu lieu. Échelle, de la plus basse à la plus haute :

| étape | preuve |
| --- | --- |
| `depot` | acte de dépôt (initiative, navette, accord international, motion de censure) |
| `examen_commission` | réunion de commission tenue, rapport déposé, décision de commission (CMP comprise) |
| `seance` | discussion en séance publique, décision de séance (conclusion `TSORTF…`, motion) |
| `adopte` | adoption **définitive**, lue dans les conclusions (voir `ADOPTION_DEFINITIVE`) |
| `promulgue` | acte de promulgation |

La législature d'un acte est celle de son identifiant (`L17-…`) : un texte transmis par le
Sénat survit à la dissolution et a une ligne par législature où il a avancé."""

NOM = "R-ETAPE"
VERSION = 1
DEPEND = ()
SORTIES = ("etape_dossier",)
DESCRIPTION = (
    "L'étape atteinte par un texte dans une législature (déposé, examiné en commission, discuté en "
    "séance, adopté définitivement, promulgué) se lit dans ce qui s'est effectivement passé : une "
    "réunion de commission tenue, un rapport déposé, une séance, la conclusion d'une décision. La "
    "simple saisine d'une commission, posée le jour du dépôt, ne vaut pas examen. Les réunions et "
    "séances annoncées pour l'avenir ne comptent pas.")

ADOPTION = "('TSORTF01', 'TSORTF02', 'TSORTF03', 'TSORTF05', 'TSORTF06', 'TSORTF18', 'TSORTF19')"
# Adoption « telle quelle » : sans modification par rapport au texte transmis (TSORTF02 et
# TSORTF05 disent « modifié » / « avec modifications » : la navette continue).
ADOPTION_CONFORME = "('TSORTF01', 'TSORTF03')"
# Lectures de la navette ordinaire, où une adoption sans modification du texte de l'autre
# chambre clôt la navette (pas la nouvelle lecture, où chaque chambre vote son propre texte).
NAVETTE = "('AN1', 'SN1', 'AN2', 'SN2', 'AN3', 'SN3')"
REJET = "('TSORTF07', 'TSORTF24')"
# Procédures à une seule chambre : résolutions (8) et résolutions de l'article 34-1 (22).
UNE_CHAMBRE = "('8', '22')"


def date_ref(ctx) -> str:
    import datetime
    return ctx.date_reference or datetime.date.today().isoformat()


def decisions(ctx) -> str:
    """Décisions de séance datées (au plus tard à la date de référence), avec chambre, lecture et
    issue lue dans la conclusion."""
    return f"""
        SELECT a.dossier, a.uid AS acte, left(a.date, 10) AS date, a.code,
               TRY_CAST(regexp_extract(a.uid, '^L(\\d+)-', 1) AS INTEGER) AS legislature,
               split_part(a.code, '-', 1) AS lecture,
               CASE WHEN a.code LIKE 'AN%' OR a.code LIKE 'CMP-DEBATS-AN%' THEN 'AN'
                    WHEN a.code LIKE 'SN%' OR a.code LIKE 'CMP-DEBATS-SN%' THEN 'SN' END AS chambre,
               a.conclusion_code, a.conclusion_libelle,
               CASE WHEN a.conclusion_code IN {ADOPTION} THEN 'adopte'
                    WHEN a.conclusion_code IN {REJET} THEN 'rejete' END AS issue,
               d.procedure_code, a.prov_url
        FROM an_dossiers__acte a JOIN an_dossiers__dossier d ON d.uid = a.dossier
        WHERE a.type_acte = 'Decision_Type' AND a.conclusion_code LIKE 'TSORT%'
          AND left(a.date, 10) <= '{date_ref(ctx)}'"""


def adoptions_definitives(ctx) -> str:
    """Décisions qui closent la navette par une adoption (une ligne par décision) :
    - lecture définitive (`ANLDEF`) adoptée ;
    - résolution (procédure à une chambre) ou lecture unique (`ANLUNI`) adoptée, ou « considérée
      comme définitive » (`TSORTF19`) ;
    - texte de CMP adopté par les deux chambres (la seconde décision) ;
    - adoption « adopté » ou « adopté sans modification » (`TSORTF01`, `TSORTF03`), en première,
      deuxième ou troisième lecture, d'un texte que l'autre chambre avait adopté à sa dernière
      décision, elle aussi de la navette ordinaire (pas en nouvelle lecture).
    Une révision constitutionnelle (procédure 7) n'est jamais close ici (Congrès ou référendum)."""
    return f"""
        WITH d AS ({decisions(ctx)}),
        x AS (
            SELECT c.*, (SELECT {{'issue': y.issue, 'lecture': y.lecture}} FROM d y
                         WHERE y.dossier = c.dossier AND y.chambre <> c.chambre
                           AND (y.date < c.date OR (y.date = c.date AND y.acte < c.acte))
                         ORDER BY y.date DESC, y.acte DESC LIMIT 1) AS autre
            FROM d c)
        SELECT dossier, acte, date, legislature, lecture, chambre, conclusion_code,
               CASE WHEN lecture = 'ANLDEF' THEN 'lecture_definitive'
                    WHEN procedure_code IN {UNE_CHAMBRE} OR lecture = 'ANLUNI'
                         OR conclusion_code = 'TSORTF19' THEN 'une_seule_chambre'
                    WHEN lecture = 'CMP' THEN 'texte_cmp_adopte_par_les_deux_chambres'
                    ELSE 'adoption_conforme' END AS motif
        FROM x
        WHERE issue = 'adopte' AND coalesce(procedure_code, '') <> '7'
          AND (lecture = 'ANLDEF'
               OR ((procedure_code IN {UNE_CHAMBRE} OR lecture = 'ANLUNI') AND chambre = 'AN')
               OR conclusion_code = 'TSORTF19'
               OR (lecture = 'CMP' AND autre.issue = 'adopte' AND autre.lecture = 'CMP')
               OR (lecture IN {NAVETTE} AND conclusion_code IN {ADOPTION_CONFORME}
                   AND autre.issue = 'adopte' AND autre.lecture IN {NAVETTE}))"""


def appliquer(ctx):
    ref = date_ref(ctx)
    ctx.ecrire("etape_dossier", f"""
        WITH a AS (
            SELECT a.dossier, a.uid AS acte, left(a.date, 10) AS date, a.type_acte, a.conclusion_code,
                   TRY_CAST(regexp_extract(a.uid, '^L(\\d+)-', 1) AS INTEGER) AS legislature
            FROM an_dossiers__acte a
            WHERE a.date IS NOT NULL AND left(a.date, 10) <= '{ref}'),
        preuve AS (
            SELECT dossier, legislature, date, acte,
                   CASE WHEN type_acte = 'Promulgation_Type' THEN 5
                        WHEN type_acte IN ('DiscussionSeancePublique_Type', 'DecisionMotionCensure_Type')
                          OR (type_acte = 'Decision_Type' AND conclusion_code LIKE 'TSORT%') THEN 3
                        WHEN type_acte IN ('DiscussionCommission_Type', 'DepotRapport_Type')
                          OR (type_acte = 'Decision_Type' AND conclusion_code IN ('TMRC01', 'TCCMP01', 'TCCMP02'))
                          THEN 2
                        WHEN type_acte IN ('DepotInitiative_Type', 'DepotInitiativeNavette_Type',
                                           'DepotAccordInternational_Type', 'DepotMotionCensure_Type') THEN 1
                   END AS rang
            FROM a
            UNION ALL
            SELECT dossier, legislature, date, acte, 4 AS rang FROM ({adoptions_definitives(ctx)})),
        par_leg AS (
            SELECT dossier, legislature, max(rang) AS rang,
                   max_by(date, rang * 100000000 + CAST(replace(date, '-', '') AS INTEGER)) AS date_etape,
                   max_by(acte, rang * 100000000 + CAST(replace(date, '-', '') AS INTEGER)) AS acte_etape,
                   bool_or(rang = 3) AS seance, bool_or(rang = 2) AS examen_commission
            FROM preuve WHERE rang IS NOT NULL AND legislature IS NOT NULL GROUP BY 1, 2),
        legs AS (SELECT DISTINCT dossier, legislature FROM a WHERE legislature IS NOT NULL)
        SELECT l.dossier, l.legislature,
               CASE p.rang WHEN 1 THEN 'depot' WHEN 2 THEN 'examen_commission' WHEN 3 THEN 'seance'
                           WHEN 4 THEN 'adopte' WHEN 5 THEN 'promulgue' ELSE 'non_etablie' END AS etape_atteinte,
               p.rang AS rang_etape, p.date_etape, p.acte_etape,
               CASE WHEN p.rang IS NULL THEN 'aucun_acte_d_etape' END AS raison,
               d.procedure_code, d.prov_url AS source_url
        FROM legs l LEFT JOIN par_leg p USING (dossier, legislature)
        JOIN an_dossiers__dossier d ON d.uid = l.dossier""")
    n = ctx.un("SELECT count(*) FROM etape_dossier")
    ok = ctx.un("SELECT count(*) FROM etape_dossier WHERE etape_atteinte <> 'non_etablie'")
    return {"etape_etablie": (ok, n)}
