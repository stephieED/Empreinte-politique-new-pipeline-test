# Extrait du lecteur `wp_candidatures` (Wikipédia)

`wp_candidatures_section1.json` (91 Ko) : réponse de l'API MediaWiki
`https://fr.wikipedia.org/w/api.php?action=parse&page=Candidatures_à_l'élection_présidentielle_française_de_2027&section=1&prop=wikitext|links&format=json&formatversion=2`,
téléchargée le 04/11/2026 (`travail/sources/wikipedia/section1.json`), recopiée à l'octet près.
Révision 240980797 (03/11/2026 12:05 UTC). Contenu de Wikipédia, auteurs : contributeurs de
l'article (historique de la page) ; licence CC BY-SA 4.0.

Ce qu'il couvre : la section « Candidats déclarés » seule (29 candidats), avec les formes de
nom `! {{TriNom|P|N}}`, `!{{TriNom|P|N}}`, `{{TriNom|P|N|nolink=oui}}` (5 cas), `![[Titre]]`
(2 cas) ; les formes de date `{{date|8 décembre 2025}}`, `{{Date|…}}`, `{{date|23/08/2026}}`,
`{{date|2|10|2026}}`, `{{Date|01|04|2025}}`, date en clair ; la liste `links` (`exists`).

Le test `test_page_entiere_avec_candidatures_retirees_forme_1` porte en plus, dans le code du
test, deux lignes de la section « Candidatures retirées » **recopiées de la révision 241073157**
(réponse rangée dans l'entrepôt complet du 06/11/2026, absente de `travail/sources/`), leurs
références raccourcies à leur seule adresse. Les formes inconnues (nom en clair, autre modèle,
TriNom incomplet) sont écrites pour le test : elles n'ont pas été rencontrées.
