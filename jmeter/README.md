# Plan de test JMeter — POC API

Ce dossier contient le scénario JMeter équivalent du POC : un utilisateur virtuel se connecte,
récupère un jeton et appelle une route protégée.

## Fichier

| Fichier | Rôle |
|---|---|
| `plan_de_test.jmx` | Plan de test XML (Test Plan JMeter 5.6.3) |

## Cible : paramétrable, `api.example.com` par défaut

Le plan pointe par défaut sur `https://api.example.com`, une URL de démonstration **qui n'existe
pas**. La cible n'est pas figée dans le fichier : elle est lue dans des **propriétés JMeter**
(`${__P(nom, défaut)}`), donc surchargeable en ligne de commande avec `-J`.

Endpoints attendus par le plan :

| Endpoint | Méthode | Attendu |
|---|---|---|
| `/login` | POST | `200` + corps JSON `{"access_token": "..."}` |
| `/protected` | GET + `Authorization: Bearer <token>` | `200` |
| `/health` | GET | `200` |

## Structure du plan

| Nœud | Type | Rôle |
|---|---|---|
| `TestPlan` | Test Plan | Conteneur, variables utilisateur |
| `Utilisateurs Virtuels` | Thread Group | 50 threads, ramp-up 10 s, scheduler 60 s |
| `Boucle` | Loop Controller | 10 itérations (ignorées, le scheduler est actif) |
| `POST /login` | HTTP Sampler | Authentification, corps `user=testuser&pass=testpass` |
| `Extraction Token` | JSON Post Processor | Corrélation : `$.access_token` → variable `${access_token}` |
| `GET /protected` | HTTP Sampler | Route protégée |
| `En-têtes HTTP` | Header Manager | `Authorization: Bearer ${access_token}` — portée limitée au sampler parent |
| `Assertion Status 200` | Response Assertion | Le test échoue si le code ≠ 200 |

**La corrélation est le cœur du plan** : la réponse du login est parsée par JSONPath, le jeton est
stocké dans une variable JMeter, puis réinjecté dans l'en-tête de la requête suivante. C'est ce
mécanisme qui distingue un test de charge d'une simple rafale de requêtes.

## Paramétrage de la charge (propriétés `-J`)

| Propriété | Défaut | Ligne du plan |
|---|---|---|
| `host` | `api.example.com` | `HTTPSampler.domain` |
| `port` | `443` | `HTTPSampler.port` |
| `protocol` | `https` | `HTTPSampler.protocol` |
| `threads` | `50` | `ThreadGroup.num_threads` |
| `ramp` | `10` | `ThreadGroup.ramp_time` |
| `duration` | `60` | `ThreadGroup.duration` |

```bash
jmeter -n -t jmeter/plan_de_test.jmx -Jhost=dummyjson.com -Jthreads=100 -Jduration=120
```

C'est le point à montrer en entretien : **on ne modifie pas le scénario pour changer de cible ou de
charge**, on passe des paramètres. Le même `.jmx` sert en local, en intégration et en préproduction.

## Lancement en mode graphique (pour découvrir l'outil)

```bash
jmeter                       # ouvre l'interface
```
Puis `File > Open` → `jmeter/plan_de_test.jmx`. Pour ouvrir directement avec des propriétés :

```bash
jmeter -Jhost=127.0.0.1 -Jport=8080 -Jprotocol=http -t jmeter/plan_de_test.jmx
```

Le mode GUI sert à **construire et déboguer**. Il ne faut jamais l'utiliser pour mesurer : l'IHM
consomme de la ressource et fausse les résultats. C'est un point à savoir expliquer en entretien.

## Lancement headless (le seul mode valable pour mesurer)

Depuis la racine du dépôt :

```bash
jmeter -n -t jmeter/plan_de_test.jmx -l resultats.jtl -e -o rapport_html
```

| Option | Effet |
|---|---|
| `-n` | Mode non graphique |
| `-t` | Fichier de plan de test |
| `-Jcle=valeur` | Surcharge une propriété du plan |
| `-l` | Fichier de résultats bruts (`.jtl`) |
| `-e -o` | Génère le rapport HTML dans le dossier cible (doit être vide ou absent) |

Résultat : `rapport_html/index.html` — statistiques agrégées, percentiles, débit, courbes.

## Démo locale hors ligne (recommandée)

L'API mock du dépôt implémente exactement `/login`, `/protected` et `/health`, y compris le format
formulaire attendu par le sampler : **le plan fonctionne sans aucune modification**.

```bash
# terminal 1
python mock_api/mock_server.py --port 8080 --latency-ms 60

# terminal 2
jmeter -n -t jmeter/plan_de_test.jmx ^
       -Jhost=127.0.0.1 -Jport=8080 -Jprotocol=http ^
       -Jthreads=50 -Jramp=10 -Jduration=60 ^
       -l resultats.jtl -e -o rapport_html
```

Pour rendre la démo parlante : relancer le mock avec `--latency-ms 500`, rejouer le même plan, puis
comparer `Average` et `95%` dans les deux rapports. Même scénario, même charge, seule la cible change
— c'est exactement le raisonnement d'un test de performance.

## Alternative : API publique réelle

`https://dummyjson.com` (**vérifié le 2026-10-21**) : `POST /auth/login` → `200` avec la clé
**`accessToken`** (et non `access_token`), `GET /auth/me` avec `Bearer` → `200`, sans en-tête → `401`,
`GET /test` → `200`.

Cette API n'utilise pas les mêmes chemins que le POC : il faut donc **éditer le plan** (contrairement
à la démo mock).

| Champ JMeter | Valeur POC | Valeur démo `dummyjson` |
|---|---|---|
| Path du sampler login | `/login` | `/auth/login` |
| Paramètres du login | `user` / `pass` | `username` = `emilys`, `password` = `emilyspass` |
| JSONPath (extracteur) | `$.access_token` | `$.accessToken` |
| Path du sampler protégé | `/protected` | `/auth/me` |
| Health check | `/health` | `/test` |

La cible reste sinon la même commande : `-Jhost=dummyjson.com` (port `443`, protocol `https` par
défaut).

**Le piège** : `dummyjson` attend du **JSON** (`Content-Type: application/json` + corps
`{"username": "emilys", "password": "emilyspass"}`), alors que le sampler du POC envoie des
paramètres de formulaire. Il faut basculer l'onglet *Body Data*. Si le login échoue en `401`/`400`,
c'est presque toujours cette cause — ou le JSONPath resté sur `$.access_token`.

## Vérifié le 2026-10-21 (conteneurs)

Campagne de référence : `docker compose run --rm jmeter`, cible `mock:8080` avec 60 ms de latence
simulée, 50 threads, rampe 10 s.

| Contrôle | Résultat |
|---|---|
| Échantillons | 1 000 (500 `POST /login`, 500 `GET /protected`) |
| Codes de réponse | 200 × 200 — **0 % d'erreur** |
| Débit | 92 transactions/s |
| Latence | moyenne 45 ms, **p95 93 ms**, p99 139 ms |
| Rapport `-e -o` | `index.html` régénéré (9,5 Ko, 127 fichiers) |

**Défaut trouvé à cette occasion** : la version d'origine du plan envoyait `POST /login` en `400` pour
100 % des requêtes. Les arguments HTTP étaient déclarés ainsi :

```xml
<elementProp name="user" elementType="HTTPArgument">
  <stringProp name="Argument.value">testuser</stringProp>
  <stringProp name="Argument.metadata">=</stringProp>
</elementProp>
```

Sans `<stringProp name="Argument.name">user</stringProp>`, JMeter ignore le nom du paramètre et envoie
`=testuser&=testpass` : le serveur répond `400`, puis la corrélation n'a pas de jeton et `/protected`
répond `401`. L'attribut `name` du `elementProp` ne joue pas ce rôle — il ne sert qu'à l'interface.

La correction ajoute `Argument.name` **et** `HTTPArgument.use_equals` sur les deux paramètres. C'est
exactement le genre de détail qui se défend en entretien : « je ne me suis pas contenté d'écrire le
plan, je l'ai exécuté et lu les `.jtl` ».

## Points à savoir défendre en entretien

- **Pourquoi un ramp-up** : 50 utilisateurs lancés instantanément produisent un pic artificiel ;
  le ramp-up de 10 s simule une montée en charge progressive et évite de saturer le générateur.
- **Pourquoi le scheduler** : la durée (60 s) prime sur le nombre d'itérations (10) dès que
  `scheduler=true`. Un test doit avoir une **durée de régime stable**, sinon on mesure la montée
  en charge et pas le palier.
- **Corrélation** : sans extraction du jeton, la route protégée renvoie `401` et le test ne mesure
  rien d'utile.
- **Assertion vs code retour** : JMeter compte une requête en succès sur le code HTTP ; l'assertion
  explicite est ce qui transforme un `200` inattendu en échec visible.
- **Paramétrage `-J`** : séparer le scénario de l'environnement est la marque d'un plan réutilisable
  — et ce que l'on attend d'un test exécuté par une CI.
- **`-e -o`** : le rapport HTML est le livrable client (débit, p95, taux d'erreur), le `.jtl` est la
  donnée brute réutilisable.
- **Ce que JMeter ne fait pas tout seul** : générer une charge distribuée (contrôleur/worker), ou
  versionner proprement le scénario — d'où l'intérêt de son équivalent Locust dans ce POC.

## Limites connues du fichier

- La cible par défaut `api.example.com` n'existe pas : sans `-Jhost` (ou sans le mock), le plan est
  un **modèle**, pas un test exécutable.
- `guiclass="JSONPathAssertionGui"` sur le `JSONPostProcessor` : l'attribut `testclass` est correct,
  mais si l'interface refuse d'ouvrir l'élément, remplacer par `JSONPostProcessorGui`.
- Pas de `CSV Data Set Config` : les identifiants sont identiques pour tous les utilisateurs
  virtuels. Sur un vrai test, on génère un utilisateur par thread depuis un fichier CSV.
- Pas de répartition de charge multi-scénarios (login massif vs navigation), pas de think time.
- `-J` ne fonctionne que sur les propriétés **du plan** : les propriétés système JMeter (mémoire,
  threads) se règlent dans `jmeter.bat` / `user.properties`.
