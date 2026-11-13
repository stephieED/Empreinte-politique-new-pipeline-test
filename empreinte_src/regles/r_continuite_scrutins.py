"""R-CONTINUITE-SCRUTINS : les trous de l'archive des scrutins (doc. 1, 1.5.5, « trous connus »).

Deux sortes de trous, établis par les données seules, jamais par une date écrite dans le code :

- `numeros_manquants` : les scrutins de l'Assemblée d'une législature sont numérotés à partir de 1,
  sans trou. Chaque suite de numéros absents de l'archive, entre 1 et le plus grand numéro lu, est
  un trou, daté par les scrutins qui l'encadrent (XVe : n° 3 781 et 3 782, entre le 25 et le
  26/05/2021 ; archive du 13/11/2026) ;
- `archive_tronquee` : pour une législature close, un acte de dossier cite un scrutin de
  l'Assemblée de cette législature que l'archive n'a pas, à une date postérieure au dernier
  scrutin qu'elle contient : l'archive s'arrête avant la fin de la législature. Le trou va du
  dernier scrutin lu à la fin de la législature ; le nombre de scrutins manquants n'est pas connu
  (XIVe : archive arrêtée au 24/11/2016, n° 1 354 ; des actes de décembre 2016 citent les n° 1 358
  à 1 364). Une législature en cours n'est jamais dite tronquée : l'archive des dossiers peut être
  plus fraîche que celle des scrutins.

Seuls les scrutins de l'Assemblée (`VTANR…`) comptent : le Congrès (`VTCG…`) a sa propre
numérotation, et un scrutin du Sénat cité par un dossier (`VTSN…`) n'est pas attendu dans
l'archive. Un scrutin cité absent **avant** le dernier scrutin lu (XVe : n° 4 689, cité le
26/01/2022, au-delà du dernier numéro de l'archive) n'est pas un trou daté : il est compté à part
(`cites_absents`), sans changer le statut.
"""

NOM = "R-CONTINUITE-SCRUTINS"
VERSION = 1
DEPEND = ("R-NATURE-SCRUTIN", "R-LEGISLATURES")
SORTIES = ("trou_scrutins",)
DESCRIPTION = (
    "Les scrutins de l'Assemblée sont numérotés à la suite dans chaque législature. Un numéro absent "
    "de l'archive publiée par l'Assemblée est un trou de la source, daté par les scrutins qui "
    "l'encadrent. Quand, pour une législature terminée, un dossier cite un scrutin plus récent que "
    "le dernier de l'archive, l'archive s'arrête avant la fin de la législature : les votes de la "
    "fin de la législature manquent, et leur nombre n'est pas connu. Les sections qui comptent des "
    "votes le disent, au lieu de se dire complètes.")

_UID = r"^VTANR5L(\d+)V(\d+)$"


def appliquer(ctx):
    """Applique R-CONTINUITE-SCRUTINS : écrit `trou_scrutins`, les trous de l'archive des scrutins
    (voir la description du module). Rend la couverture, `{nom: (numérateur, dénominateur)}` :
    `legislature_sans_trou_de_scrutins`."""
    cites = "NULL::VARCHAR[]"
    acte = ctx.existe("an_dossiers__acte")
    ctx.ecrire("trou_scrutins", f"""
        WITH s AS (SELECT legislature, numero, left(date, 10) AS d FROM scrutin_nature
                   WHERE scrutin LIKE 'VTANR%' AND numero IS NOT NULL AND legislature IS NOT NULL),
        b AS (SELECT legislature, max(numero) AS m, max(d) AS derniere_date FROM s GROUP BY 1),
        g AS (SELECT legislature, unnest(range(1, m + 1)) AS n FROM b),
        manq AS (SELECT g.legislature, g.n FROM g ANTI JOIN s
                 ON s.legislature = g.legislature AND s.numero = g.n),
        ilots AS (SELECT legislature, n, n - row_number() OVER (PARTITION BY legislature ORDER BY n) AS k
                  FROM manq),
        suites AS (SELECT legislature, min(n) AS a, max(n) AS z, list(n ORDER BY n) AS numeros
                   FROM ilots GROUP BY legislature, k),
        num AS (
            SELECT u.legislature, 'numeros_manquants' AS nature,
                   (SELECT max(d) FROM s WHERE s.legislature = u.legislature AND s.numero < u.a) AS du,
                   (SELECT min(d) FROM s WHERE s.legislature = u.legislature AND s.numero > u.z) AS au,
                   u.numeros, len(u.numeros) AS nb, {cites} AS cites
            FROM suites u),
        cit AS ({
            f'''SELECT DISTINCT v AS scrutin, left(a.date, 10) AS d,
                       TRY_CAST(regexp_extract(v, '{_UID}', 1) AS INTEGER) AS legislature,
                       TRY_CAST(regexp_extract(v, '{_UID}', 2) AS INTEGER) AS numero
                FROM an_dossiers__acte a, unnest(a.scrutins) AS t(v)
                WHERE regexp_matches(v, '{_UID}')
                  AND v NOT IN (SELECT scrutin FROM scrutin_nature)'''
            if acte else
            "SELECT NULL::VARCHAR AS scrutin, NULL::VARCHAR AS d, NULL::INTEGER AS legislature, "
            "NULL::INTEGER AS numero WHERE false"}),
        tronq AS (
            SELECT b.legislature, 'archive_tronquee' AS nature, b.derniere_date AS du,
                   left(l.fin, 10) AS au,
                   list(DISTINCT c.numero ORDER BY c.numero) AS numeros, NULL::BIGINT AS nb,
                   list(DISTINCT c.scrutin ORDER BY c.scrutin) AS cites
            FROM b JOIN legislature l ON l.numero = b.legislature
            JOIN cit c ON c.legislature = b.legislature
            WHERE l.fin IS NOT NULL AND c.d > b.derniere_date AND c.d <= left(l.fin, 10)
            GROUP BY ALL)
        SELECT *, (SELECT count(DISTINCT c.scrutin) FROM cit c
                   WHERE c.legislature = x.legislature) AS cites_absents
        FROM (SELECT * FROM num UNION ALL SELECT * FROM tronq) x
        ORDER BY legislature, du""")
    legs = ctx.un("SELECT count(DISTINCT legislature) FROM scrutin_nature WHERE scrutin LIKE 'VTANR%'")
    avec = ctx.un("SELECT count(DISTINCT legislature) FROM trou_scrutins")
    return {"legislature_sans_trou_de_scrutins": (legs - avec, legs)}


# -- lecture par les composeurs ------------------------------------------------------------------

def trous(ctx, legislature: int | None = None) -> list[dict]:
    """Trous de l'archive des scrutins (d'une législature, ou tous), du plus ancien au plus récent."""
    if not ctx.existe("trou_scrutins"):
        return []
    sql = "SELECT * FROM trou_scrutins" + (" WHERE legislature = ?" if legislature is not None else "")
    cur = ctx.con.execute(sql + " ORDER BY legislature, du", [legislature] if legislature is not None else [])
    noms = [c[0] for c in cur.description]
    return [dict(zip(noms, r)) for r in cur.fetchall()]


def _fr(d) -> str:
    return f"{d[8:10]}/{d[5:7]}/{d[:4]}" if d and len(d) >= 10 else str(d)


def _n(x: int) -> str:
    return f"{x:,}".replace(",", "\u202f")


def phrase(t: dict) -> str:
    """Le trou dit au lecteur, en une phrase (décomptes et dates, jamais d'estimation)."""
    from ..perimetre import nom_legislature
    leg = nom_legislature(t["legislature"])
    nums = list(t["numeros"] or [])
    if t["nature"] == "archive_tronquee":
        cites = ", ".join(_n(n) for n in nums)
        return (f"L'archive des scrutins de la {leg} publiée par l'Assemblée s'arrête au "
                f"{_fr(t['du'])} : les scrutins suivants, jusqu'à la fin de la législature le "
                f"{_fr(t['au'])}, manquent à la source (des dossiers citent les n° {cites}, absents de "
                "l'archive), et leur nombre n'est pas connu.")
    n = ("n° " + _n(nums[0]) if len(nums) == 1 else f"n° {_n(nums[0])} et {_n(nums[1])}" if len(nums) == 2
         else f"n° {_n(nums[0])} à {_n(nums[-1])}")
    return (f"{len(nums)} scrutin{'s' if len(nums) > 1 else ''} de la {leg} "
            f"manque{'nt' if len(nums) > 1 else ''} à la source ({n}, entre le {_fr(t['du'])} et le "
            f"{_fr(t['au'])}).")


def resume(t: dict) -> dict:
    """Le trou tel qu'il est servi dans la couverture d'une section."""
    return {"legislature": t["legislature"], "nature": t["nature"], "du": t["du"], "au": t["au"],
            "numeros": list(t["numeros"] or []), "nb": t["nb"]}


def couvre(t: dict, debut: str | None, fin: str | None) -> bool:
    """Le trou tombe-t-il dans la période [debut, fin] (fin ouverte : None) ?"""
    if debut is not None and (t["au"] or "9999") < debut[:10]:
        return False
    if fin is None:
        return True
    # Archive tronquée : le jour du dernier scrutin lu est encore couvert, le trou commence après.
    return t["du"] < fin[:10] if t["nature"] == "archive_tronquee" else t["du"] <= fin[:10]


def marquer(couv: dict, ts: list[dict]) -> dict:
    """Une section de votes touchée par un trou de la source n'est pas `complet` : `trou_source`,
    avec le trou dit en clair et décrit (doc. 1, 1.5.5). Un statut plus grave (hors périmètre,
    non relu, panne…) est gardé, le trou seulement ajouté à sa description."""
    if not ts:
        return couv
    c = dict(couv)
    if couv.get("statut") in ("complet", "partiel"):
        c.update(statut="trou_source", statut_sans_trou=couv["statut"])
    c.update(detail=((couv.get("detail") or "") + " " + " ".join(phrase(t) for t in ts)).strip(),
             trous_source=[resume(t) for t in ts])
    return c


def date_des_donnees(au: str | None, ts: list[dict]) -> str | None:
    """Date des données : une archive tronquée s'arrête à son dernier scrutin, pas à la fin de la
    législature."""
    fins = [t["du"] for t in ts if t["nature"] == "archive_tronquee"]
    return min([au[:10], *fins]) if fins and au else au
