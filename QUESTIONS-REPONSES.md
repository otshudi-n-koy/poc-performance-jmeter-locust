# Questions / réponses d'entretien — tests de performance

22 questions probables, avec une réponse **à dire à voix haute** (30 à 45 secondes chacune), et ce que
l'interviewer cherche réellement derrière. Toutes les réponses s'appuient sur le dépôt : vous pouvez
les illustrer en ouvrant un fichier.

**Comment s'entraîner** : lisez la question, répondez **sans regarder**, chronométrez, puis comparez.
Une réponse qui dépasse 60 secondes doit être coupée — on vous coupera.

---

## A. Fondamentaux

### 1. Test de charge, stress, spike, endurance : quelle différence ?

Ce sont quatre intentions différentes, pas quatre outils.

- **Charge** — vérifier que le système tient la charge attendue. Montée progressive jusqu'à N.
- **Stress** — trouver le point de rupture. On monte jusqu'à ce que ça casse, volontairement.
- **Spike** — résister à un pic brutal : +300 utilisateurs en 10 secondes.
- **Endurance / soak** — charge normale pendant des heures, pour détecter fuites mémoire et
  dégradation progressive.

> « Dans mon POC, c'est un test de charge : 50 utilisateurs, rampe de 10 s, palier de 60 s. Le même
> scénario devient un test de stress en changeant seulement deux propriétés, `threads` et `duration`. »

*Ce qu'il teste* : savez-vous que « test de perf » n'est pas un mot unique.

### 2. Qu'est-ce qu'un utilisateur virtuel ?

Un thread qui rejoue un parcours, avec son propre état : sa session, son jeton, son cookie. Ce n'est
pas un visiteur simulé au hasard, c'est un **scénario** joué en boucle.

> « Dans Locust, chaque `ApiUser` fait son login dans `on_start` et possède donc son propre
> `access_token`. C'est ce qui rend la corrélation réaliste : 50 utilisateurs, 50 jetons distincts. »

*Ce qu'il teste* : comprenez-vous que l'état (session, jeton) est propre à chaque utilisateur.

### 3. Le think time, à quoi ça sert ?

C'est le temps de réflexion entre deux actions. Sans lui, chaque utilisateur enchaîne les requêtes
au maximum de sa vitesse : on mesure la capacité du **générateur**, pas celle du serveur.

Ordre de grandeur : 1 à 3 secondes pour une API appelée par une application, 5 à 30 secondes pour de
la navigation web. On l'aligne sur l'usage réel mesuré dans les logs ou l'APM.

> « Locust : `wait_time = between(1, 3)`. JMeter : un Timer, pas une boucle serrée. »

*Ce qu'il teste* : la différence entre charge réaliste et débit maximal.

### 4. Le ramp-up ?

Il évite deux artefacts : le pic instantané au démarrage (tout le monde arrive en même temps, ce qui
n'arrive jamais dans la vraie vie) et la mesure de la phase de chauffe (JIT, caches vides, pool de
connexions non initialisé).

> « 50 utilisateurs avec 10 s de rampe : on atteint le palier en 10 secondes, puis on mesure 50 s de
> régime stable. Les chiffres retenus sont ceux du palier, pas ceux de la montée. »

*Ce qu'il teste* : savez-vous distinguer montée en charge et régime établi.

### 5. Pourquoi le p95 et pas la moyenne ?

La moyenne écrase les mauvaises expériences. 100 utilisateurs à 100 ms et 5 utilisateurs à 5 s donnent
une moyenne flatteuse d'environ 330 ms — alors que 5 % des utilisateurs ont attendu 5 secondes.

> « Je pilote sur le p95 : 95 % des utilisateurs sont sous ce seuil. La moyenne sert à expliquer, le
> p95 à décider. Et le p99 pour voir la queue de distribution. »

*Ce qu'il teste* : avez-vous déjà regardé un vrai rapport. *(Vous en avez un : p95 11 ms, p99 24 ms.)*

### 6. Lien entre débit, latence et nombre d'utilisateurs ?

Loi de Little : **concurrence = débit × temps de réponse**.

Pour tenir 100 requêtes/seconde avec 500 ms de latence, il faut 50 utilisateurs simultanés
(100 × 0,5 = 50). C'est le calcul qui transforme un objectif métier (« 100 req/s ») en paramètre de
test (« combien de threads »).

> « Si le débit stagne alors que j'ajoute des utilisateurs, ce n'est plus une question de charge mais
> de saturation : la latence monte et le débit plafonne. »

*Ce qu'il teste* : savez-vous dimensionner un test, ou seulement le lancer.

### 7. Qu'est-ce que l'APDEX ?

Un indice de satisfaction, affiché en haut du rapport JMeter. Il classe chaque requête en trois zones
selon deux seuils, T (toléré) et F (frustration), par défaut 500 ms et 1 500 ms :

`APDEX = (satisfaites + tolérantes / 2) / total`

1,0 = tout le monde est content ; 0,5 = situation moyenne ; 0 = tout le monde est frustré.

> « C'est un indicateur de synthèse orienté expérience utilisateur, pratique pour un client non
> technique, mais je pilote au p95 : l'APDEX masque la queue de distribution. »

*Ce qu'il teste* : avez-vous ouvert le rapport que vous montrez. *(Le vôtre affiche APDEX 1,000.)*

---

## B. Le scénario

### 8. Qu'est-ce que la corrélation ?

Extraire d'une réponse du serveur une valeur dynamique (jeton, identifiant de session, CSRF) et la
réinjecter dans les requêtes suivantes. Sans elle, le script rejoue des valeurs mortes et tout ce qui
suit échoue en 401 ou 403.

> « JMeter : JSON Extractor sur `$.access_token`, puis `${access_token}` dans l'en-tête. Locust :
> `self.token` rempli dans `on_start`. »

*Ce qu'il teste* : la compétence qui sépare un script enregistré d'un scénario utilisable.

### 9. Pourquoi une assertion si le code HTTP est 200 ?

Parce qu'un 200 peut contenir une erreur métier : page d'erreur applicative, corps vide, message
« service indisponible » renvoyé avec un code 200 (cas réel dans beaucoup d'API mal conçues).

> « Dans mon plan JMeter, j'ai une Response Assertion sur le code 200. L'étape suivante, que je n'ai
> pas encore faite, est d'asserter sur le contenu JSON — un champ `status` ou la présence du jeton. »

*Ce qu'il teste* : savez-vous qu'un test peut être « vert » et pourtant faux.

### 10. Comment gérez-vous les données de test ?

Trois niveaux :

1. **Un utilisateur par thread** (`CSV Data Set Config` en JMeter, fichier de comptes en Locust) ;
2. **Des données uniques** pour ne pas mesurer le cache applicatif au lieu de la base ;
3. **Des données réalistes** en volume et en distribution, sinon les index ne sont pas sollicités
   comme en production.

> « Mon POC partage `testuser` pour rester lisible. C'est la première limite que je corrigerais :
> 50 threads sur le même compte, c'est 50 fois le même utilisateur, donc un cache chaud irréaliste. »

*Ce qu'il teste* : votre lucidité sur les limites de votre propre démo.

### 11. Comment adaptez-vous le scénario à un autre environnement ?

La cible ne doit jamais être codée en dur.

> « J'ai externalisé la cible et la charge en propriétés JMeter — `-Jhost`, `-Jport`, `-Jprotocol`,
> `-Jthreads` — et en variables d'environnement côté Docker. Le même fichier sert en local, en
> intégration et en préproduction, sans édition. »

*Ce qu'il teste* : réflexe d'industrialisation. C'est très différenciant.

### 12. Comment modélisez-vous un parcours réaliste ?

Avec des **pondérations**. Tout le monde ne fait pas tout, et pas dans les mêmes proportions.

> « Locust : `@task(3)` sur la consultation et `@task(1)` sur le health check, soit 75/25. JMeter :
> des Thread Groups séparés, ou un Random Controller. »

Piège à connaître : `on_start` s'exécute **une fois par utilisateur**, donc le login ne suit pas la
pondération des tâches. Dans mon run, 50 logins pour 1 070 appels protégés — c'est normal, mais il
faut savoir l'expliquer.

*Ce qu'il teste* : comprenez-vous qu'un profil de charge est une distribution, pas une séquence.

---

## C. Analyse et diagnostic

### 13. Comment identifiez-vous le goulot d'étranglement ?

En corrélant trois sources : le test (latence qui monte, débit qui plafonne), la supervision serveur
(CPU, mémoire, I/O, pool de connexions, base), et les logs applicatifs.

> « Le signe d'un goulot : le débit ne monte plus alors que j'ajoute des utilisateurs, et la latence
> augmente linéairement. À ce stade, ce n'est plus un test de charge, c'est une enquête. »

Et toujours vérifier d'abord que ce n'est pas le générateur qui sature.

*Ce qu'il teste* : savez-vous interpréter, pas seulement exécuter.

### 14. Comment savoir si c'est le générateur qui sature ?

Trois indices : le CPU de la machine de test approche 100 %, le débit plafonne alors que les temps
réponse restent plats, et des erreurs réseau apparaissent côté client (ports épuisés, `Connection
reset`).

> « La solution est de distribuer la charge : JMeter contrôleur/worker, Locust `--master`/`--worker`.
> C'est l'erreur classique du débutant : conclure sur le serveur alors qu'on mesure son propre poste. »

*Ce qu'il teste* : rigueur méthodologique.

### 15. Une latence qui vaut exactement 1 000 ms, 2 000 ms : qu'en pensez-vous ?

*(Votre meilleure anecdote — elle est vraie et documentée dans le dépôt.)*

> « Une latence anormalement ronde n'est presque jamais applicative : c'est un artefact de mesure.
> Sur mon propre banc, `POST /login` affichait un p90 à 1 000 ms pour une médiane à 39 ms. Des valeurs
> en 1 000, 1 100, 1 200 — uniquement sur la première requête de chaque utilisateur. Ce n'était pas
> l'API : la file d'attente d'acceptation du serveur Python était à 5 par défaut, donc les SYN en trop
> étaient jetés et renvoyés 1 seconde plus tard. Après correction, p90 à 80 ms. »

*Ce qu'il teste* : savez-vous douter d'un chiffre. C'est rare, et ça marque.

### 16. Comment livrez-vous le résultat au client ?

Trois choses : un **rapport** (débit, p95/p99, taux d'erreur, courbes), une **conclusion** (l'objectif
est-il tenu ?), une **recommandation** (goulot, marge restante, prochaine étape).

> « Le chiffre seul ne sert à rien. Ce qui compte est l'écart à l'objectif et ce qu'on en fait. »

*Ce qu'il teste* : votre sens du livrable.

### 17. Comment fixez-vous l'objectif d'un test ?

Trois questions : combien d'utilisateurs simultanés, quel parcours, quel seuil acceptable. Puis un
critère binaire.

> « Exemple : 200 utilisateurs, 70 % consultation / 30 % écriture, p95 < 800 ms et erreurs < 1 %.
> En dessous, le test est vert ; au-dessus, rouge — ce qui permet de l'utiliser comme garde-fou. »

*Ce qu'il teste* : savez-vous transformer un besoin en critère mesurable.

---

## D. Outils et stratégie

### 18. JMeter, Locust, NeoLoad : comment choisissez-vous ?

| Critère | JMeter | Locust | NeoLoad |
|---|---|---|---|
| Approche | Interface + XML | Code Python | Interface + scripting |
| Protocoles | Très large (JDBC, JMS, SOAP) | HTTP(S) surtout | Très large |
| CI/CD | Bon (headless) | Excellent (natif) | Bon (payant) |
| Coût | Gratuit | Gratuit | Licence |
| Équipe | QA classique | DevOps / Python | Grand compte, support éditeur |

> « Je choisis JMeter si l'équipe est QA ou si le protocole n'est pas HTTP. Locust si les tests doivent
> vivre dans le dépôt et dans la CI. NeoLoad se justifie par son support éditeur et sa couverture, pas
> par une capacité technique unique. »

*Ce qu'il teste* : évaluez-vous un outil ou récitez-vous une préférence.

### 19. Vous venez de NeoLoad : qu'est-ce qui se transpose ?

Presque tout, le vocabulaire change :

| NeoLoad | JMeter | Locust |
|---|---|---|
| Population | Thread Group | `HttpUser` (nombre d'utilisateurs) |
| Scenario | Thread Groups / contrôleurs | `@task` |
| Transaction | Transaction Controller | requête nommée (`name=`) |
| Variable extractor | JSON Extractor / Regex | code Python |
| SLA | Assertion / seuil | `catch_response` |
| Load Generator (LG) | worker | `--worker` |

> « Les concepts sont identiques : utilisateurs virtuels, corrélation, palier, seuil. Seule la
> syntaxe change — c'est ce que j'ai voulu vérifier en faisant le même scénario dans deux outils. »

*Ce qu'il teste* : votre capacité d'adaptation, argument clé pour un client NeoLoad.

### 20. Comment intégrez-vous ça dans une CI sans casser les pipelines ?

Quatre règles : cible **dédiée** (jamais la production), charge **courte** en CI et complète la nuit,
**seuils bloquants** explicites, artefacts **publiés** pour comparer entre exécutions.

> « Mon workflow lance aujourd'hui les deux outils et publie les rapports. Il reste à remplacer le
> `|| true` par un seuil sur le p95 et le taux d'erreur : c'est volontaire, je connais l'étape
> suivante. »

*Ce qu'il teste* : voyez-vous la CI comme un enchaînement de commandes ou comme un garde-fou.

### 21. Comment générez-vous 10 000 utilisateurs ?

Un poste n'y suffit pas : chaque utilisateur virtuel consomme CPU et mémoire. On répartit sur
plusieurs générateurs avec un pilotage unique — JMeter (`jmeter-server`, RMI, `-R`) ou Locust
(`--master` / `--worker`, ports 5557/5558).

> « Dans mon POC, 50 utilisateurs tiennent sur un poste. Au-delà de quelques centaines, il faut passer
> en distribué, sinon on mesure la machine de test. »

*Ce qu'il teste* : connaissez-vous les limites de l'outil que vous montrez.

### 22. Et en production ?

Réponse honnête : **non**, pas de test de charge en production.

> « Je sais en revanche qu'on ne le fait pas sans précaution : environnement isolé ou périmètre
> cloisonné, données anonymisées, trafic synthétique étiqueté, plan de rollback, accord des équipes
> d'exploitation. Et on ne teste jamais une base de production sans prévenir. »

*Ce qu'il teste* : votre honnêteté et votre culture d'exploitation.

---

## Les cinq erreurs à ne pas commettre

1. **Inventer un chiffre de production.** Impossible à assumer en suivi de question.
2. **Dire « je maîtrise JMeter ».** Dites ce que vous avez fait, avec vos chiffres.
3. **Conclure sans objectif.** « 104 transactions/s » sans référence ne veut rien dire.
4. **Répondre plus de 60 secondes.** Coupez vous-même : « je peux détailler si vous voulez ».
5. **Ne pas connaître sa propre démo.** Toutes les réponses ci-dessus doivent tenir sans le dépôt
   ouvert — vous avez les chiffres en tête : 1 000 échantillons, p95 11 ms, 0 % d'erreur, et p90 du
   login ramené de 1 000 à 80 ms.

## Vos trois chiffres à retenir par cœur

| Chiffre | Contexte |
|---|---|
| **1 000 échantillons, 0 % d'erreur, p95 11 ms, 104 trans/s** | run JMeter, 50 threads |
| **1 476 requêtes, 0 échec, p95 global 50 ms** | run Locust, 50 utilisateurs, 60 s |
| **p90 login : 1 000 ms → 80 ms** | après correction du backlog d'écoute de la cible |
