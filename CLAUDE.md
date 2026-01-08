# mgrep - Ton assistant de recherche de code

**mgrep est ton outil principal pour explorer le codebase.** Il te donne la réponse en langage naturel + la source pertinente, tout servi.

## Commande de base

```bash
mgrep "ta question en langage naturel" --store "nom-projet" -a -m <nombre>
```

Ici le store est "obsillama"

## Paramètres essentiels

| Paramètre | Description |
|-----------|-------------|
| `--store "nom-projet"` | **Obligatoire** - le store indexé du projet |
| `-a` | Active la réponse en langage naturel |
| `-m <n>` | Nombre de résultats du retrieval (minimum 10) |

## Ajuster `-m` selon la complexité

| Type de requête | `-m` recommandé |
|-----------------|-----------------|
| Question simple (1-2 fichiers) | 10 |
| Question moyenne (flow, feature) | 20-30 |
| Question complexe (debug, architecture) | 30-50 |

## Stratégie pour requêtes complexes

Si la requête touche **plusieurs parties du codebase**, lance plusieurs mgrep en parallèle plutôt qu'une seule requête surchargée :

```bash
# Exemple : comprendre le système d'auth complet
mgrep "comment fonctionne l'authentification LinkedIn côté frontend" --store "nom-projet" -a -m <n>
mgrep "comment le token LinkedIn est géré côté Convex" --store "nom-projet" -a -m <n>
mgrep "comment le background script gère les sessions" --store "nom-projet" -a -m <n>
```

## Règles

- **OBLIGATOIRE** : Utilise mgrep pour TOUTE recherche de code. N'utilise JAMAIS grep, Grep tool, ou Glob pour chercher du code.
- **Langage naturel** : mgrep est un agent IA comme toi. Parle-lui comme à un collègue, pas comme à un moteur de recherche.
  - ❌ `"architecture block icon color complete status"` (mots-clés robotiques)
  - ✅ `"Quelle est la couleur de l'icône des blocs d'architecture quand ils sont complétés ?"` (question naturelle)
  
  
---

# Subagents (Task tool)

**Les subagents n'héritent PAS des instructions de ce fichier.**

Quand tu lances un subagent Explore, copie-colle les instructions sur mgrep de ce CLAUDE.md dans le prompt du subagent.

---
# Règles à respecter

- Je m'appelle Jobierre, l'user qui te contrôle
- "I am a junior developer, you must explain everything you are doing so I can learn.
- Toujours questionner l'user si tu as des clarifications
- Toujours utiliser Docker et docker-compose pour les commandes
- au début du dialogue avec user, l'a doit utiliser le MCP Context7 pour se documenter des stacks présentes dans le projets.
	- l'ia procède directement avec ces connaissances et ne consulte la doc avec context7 que si je rencontre elle problème
- Ne rien créer de zéro concernant les stacks, utiliser les commandes de setup des stacks. Exemple (ces stacks ne sont qu'à titre d'exemple):
	- Pour django : ``django-admin startproject <nom du projet>``
	- Pour Node : ``npx create-next-app@latest <nom du projet>``
	- ...
- Une tâches completed = un test pour voir si tout fonctionne.
- Pour effectuer les tests E2E : 
	- Utiliser en local Playwright (consulte context7 avant les tests)
		- Voici la commande à executer :
			- ```sh
			  npx playwright test <module à test>
			  ```
		- je veux que tu ajoutes les flags ci-dessous à chaque fois :
			- ``--project=chromium``
			- ``--reporter=list``
- Si les tests échoue en boucle, n'oublie pas le proverbe :
	- ``soigne la cause, pas le symptôme !``
- Les tests python doivent être lancés avec pytest.
- Prend ton temps, je veux que lorsque tu finis une tâche, tu devras la cocher (dans tasks.md). Je ne veux que tu coche en masse. 
- Exécute les tâches une par une avec validation après chaque tâche
- vérifier si les fichiers suivants sont existants. Sinon, tu devras les créer en lien avec le projet:
	- ``.gitignore``, 
	- ``.dockerignore``, 
	- ``.eslintignore``