# Démonstration en entretien — mode d'emploi

Ce document ne présente pas l'outil : il décrit **comment vous en parlez**. Objectif : que le dépôt
devienne un support de conversation, pas une simple preuve d'existence.

## 1. Votre positionnement, en une phrase

> « L'outil visé chez vous était NeoLoad, qui est payant. J'ai voulu comprendre les concepts
> indépendamment de l'outil : j'ai donc reproduit le même scénario dans deux outils open source, un
> classique (JMeter) et un orienté DevOps (Locust), avec une cible mock pour que ce soit reproductible
> hors ligne. »

Cette phrase fait trois choses : elle **explique l'écart** avec NeoLoad, elle montre que vous avez
cherché les principes plutôt que la recette, et elle annonce que la démo fonctionne.

Ne dites jamais « je maîtrise JMeter ». Dites « je sais le mettre en œuvre sur un scénario réaliste et
expliquer ce qu'il mesure ». C'est vérifiable, donc crédible.

## 2. Checklist de préparation (à faire la veille, hors entretien)

- [ ] **Option Docker (recommandée si l'outillage manque)** : `docker compose up -d mock` puis
      `docker compose run --rm jmeter` et `docker compose run --rm locust` — vérifié, sorties dans
      `resultats/`. C'est la seule voie qui ne demande aucune installation Java/Python.
- [ ] `java -version` renvoie une version 11+ ; `jmeter -v` répond **ou** l'option Docker ci-dessus.
- [ ] `python --version` ; si Python ≥ 3.14, créer un venv 3.11/3.12 avant d'installer Locust
      (`python -m venv .venv` puis `.venv\Scripts\pip install locust`).
- [ ] `python mock_api/mock_server.py` démarre sur le port 8080.
- [ ] Un `jmeter -n ...` complet a **déjà** produit un `rapport_html`.
- [ ] Un `locust --headless` complet a **déjà** produit des CSV.
- [ ] Vous avez un `rapport_html/index.html` et un `resultats_stats.csv` **pré-générés** dans le
      dépôt ou sur le bureau (secours si le réseau/l'outil flanche en direct).
- [ ] Le dépôt GitHub est public et vous savez montrer l'URL depuis un navigateur.

## 3. Le parcours de démonstration (12 minutes)

Ordre choisi : le **concept** d'abord, l'**outil** ensuite, la **preuve** à la fin.

| Minute | Ce que vous montrez | Ce que vous dites |
|---|---|---|
| 0–1 | `README.md` | « Un POC comparatif d'un scénario API réaliste : login, extraction de jeton, route protégée. » |
| 1–3 | `jmeter/plan_de_test.jmx` (arborescence) | « Thread Group de 50 utilisateurs, ramp-up 10 s, extraction JSONPath du token, header `Bearer`, assertion 200. » |
| 3–5 | Les 6 propriétés `-J` | « La cible et la charge sont externalisées : aucun fichier modifié entre local, intégration et prod. » |
| 5–7 | `locust/locustfile.py` | « Le même scénario en 30 lignes : `on_start` = la corrélation, `@task(3)` = le profil d'usage 75/25. » |
| 7–9 | `mock_api/mock_server.py` + `--latency-ms 400` | « J'ai écrit une cible mock : la démo ne dépend ni du wifi ni d'un service tiers. » |
| 9–11 | Deux CSV côte à côte (60 ms vs 400 ms) | « Même charge, même scénario : seul le p95 bouge. C'est ça, mesurer un impact. » |
| 11–12 | `.github/workflows/performance.yml` | « Cible mock démarrée dans la CI, deux tests en headless, seuils bloquants sur le p95, rapports publiés — et une release créée automatiquement sur un tag. » |

Le point le plus fort est la **minute 9–11** : un avant/après chiffré fait plus d'effet que dix
fichiers. Préparez-le, c'est le seul moment où l'on vous croit sur parole.

## 4. Les 10 questions probables

### 1. Test de charge, stress, spike, endurance : quelle différence ?

Le **type de test** décrit l'intention, pas l'outil.

| Type | Objectif | Profil |
|---|---|---|
| Charge | Vérifier le comportement à la charge attendue | Montée progressive jusqu'à N utilisateurs |
| Stress | Trouver le point de rupture | On augmente jusqu'à ce que ça casse |
| Spike | Résister à un pic brutal | +300 utilisateurs en 10 s |
| Endurance / soak | Détecter les fuites mémoire | Charge normale pendant des heures |

> « Dans mon POC, c'est un test de charge : 50 utilisateurs, rampe de 10 s, palier de 60 s. Le même
> scénario se transforme en test de stress en changeant seulement `-Jthreads` et `-Jduration`. »

### 2. Pourquoi le p95 plutôt que la moyenne ?

La moyenne cache les mauvaises expériences : 100 utilisateurs à 100 ms et 5 à 5 s donnent une moyenne
flatteuse de ~330 ms, alors que 5 % des utilisateurs attendent 5 s.

> « Je pilote sur le p95 : 95 % des utilisateurs sont sous ce seuil. La moyenne sert à expliquer, le
> p95 à décider. »

### 3. À quoi servent le ramp-up et le think time ?

- **Ramp-up** : évite de créer un pic artificiel au démarrage et laisse caches/réseau se stabiliser.
- **Think time** (`wait_time` en Locust) : simule le temps de lecture humain ; sans lui, vous mesurez
  la vitesse du générateur, pas la capacité du serveur.

> « Un test sans think time est un test de résistance à la rafale, pas une simulation d'usage. »

### 4. Qu'est-ce que la corrélation, et pourquoi c'est indispensable ici ?

Une valeur produite par le serveur (jeton, id de session, CSRF) doit être **extraite** de la réponse
et **réinjectée** dans les requêtes suivantes. Sans elle, chaque requête protégée renvoie 401.

> « JMeter : JSON Extractor sur `$.access_token` puis `${access_token}` dans le header. Locust :
> stockage dans `self.token` à l'intérieur de `on_start`, propre à chaque utilisateur virtuel. »

### 5. Comment savoir si le goulot est l'application ou le générateur ?

Trois signaux :

1. Le générateur sature son **CPU** (le vôtre, pas celui du serveur) ;
2. Le débit **plafonne** alors que la latence continue de monter linéairement ;
3. Les **erreurs réseau** apparaissent côté client (ports épuisés, timeouts).

> « Je surveille d'abord la machine qui génère : si elle est à 100 % CPU, les chiffres ne décrivent
> plus le serveur. La solution est alors de distribuer la charge (JMeter contrôleur/worker, Locust
> `--master`/`--worker`). »

**L'anecdote à raconter** (elle est vraie, elle est dans le dépôt) : sur mon premier run Locust,
`POST /login` affichait un p90 à 1 000 ms pour une médiane à 39 ms. Des latences rondes, uniquement
sur la première requête de chaque utilisateur. Ce n'était pas l'application : c'était la file
d'attente d'acceptation de la cible mock (`request_queue_size = 5` par défaut en Python), qui
débordait quand 50 utilisateurs se connectaient dans la même seconde — `SYN` perdu, renvoi après 1 s.
Après correction, p90 à 80 ms. La règle à énoncer : **une latence anormalement ronde est un artefact
de mesure, pas un comportement applicatif**.

### 6. JMeter, Locust, NeoLoad : comment choisir ?

| Critère | JMeter | Locust | NeoLoad |
|---|---|---|---|
| Approche | Interface + XML | Code Python | Interface + scripting |
| Protocoles | Très large (JDBC, JMS, SOAP) | HTTP(S) surtout | Très large |
| CI/CD | Bon (headless) | Excellent (natif) | Bon (payant) |
| Coût | Gratuit | Gratuit | Licence |
| Profil d'équipe | QA classique | DevOps / Python | Grande entreprise, support éditeur |

> « Je choisis JMeter si l'équipe est QA ou si le protocole n'est pas HTTP. Locust si les tests doivent
> vivre dans le dépôt et dans la CI. NeoLoad se justifie par son support éditeur et sa couverture, pas
> par une capacité technique unique. »

### 7. Comment fixez-vous l'objectif d'un test ?

Trois questions : **combien** d'utilisateurs simultanés, **quel** parcours, **quel** seuil acceptable.
Puis un critère binaire, sinon le test n'est pas interprétable.

> « Exemple : 200 utilisateurs, 70 % consultation / 30 % écriture, p95 < 800 ms et taux d'erreur
> < 1 %. En dessous, le test est vert ; au-dessus, il est rouge — ce qui permet de l'utiliser comme
> garde-fou en CI. »

### 8. Comment générer 1 000 ou 10 000 utilisateurs ?

Un poste ne suffit pas : chaque utilisateur virtuel consomme CPU et mémoire. On répartit sur
plusieurs machines : JMeter en mode contrôleur/worker (`-R`, `jmeter-server`) ou Locust en
`--master` / `--worker`, avec un point de pilotage unique.

> « À noter : dans mon POC, 50 utilisateurs tiennent sur un poste ; au-delà de quelques centaines, il
> faut passer en distribué, sinon on mesure la machine de test. »

### 9. Comment intégrer ça dans une CI sans rendre les pipelines instables ?

- Cible **dédiée** et isolée (jamais la production) ;
- charge et durée **courtes** en CI (fumée), complètes la nuit ;
- **seuils bloquants** explicites plutôt qu'un `|| true` ;
- artefacts (rapports HTML/CSV) publiés pour comparer d'une exécution à l'autre.

> « Mon workflow démarre la cible mock, exécute les deux scénarios, et **échoue** si le p95 dépasse
> 500 ms ou si une seule requête échoue — c'est `ci/check_thresholds.py`. Les rapports sont publiés en
> artefacts à chaque exécution, même en cas d'échec, et un tag `v*` crée une release avec les rapports
> en pièce jointe. »

### 10. Que livrez-vous au client à la fin d'un test ?

Trois choses : un **rapport** (débit, p95/p99, taux d'erreur, courbes), une **conclusion** (le système
tient-il l'objectif ?), et une **recommandation** (goulot identifié, marge restante, prochaine étape).

> « Le chiffre seul ne sert à rien : ce qui compte est l'écart à l'objectif et ce qu'on en fait. »

### Bonus — « Avez-vous déjà fait du test de performance en production ? »

Répondez **non**, clairement, puis enchaînez : « Je sais en revanche qu'on ne teste pas en production
sans précaution : environnement isolé, données anonymisées, trafic synthétique étiqueté, plan de
rollback. » L'honnêteté sur ce point rassure plus qu'une expérience invérifiable.

## 5. Ce qu'il ne faut pas dire

- ❌ « Je maîtrise NeoLoad » → ✅ « J'ai travaillé les concepts sur des équivalents open source. »
- ❌ « 50 utilisateurs, c'est représentatif d'un site e-commerce » → ✅ « C'est un palier de
  démonstration ; le dimensionnement se déduit du trafic réel. »
- ❌ « Ça marche, donc c'est performant » → sans objectif chiffré, aucune conclusion n'est possible.
- ❌ Inventer un chiffre de production. Un ordre de grandeur faux se repère en deux questions.

## 6. Si la démo plante — le plan B

1. **Ne déboguez pas en direct** plus de 30 secondes. Dites : « Je vous montre le rapport généré hier
   sur le même scénario », et ouvrez le HTML/CSV pré-généré.
2. Expliquez la cause probable en une phrase (port occupé, Java absent, wifi) : c'est déjà une preuve
   de compréhension.
3. Basculez sur le code : `on_start`, `@task(3)`, les propriétés `-J`. Le code se lit sans exécuter.
4. Proposez : « Je vous envoie la sortie complète après l'entretien. » Puis **faites-le**.
5. **Filet de sécurité Docker** : si Java/JMeter/Locust manquent sur votre poste,
   `docker compose up -d mock` puis `docker compose run --rm jmeter` reproduit la démo complète en
   une minute, sans rien installer. Attention : le premier build télécharge ~1 Go d'images — faites-le
   la veille, pas en salle d'entretien.

## 7. Glossaire minimum à savoir employer

| Terme | Définition courte |
|---|---|
| Utilisateur virtuel (VU) | Thread qui rejoue un parcours |
| Ramp-up | Temps de montée jusqu'au palier |
| Think time | Temps de réflexion entre deux actions |
| Palier / steady state | Phase à charge constante, celle qu'on mesure |
| Throughput | Requêtes traitées par seconde |
| Percentile (p95) | Seuil sous lequel se trouvent 95 % des temps de réponse |
| Corrélation | Extraction/réinjection d'une valeur produite par le serveur |
| Saturation | Point où la ressource (CPU, pool DB, I/O) devient le facteur limitant |

## 8. Après l'entretien

- Envoyez le lien du dépôt avec la phrase d'accroche de la section 1, pas juste l'URL.
- Ajoutez au dépôt ce que l'entretien a révélé comme manque (un seuil bloquant, un CSV d'utilisateurs,
  un test distribué). C'est la meilleure preuve de progression : le dépôt évolue après l'échange.
