"""R-ORDRE-DU-JOUR : les points d'ordre du jour des séances publiques de l'Assemblée (cahier
3.1.7 et 4.5, « À l'ordre du jour »).

L'agenda mélange séances de l'Assemblée, séances du Sénat et réunions de commission : seules
les réunions de type séance (`seance_type`) dont l'organe est l'Assemblée d'une législature
(`legislature.organe`) sont gardées. Chaque point garde le statut publié de sa séance
(`confirmee`, `supprimee`, sinon `non_etabli`) et le sien. Le dossier est celui que l'agenda
cite pour le point ; un point qui n'en cite aucun est déclaré `non_lie` (la plupart des points
de questions, débats et déclarations n'en citent pas) ; jamais deviné par le titre. La
commission saisie au fond vient de `matiere` (R-MATIERE) quand cette sortie existe.
"""

NOM = "R-ORDRE-DU-JOUR"
VERSION = 1
# `matiere` (R-MATIERE, groupe B) est lue si elle existe ; elle n'est pas une dépendance déclarée
# pour que la règle tourne sans elle (R-MATIERE passe avant : ordre alphabétique de `ordonner`).
DEPEND = ("R-LEGISLATURES",)
DEPEND_FACULTATIF = ("R-MATIERE",)   # commission du dossier, si la règle existe
SORTIES = ("ordre_du_jour",)
DESCRIPTION = (
    "L'ordre du jour d'une législature est celui des séances publiques de l'Assemblée publiées "
    "dans son agenda (ni le Sénat, ni les commissions). Chaque séance garde son statut publié "
    "(confirmée ou supprimée) et chaque point le dossier législatif que l'agenda lui associe ; "
    "un point sans dossier cité est montré comme non lié, sans deviner. La commission est la "
    "commission saisie au fond du dossier.")

URL = "https://www.assemblee-nationale.fr/dyn/"


def appliquer(ctx):
    if ctx.existe("matiere"):
        jointure = "LEFT JOIN (SELECT dossier, any_value(commission) AS commission, any_value(libelle) AS libelle, any_value(statut) AS statut FROM matiere GROUP BY 1) m ON m.dossier = b.dossier"
        cols = "m.commission, m.libelle AS commission_libelle, m.statut AS matiere_statut"
    else:
        jointure = ""
        cols = "NULL::VARCHAR AS commission, NULL::VARCHAR AS commission_libelle, 'matiere_absente'::VARCHAR AS matiere_statut"
    ctx.ecrire("ordre_du_jour", f"""
        WITH b AS (
            SELECT coalesce(left(r.date_seance, 10), left(r.debut, 10)) AS date, r.uid AS reunion,
                   p.rang, p.objet, l.numero AS legislature,
                   CASE WHEN len(p.dossiers) = 1 THEN p.dossiers[1] END AS dossier,
                   coalesce(p.dossiers, []) AS dossiers,
                   CASE r.etat WHEN 'Confirmé' THEN 'confirmee' WHEN 'Supprimé' THEN 'supprimee'
                        ELSE 'non_etabli' END AS statut_seance,
                   CASE p.etat WHEN 'Confirmé' THEN 'confirme' WHEN 'Supprimé' THEN 'supprime'
                        ELSE 'non_etabli' END AS statut_point,
                   r.etat AS etat_seance_source, p.etat AS etat_point_source,
                   p.uid AS point, p.type_point, p.nature_travaux, r.compte_rendu,
                   CASE WHEN r.compte_rendu IS NOT NULL
                        THEN '{URL}' || CAST(l.numero AS VARCHAR) || '/comptes-rendus/seance/' || r.compte_rendu
                   END AS source_url
            FROM an_agenda__reunion r
            JOIN legislature l ON l.organe = r.organe
            LEFT JOIN an_agenda__point_odj p ON p.reunion = r.uid
            WHERE r.type_reunion = 'seance_type')
        SELECT b.date, b.reunion, b.rang, b.objet, b.dossier, b.statut_seance,
               b.statut_point,
               CASE WHEN b.rang IS NULL THEN 'sans_point' WHEN len(b.dossiers) = 0 THEN 'non_lie'
                    WHEN len(b.dossiers) = 1 THEN 'lie' ELSE 'plusieurs_dossiers' END AS lien_dossier,
               b.dossiers, {cols}, b.legislature, b.point, b.type_point, b.nature_travaux,
               b.etat_seance_source, b.etat_point_source, b.compte_rendu, b.source_url
        FROM b {jointure}
        ORDER BY b.date, b.reunion, b.rang""")
    # Couverture sur les points confirmés de séances confirmées (les points supprimés ne citent
    # jamais de dossier dans l'agenda XVIIe).
    t = ctx.x("""SELECT count(*) FILTER (lien_dossier IN ('lie', 'plusieurs_dossiers')), count(*),
                        count(*) FILTER (dossier IS NOT NULL AND commission IS NOT NULL),
                        count(*) FILTER (dossier IS NOT NULL)
                 FROM ordre_du_jour
                 WHERE rang IS NOT NULL AND statut_seance = 'confirmee' AND statut_point = 'confirme'""")[0]
    n, publie = ctx.x("""SELECT count(*), count(*) FILTER (statut_seance <> 'non_etabli')
                         FROM (SELECT DISTINCT reunion, statut_seance FROM ordre_du_jour)""")[0]
    couv = {"point_confirme_lie_a_un_dossier": (t[0], t[1]), "statut_de_seance_publie": (publie, n)}
    if ctx.existe("matiere"):
        couv["commission_connue"] = (t[2], t[3])
    return couv
