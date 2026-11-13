"""R-NATURE-SCRUTIN : la nature d'un scrutin de l'Assemblée (doc. 1, 1.6 ; cahier 4.6, « vote sur
l'ensemble d'un texte » ; mesures `an-scrutins-dossiers.md`, 3.1 et 3.2).

D'abord le **code** du type (`MOC` = motion de censure, `SPS` = solennel) : le libellé ne compte
pas (il dit « scrutin public solennel » pour une motion de censure en XVe et XVIe). Ensuite
l'intitulé, normalisé (minuscules, accents et apostrophes retirés, espaces resserrés, « sur »
initial ôté), comparé à des motifs écrits ici et testés, dans l'ordre :

| motif (début de l'intitulé normalisé) | nature | détail |
| --- | --- | --- |
| code `MOC`, ou « la motion de censure » | `motion_censure` | |
| « [l'ensemble de] la première/deuxième… partie » | `partie_de_texte` | jamais une dernière lecture (doc. 5, Q20) |
| « l'ensemble de la proposition / du projet / du texte » | `ensemble` | `ensemble` |
| « la proposition de loi / de résolution », « le projet de loi » | `ensemble` | `ensemble_sans_le_mot` (résolutions : doc. 5, Q20) |
| « l'amendement », « le sous-amendement », « les amendements » (coquilles tolérées) | `amendement` | |
| « l'article », « les articles » (« aticle » toléré) | `article` | `article_unique` à part |
| « la motion de rejet préalable » | `motion_rejet` | |
| « la motion … » (autre) | `autre` | `motion_procedure` |
| « la déclaration » | `declaration` | |
| « la demande de suspension / de seconde délibération », « la proposition du Gouvernement de prolonger » | `autre` | |
| tout autre intitulé | `non_etablie` | raison `intitule_hors_motifs` |

Les scrutins du Congrès (`VTCG…`) sont hors périmètre (cahier 3.1.2) : écartés et comptés.
La lecture (première, deuxième, nouvelle, CMP, définitive) est lue dans la parenthèse finale de
l'intitulé ; absente, elle reste nulle."""

NOM = "R-NATURE-SCRUTIN"
VERSION = 1
DEPEND = ()
SORTIES = ("scrutin_nature",)
DESCRIPTION = (
    "La nature d'un vote (ensemble d'un texte, partie d'un texte financier, article, amendement, "
    "motion, déclaration) n'est pas publiée par l'Assemblée : elle se lit dans l'intitulé du "
    "scrutin. Le type officiel (motion de censure, scrutin solennel) est lu dans son code, jamais "
    "dans son libellé. L'intitulé est comparé à une liste de motifs publiée ; les coquilles connues "
    "(« amenedement », « aticle ») sont tolérées. Un vote sur une partie d'une loi de finances ou de "
    "financement de la sécurité sociale n'est pas un vote sur l'ensemble du texte. Un vote sur une "
    "proposition de résolution est un vote sur l'ensemble d'un texte qui n'est pas une loi "
    "(décision provisoire). Un intitulé qui ne correspond à aucun motif reste « non établi » : le "
    "scrutin ne compte alors pas parmi les votes sur l'ensemble.")

# Intitulé normalisé : minuscules, sans accents, apostrophes et espaces insécables -> espace.
NORME = r"""trim(regexp_replace(regexp_replace(
    regexp_replace(strip_accents(lower(coalesce(titre, ''))), '[’''`´\x{00A0}]', ' ', 'g'),
    '\s+', ' ', 'g'), '^\s*sur\s+', ''))"""

ORDINAUX = "(premiere|deuxieme|troisieme|quatrieme)"

# Motifs, dans l'ordre : (motif sur l'intitulé normalisé, nature, détail).
MOTIFS = [
    (r"^la motion de censure\b", "motion_censure", "intitule"),
    (rf"^(l ensemble (de |du |d )+)?(la )?{ORDINAUX}( et {ORDINAUX})? parties?\b",
     "partie_de_texte", "partie"),
    (r"^l ensemble (de |du |des |d )+(la |l )?(proposition|projet|texte)\b", "ensemble", "ensemble"),
    (r"^(la proposition de (loi|resolution)|le projet de loi)\b", "ensemble", "ensemble_sans_le_mot"),
    (r"^(l |le |les |la )(sous ?-? ?)?am[a-z]{0,3}d[a-z]{0,3}m[a-z]{0,3}nts?\b", "amendement", None),
    (r"^l a?r?ticle unique\b", "article", "article_unique"),
    (r"^(l |les )a?r?ticles?\b", "article", None),
    (r"^la motion de rejet p[a-z]{0,3}alable\b", "motion_rejet", None),
    (r"^la motion\b", "autre", "motion_procedure"),
    (r"^la declaration\b", "declaration", None),
    (r"^la demande de suspension\b", "autre", "suspension_de_seance"),
    (r"^la demande de seconde deliberation\b", "autre", "seconde_deliberation"),
    (r"^la proposition du gouvernement de prolonger\b", "autre", "prolongation_de_seance"),
]

# Lecture, lue dans la parenthèse finale de l'intitulé normalisé.
LECTURES = [
    (r"\(\s*premiere lecture\s*\)", "premiere"),
    (r"\(\s*deuxieme lecture\s*\)", "deuxieme"),
    (r"\(\s*troisieme lecture\s*\)", "troisieme"),
    (r"\(\s*nouvelle lecture\s*\)", "nouvelle"),
    (r"\(\s*lecture definitive\s*\)", "definitive"),
    (r"\(\s*texte de la commission mixte paritaire\s*\)", "cmp"),
]


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _cas(colonne_sortie: str) -> str:
    """CASE … sur l'intitulé normalisé `n`, après le code du type."""
    branches = ["WHEN code_type = 'MOC' THEN " + (_q("motion_censure") if colonne_sortie == "nature"
                                                  else _q("code_MOC"))]
    for motif, nature, detail in MOTIFS:
        val = nature if colonne_sortie == "nature" else detail
        branches.append(f"WHEN regexp_matches(n, {_q(motif)}) THEN "
                        + (_q(val) if val is not None else "NULL"))
    defaut = _q("non_etablie") if colonne_sortie == "nature" else "NULL"
    return "CASE " + " ".join(branches) + f" ELSE {defaut} END"


def _lecture() -> str:
    return ("CASE " + " ".join(f"WHEN regexp_matches(n, {_q(m)}) THEN {_q(v)}" for m, v in LECTURES)
            + " ELSE NULL END")


def appliquer(ctx):
    """Applique R-NATURE-SCRUTIN : écrit `scrutin_nature`, la nature et la lecture de chaque
    scrutin de l'Assemblée (voir la description du module). Rend la couverture,
    `{nom: (numérateur, dénominateur)}` : `nature_etablie`, `lecture_etablie`."""
    ctx.ecrire("scrutin_nature", f"""
        WITH s AS (
            SELECT *, {NORME} AS n FROM an_scrutins__scrutin WHERE uid NOT LIKE 'VTCG%')
        SELECT uid AS scrutin, legislature, numero, date, seance, code_type AS type_code,
               titre, n AS titre_normalise,
               {_cas("nature")} AS nature, {_cas("detail")} AS detail,
               CASE WHEN titre IS NULL THEN 'intitule_absent'
                    WHEN ({_cas("nature")}) = 'non_etablie' THEN 'intitule_hors_motifs' END AS raison,
               {_lecture()} AS lecture,
               CASE sort_code WHEN 'adopté' THEN 'adopte' WHEN 'rejeté' THEN 'rejete' END AS sort,
               code_type IN ('SPS', 'SSG') AS solennel,
               code_type = 'MOC' AS motion_censure,
               dossier_ref, prov_url AS source_url
        FROM s""")
    n = ctx.un("SELECT count(*) FROM scrutin_nature")
    etablie = ctx.un("SELECT count(*) FROM scrutin_nature WHERE nature <> 'non_etablie'")
    lecture = ctx.un("SELECT count(*) FROM scrutin_nature WHERE lecture IS NOT NULL")
    return {"nature_etablie": (etablie, n), "lecture_etablie": (lecture, n)}
