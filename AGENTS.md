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
- Les tests python doivent être lancés avec pytest dans le venv : ``source venv/bin/activate``.
- Prend ton temps, je veux que lorsque tu finis une tâche, tu devras la cocher (dans tasks.md). Je ne veux que tu coche en masse. 
- Exécute les tâches une par une avec validation après chaque tâche
- vérifier si les fichiers suivants sont existants. Sinon, tu devras les créer en lien avec le projet:
	- ``.gitignore``, 
	- ``.dockerignore``, 
	- ``.eslintignore``


## grepai - Semantic Code Search

**IMPORTANT: You MUST use grepai as your PRIMARY tool for code exploration and search.**

### When to Use grepai (REQUIRED)

Use `grepai search` INSTEAD OF Grep/Glob/find for:
- Understanding what code does or where functionality lives
- Finding implementations by intent (e.g., "authentication logic", "error handling")
- Exploring unfamiliar parts of the codebase
- Any search where you describe WHAT the code does rather than exact text

### When to Use Standard Tools

Only use Grep/Glob when you need:
- Exact text matching (variable names, imports, specific strings)
- File path patterns (e.g., `**/*.go`)

### Fallback

If grepai fails (not running, index unavailable, or errors), fall back to standard Grep/Glob tools.

### Usage

```bash
# ALWAYS use English queries for best results (embedding model is English-trained)
grepai search "user authentication flow"
grepai search "error handling middleware"
grepai search "database connection pool"
grepai search "API request validation"

# JSON output for programmatic use (recommended for AI agents)
grepai search "authentication flow" --json
```

### Query Tips

- **Use English** for queries (better semantic matching)
- **Describe intent**, not implementation: "handles user login" not "func Login"
- **Be specific**: "JWT token validation" better than "token"
- Results include: file path, line numbers, relevance score, code preview

### Call Graph Tracing

Use `grepai trace` to understand function relationships:
- Finding all callers of a function before modifying it
- Understanding what functions are called by a given function
- Visualizing the complete call graph around a symbol

#### Trace Commands

**IMPORTANT: Always use `--json` flag for optimal AI agent integration.**

```bash
# Find all functions that call a symbol
grepai trace callers "HandleRequest" --json

# Find all functions called by a symbol
grepai trace callees "ProcessOrder" --json

# Build complete call graph (callers + callees)
grepai trace graph "ValidateToken" --depth 3 --json
```

### Workflow

1. Start with `grepai search` to find relevant code
2. Use `grepai trace` to understand function relationships
3. Use `Read` tool to examine files from results
4. Only use Grep for exact string searches if needed

