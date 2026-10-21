# Plan de test JMeter — POC API

Ce dossier contient le scénario JMeter équivalent du POC : un utilisateur virtuel se connecte,
récupère un jeton et appelle une route protégée.

## Fichier

| Fichier | Rôle |
|---|---|
| `plan_de_test.jmx` | Plan de test XML (Test Plan JMeter 5.6.3) |

## ⚠️ Cible du fichier : `api.example.com`

`plan_de_test.jmx` pointe volontairement sur `https://api.example.com`, une **URL de
démonstration qui n'existe pas**. C'est le contrat d'interface du POC : les endpoints attendus sont

| Endpoint | Méthode | Attendu |
|---|---|---|
| `/login` | POST | `200` + corps JSON `{"access_token": "..."}` |
| `/protected` | GET + `Authorization: Bearer <token>` | `200` |
| `/health` | GET | `200` |

Pour exécuter le plan, il faut donc le repointer vers une API réelle (voir plus bas).

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

## Lancement en mode graphique (pour découvrir l'outil)

```bash
jmeter                       # ouvre l'interface
```
Puis `File > Open` → `jmeter/plan_de_test.jmx`.

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
| `-l` | Fichier de résultats bruts (`.jtl`) |
| `-e -o` | Génère le rapport HTML dans le dossier cible (doit être vide ou absent) |

Résultat : `rapport_html/index.html` — statistiques agrégées, percentiles, débit, courbes.

## Repointer le plan vers une API publique réelle

`https://dummyjson.com` expose une API de démonstration **vérifiée le 2026-10-21** :

| Vérification | Résultat observé |
|---|---|
| `POST /auth/login` | `200` → clé **`accessToken`** (et non `access_token`) |
| `GET /auth/me` sans en-tête | `401` |
| `GET /auth/me` avec `Bearer <accessToken>` | `200` |
| `GET /test` | `200` → `{"status":"ok"}` |

Correspondance à appliquer dans le GUI (les noms d'endpoints diffèrent du POC) :

| Champ JMeter | Valeur POC | Valeur démo `dummyjson` |
|---|---|---|
| Protocol | `https` | `https` |
| Server Name | `api.example.com` | `dummyjson.com` |
| Port | `443` | `443` |
| Path du sampler login | `/login` | `/auth/login` |
| Paramètres du login | `user` / `pass` | `username` = `emilys`, `password` = `emilyspass` |
| JSONPath (extracteur) | `$.access_token` | `$.accessToken` |
| Path du sampler protégé | `/protected` | `/auth/me` |
| Health check | `/health` | `/test` |

**Le piège** : `dummyjson` attend du **JSON** (`Content-Type: application/json` + corps
`{"username": "...", "password": "..."}`), alors que le plan du POC envoie des paramètres de
formulaire. Il faut basculer l'onglet *Body Data* du sampler. Si le login échoue en `401`/`400`,
c'est presque toujours cette cause — ou le JSONPath resté sur `$.access_token`.

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
- **`-e -o`** : le rapport HTML est le livrable client (débit, p95, taux d'erreur), le `.jtl` est la
  donnée brute réutilisable.
- **Ce que JMeter ne fait pas tout seul** : générer une charge distribuée (contrôleur/worker), ou
  versionner proprement le scénario — d'où l'intérêt de son équivalent Locust dans ce POC.

## Limites connues du fichier

- La cible `api.example.com` n'existe pas : le plan est un **modèle**, pas un test exécutable en
  l'état.
- `guiclass="JSONPathAssertionGui"` sur le `JSONPostProcessor` : l'attribut `testclass` est correct,
  mais si l'interface refuse d'ouvrir l'élément, remplacer par `JSONPostProcessorGui`.
- Pas de `CSV Data Set Config` : les identifiants sont identiques pour tous les utilisateurs
  virtuels. Sur un vrai test, on génère un utilisateur par thread depuis un fichier CSV.
- Pas de répartition de charge multi-scénarios (login massif vs navigation), pas de think time.
