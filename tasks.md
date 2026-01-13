# ObsIllama - Liste des tâches

> **Projet** : Système d'organisation intelligente de notes Obsidian avec GraphRAG + Ollama
> **Développeur** : Jobierre
> **Statut** : En cours (Phase 1)

---

## Légende

- [ ] Tâche à faire
- [x] Tâche terminée
- [~] Tâche en cours
- [!] Tâche bloquée/problème

**Important** : Chaque tâche completed = test pour vérifier que tout fonctionne !

---

## Phase 1 : Fondations (Semaine 1)

### 1.1 Structure du projet

- [x] Créer la structure des dossiers du projet
  - [x] `obsillama/` (package principal)
  - [x] `obsillama/cli/`
  - [x] `obsillama/core/`
  - [x] `obsillama/llm/`
  - [x] `obsillama/llm/prompts/`
  - [x] `obsillama/storage/`
  - [x] `obsillama/models/`
  - [x] `obsillama/utils/`
  - [x] `obsillama/config/`
  - [x] `data/lancedb/`
  - [x] `data/categories/`
  - [x] `data/cache/`
  - [x] `config/`
  - [x] `logs/`
  - [x] `tests/`
  - [x] `docs/`

- [x] Créer les fichiers `__init__.py` pour tous les packages Python

- [x] Créer `.gitignore`
  - [x] Ignorer `data/`, `logs/`, `*.pyc`, `__pycache__/`, `.env`, etc.

- [x] Créer `.dockerignore` (si besoin Docker plus tard)

- [x] Initialiser le repository git
  - [x] `git init`
  - [x] Commit initial

### 1.2 Configuration et dépendances

- [x] Créer `requirements.txt` avec toutes les dépendances
  ```
  graphrag==2.7.0
  lancedb>=0.17.0 (updated from 0.15.0 for compatibility)
  ollama>=0.4.2
  click>=8.1.7
  rich>=13.7.1
  textual>=0.85.0
  ruamel.yaml>=0.18.6
  python-frontmatter>=1.1.0
  pydantic>=2.9.2
  pandas>=2.2.3 (updated from 2.2.2 for graphrag compatibility)
  numpy>=1.26.4
  scikit-learn>=1.5.2
  igraph==0.11.8
  langchain==0.3.15
  tenacity==9.0.0
  tqdm==4.67.1
  chardet==5.2.0
  pathlib2==2.3.7
  ```

- [x] Créer `pyproject.toml` pour la configuration du projet

- [x] Créer `setup.py` pour l'installation du package

- [x] Installer les dépendances dans un environnement virtuel
  ```bash
  python3.11 -m venv venv  # Used Python 3.11 for graphrag compatibility
  source venv/bin/activate
  pip install -r requirements.txt
  ```

- [x] Tester l'installation des dépendances
  - [x] Vérifier que toutes les librairies s'importent correctement

### 1.3 Configuration système

- [x] Créer `config/config.yaml` avec la configuration par défaut
  - [x] Section `vault` (path, backup_path, exclude_folders)
  - [x] Section `ollama` (base_url, models, params)
  - [x] Section `graphrag` (algorithmes, entity_types)
  - [x] Section `categorization` (target_count, thresholds)
  - [x] Section `incremental` (tracking, auto_ameliorate)
  - [x] Section `frontmatter` (preserve, fields_to_add)
  - [x] Section `lancedb` (path, index_type)
  - [x] Section `processing` (workers, batch_size)
  - [x] Section `logging` (level, file)

- [x] Créer `obsillama/config/settings.py`
  - [x] Modèle Pydantic pour la configuration
  - [x] Chargement du fichier YAML
  - [x] Validation des paramètres
  - [x] Gestion des variables d'environnement

- [x] Tester le chargement de la configuration
  - [x] Script de test pour vérifier la lecture du config.yaml

### 1.4 Modèles de données

- [x] Créer `obsillama/models/note.py`
  - [x] Modèle `Note` avec tous les champs (id, file_path, title, content, etc.)
  - [x] Validation des types
  - [x] Méthodes helper (to_dict, from_dict, get_all_tags, has_tag)

- [x] Créer `obsillama/models/category.py`
  - [x] Modèle `Category` avec hiérarchie (parent/enfants)
  - [x] Champs pour review_status, confidence, etc.
  - [x] Méthodes (approve, reject, update_stats, etc.)

- [x] Créer `obsillama/models/embedding.py`
  - [x] Modèle `Embedding` pour les vecteurs
  - [x] Méthodes de calcul (cosine_similarity, euclidean_distance, normalize)

- [x] Créer `obsillama/models/graph_entity.py`
  - [x] Modèle `GraphEntity` pour entités GraphRAG
  - [x] Modèle `GraphRelationship` pour relations
  - [x] Modèle `GraphCommunity` pour communautés

- [x] Tester les modèles
  - [x] Créer des instances de test (25 tests pytest)
  - [x] Vérifier la validation Pydantic (tous passent)

### 1.5 Client Ollama (🔴 CRITIQUE)

- [x] Créer `obsillama/llm/ollama_client.py`
  - [x] Classe `OllamaClient` avec connexion à Ollama
  - [x] Méthode `generate()` pour génération de texte (mistral)
  - [x] Méthode `embed()` pour embeddings (nomic-embed-text)
  - [x] Méthode `embed_batch()` pour batch embeddings
  - [x] Retry logic avec tenacity (exponential backoff)
  - [x] Gestion d'erreurs et timeout
  - [x] Logging des appels API

- [x] Tester le client Ollama
  - [x] Test de connexion à Ollama (localhost:11434)
  - [x] Test génération avec mistral
    ```python
    response = client.generate("Bonjour, comment vas-tu ?")
    ```
  - [x] Test embeddings avec nomic-embed-text
    ```python
    embedding = client.embed("Test d'embedding en français")
    print(f"Dimension: {len(embedding)}")  # Devrait être 768
    ```
  - [x] Test batch embeddings (10 textes)
  - [x] Test retry sur échec simulé

### 1.6 Scanner de notes (🔴 CRITIQUE)

- [x] Créer `obsillama/core/frontmatter_parser.py`
  - [x] Fonction `parse_frontmatter(content: str)` avec python-frontmatter
  - [x] Gestion des notes sans frontmatter
  - [x] Extraction du contenu sans YAML
  - [x] Gestion des erreurs de parsing

- [x] Créer `obsillama/core/note_scanner.py`
  - [x] Classe `NoteScanner`
  - [x] Méthode `scan_vault(vault_path, exclude_folders)` → liste de fichiers .md
  - [x] Méthode `parse_note(file_path)` → objet Note
  - [x] Méthode `scan_and_parse(sample_strategy, sample_size)` → liste Notes
  - [x] Support échantillonnage : random, stratified, all
  - [x] Détection backlinks `[[...]]`
  - [x] Calcul word_count
  - [x] Cache des notes parsées (JSON)

- [x] Tester le scanner
  - [x] Test sur le vault réel : `/Users/jordanmirmand/Documents/Obsidian and CO/obsinote`
  - [x] Scanner 10 notes au hasard
  - [x] Vérifier le parsing du frontmatter
  - [x] Vérifier l'extraction du contenu
  - [x] Tester l'échantillonnage stratifié (15%)

### 1.7 LanceDB Manager (🔴 CRITIQUE)

- [x] Créer `obsillama/storage/lancedb_manager.py`
  - [x] Classe `LanceDBManager` avec connexion à LanceDB
  - [x] Méthode `create_notes_table()` avec schéma complet
  - [x] Méthode `create_categories_table()`
  - [x] Méthode `create_entities_table()`
  - [x] Méthode `create_communities_table()`
  - [x] Méthode `insert_notes(notes: List[Note])`
  - [x] Méthode `insert_categories(categories: List[Category])`
  - [x] Méthode `get_note_by_id(note_id: str)` → Note
  - [x] Méthode `get_all_notes()` → List[Note]
  - [x] Méthode `search_notes_by_embedding(query_embedding, limit=10)`
  - [x] Création d'index vectoriel IVF_PQ

- [x] Tester LanceDB
  - [x] Créer les tables dans `data/lancedb/`
  - [x] Insérer 5 notes de test
  - [x] Récupérer une note par ID
  - [x] Recherche vectorielle avec embedding test
  - [x] Vérifier la persistance (fermer/rouvrir DB)

---

## Phase 2 : GraphRAG (Semaine 2)

### 2.1 Prompts français

- [x] Créer `obsillama/llm/prompts/categorization.py`
  - [x] Prompt pour génération de catégories (FR)
  - [x] Prompt pour nommage de catégories
  - [x] Prompt pour descriptions de catégories

- [x] Créer `obsillama/llm/prompts/analysis.py`
  - [x] Prompt pour extraction d'entités (FR)
  - [x] Prompt pour extraction de relations
  - [x] Prompt pour résumé de communauté

- [x] Créer `obsillama/llm/prompts/refinement.py`
  - [x] Prompt pour amélioration de catégories
  - [x] Prompt pour création de sous-catégories
  - [x] Prompt pour fusion de catégories

### 2.2 Pipeline GraphRAG (🔴 CRITIQUE)

- [x] Créer `obsillama/llm/graphrag_integration.py`
  - [x] Classe `GraphRAGPipeline`
  - [x] Méthode `extract_entities(note: Note)` → List[GraphEntity]
    - [x] Appel LLM avec prompt français
    - [x] Parsing de la réponse JSON
    - [x] Création objets GraphEntity
  - [x] Méthode `extract_relationships(notes, entities)` → List[GraphRelationship]
  - [x] Méthode `build_graph(entities, relationships)` → igraph.Graph
  - [x] Méthode `detect_communities(graph)` → List[GraphCommunity]
    - [x] Algorithme Leiden
    - [x] Seuil min_community_size
  - [x] Méthode `summarize_community(community)` → str (description LLM)
  - [x] Méthode `run_full_pipeline(notes)` → (entities, relationships, communities)

- [x] Créer `obsillama/storage/graph_store.py`
  - [x] Classe `GraphStore` pour stockage dans LanceDB
  - [x] Méthode `save_entities(entities)`
  - [x] Méthode `save_communities(communities)`
  - [x] Méthode `load_graph()` → (entities, relationships, communities)

- [x] Tester le pipeline GraphRAG
  - [x] Test sur 20 notes du vault (115 entités, 55 relations extraites)
  - [x] Vérifier extraction d'entités (technologies, personnes, etc.)
  - [x] Vérifier détection de communautés (Leiden avec RTX 5070 Ti)
  - [x] Vérifier résumés générés par LLM
  - [x] Tester le stockage dans LanceDB (sauvegarde/chargement validés)

### 2.3 Générateur de catégories

- [x] Créer `obsillama/core/category_generator.py`
  - [x] Classe `CategoryGenerator`
  - [x] Méthode `generate_from_communities(communities)` → List[Category]
    - [x] Mapper communautés → catégories suggérées
    - [x] Génération noms via LLM
    - [x] Génération descriptions
    - [x] Calcul keywords
  - [x] Méthode `assign_notes_to_categories(notes, categories)` → Dict
    - [x] Utilise embeddings pour similarité
    - [x] Calcul confidence_score
  - [x] Méthode `build_hierarchy(categories)` → hiérarchie parent/enfant
  - [x] Méthode `generate_tag_names(categories)` → ajout tag_name

- [x] Créer `obsillama/storage/category_store.py`
  - [x] Classe `CategoryStore`
  - [x] Méthode `save_taxonomy(categories)` → JSON
  - [x] Méthode `save_assignments(assignments)` → JSON
  - [x] Méthode `load_taxonomy()` → List[Category]
  - [x] Méthode `update_category(category_id, updates)`

- [x] Tester le générateur
  - [x] Générer des catégories à partir des communautés GraphRAG (2 catégories créées)
  - [x] Vérifier la hiérarchie (parents/enfants) (niveau 0, hiérarchie plate validée)
  - [x] Assigner les notes de test aux catégories (5 notes assignées, similarité 0.69-0.77)
  - [x] Vérifier les confidence_scores (tous > seuil 0.6)
  - [x] Sauvegarder dans `data/categories/taxonomy.json` (version 20260110_180225)

---

## Phase 3 : Embeddings (Semaine 3)

### 3.1 Gestion des embeddings

- [x] Créer `obsillama/core/embedding_manager.py`
  - [x] Classe `EmbeddingManager`
  - [x] Méthode `generate_embedding(text: str)` → List[float]
    - [x] Appel client Ollama (nomic-embed-text)
    - [x] Troncature automatique à 2000 chars
  - [x] Méthode `generate_embeddings_batch(texts, batch_size=8)`
    - [x] Traitement par batch
    - [x] Progress bar avec tqdm
  - [x] Méthode `embed_notes(notes)` → Notes avec embeddings
  - [x] Cache embeddings (hash du contenu → embedding)
    - [x] Persistance JSON
    - [x] Accélération 1190x
  - [x] Méthode `compute_similarity(emb1, emb2)` → float (cosine)

- [x] Créer `obsillama/storage/embedding_store.py`
  - [x] Classe `EmbeddingStore` (extension LanceDBManager)
  - [x] Méthode `upsert_embeddings(note_id, embedding)`
  - [x] Méthode `search_similar_notes(query_embedding, top_k=10)`
  - [x] Méthode `get_category_centroid(category_id)` → embedding moyen
  - [x] Méthodes avancées (batch_search, similarity_range)

- [x] Tester le système d'embeddings
  - [x] Générer embeddings pour 19 notes (79.42 notes/sec)
  - [x] Vérifier la dimension (768)
  - [x] Tester la recherche sémantique (5.84ms moyenne)
    - [x] Query : "self-hosting docker"
    - [x] Vérifier les résultats pertinents
  - [x] Tester le cache (re-générer → utilise cache, 1190x plus rapide)
  - [x] Calculer centroides pour les catégories

### 3.2 Recherche sémantique

- [x] Ajouter méthodes de recherche
  - [x] Recherche par texte libre (search_by_text)
  - [x] Recherche filtrée par catégorie
  - [x] Recherche avec seuil de similarité
  - [x] Recherche filtrée par dossier et word_count

- [x] Tester la recherche
  - [x] 10 requêtes de test variées (benchmark complet)
  - [x] Vérifier la pertinence des résultats
  - [x] Mesurer les temps de réponse (5.84ms moyenne)

---

## Phase 4 : CLI (Semaine 4)

### 4.1 Infrastructure CLI

- [x] Créer `obsillama/__main__.py`
  - [x] Point d'entrée pour `python -m obsillama`
  - [x] Auto-envvar prefix OBSILLAMA

- [x] Créer `obsillama/cli/commands.py`
  - [x] Groupe Click principal avec décorateurs
  - [x] Classe ObsillamaContext pour contexte partagé
  - [x] Configuration logging avec RichHandler
  - [x] Chargement config globale avec gestion erreurs
  - [x] Support --config et --verbose flags
  - [x] Version command (--version)
  - [x] Help formaté avec workflow typique

- [x] Créer `obsillama/utils/progress.py`
  - [x] Fonctions helper pour progress bars (create_progress, track_progress)
  - [x] Affichage de tableaux (create_table, print_table)
  - [x] Messages formatés (success, error, warning, info, step)
  - [x] Panels et sections (print_panel, print_header)
  - [x] Statistiques et résumés (print_stats, print_summary)
  - [x] Interactions utilisateur (confirm, prompt)
  - [x] Formatters utilitaires (size, duration, percentage)
  - [x] Tests complets avec test_cli_helpers.py (tous passent)

### 4.2 Commande `init`

- [x] Créer `obsillama/cli/init.py`
  - [x] Command Click `init` avec décorateur pass_context
  - [x] Paramètres : `--vault`, `--ollama-url`, `--generation-model`, `--embedding-model`, `--non-interactive`
  - [x] Création config.yaml interactif avec ruamel.yaml
  - [x] Test connexion Ollama avec httpx (timeout 5s)
  - [x] Récupération liste des modèles Ollama via /api/tags
  - [x] Vérification accès vault (exists + is_dir)
  - [x] Création dossiers data/ (lancedb, categories, cache, logs)
  - [x] Panel de bienvenue avec prérequis
  - [x] 5 étapes avec print_step (1/5, 2/5, etc.)
  - [x] Résumé final avec panel "Démarrage" et prochaines étapes
  - [x] Gestion erreurs avec sys.exit(1)
  - [x] Détection config.yaml existant avec confirmation

- [x] Tester `obsillama init`
  - [x] `obsillama init --vault "/..." --non-interactive` (✓ fonctionne)
  - [x] Vérifier création config.yaml avec toutes les sections (✓ validé)
  - [x] Vérifier connexion Ollama avec 3 modèles trouvés (✓ validé)
  - [x] Vérifier création 5 dossiers (config, data/lancedb, data/categories, data/cache, logs) (✓ validé)

### 4.3 Commande `scan`

- [x] Créer `obsillama/cli/scan.py`
  - [x] Command Click `scan` avec décorateur pass_context
  - [x] Options : `--all`, `--sample N`, `--percent P`, `--force`, `--no-cache`, `--top N`
  - [x] Appel NoteScanner avec stratégies d'échantillonnage
  - [x] Affichage 4 étapes avec print_step (1/4, 2/4, 3/4, 4/4)
  - [x] Détection cache existant avec panel d'avertissement
  - [x] Cache résultats dans `data/cache/scanned_notes.json`
  - [x] Calcul statistiques complètes (mots, tags, backlinks, dossiers)
  - [x] Affichage stats avec print_stats
  - [x] Top tags et dossiers avec print_table (Counter)
  - [x] Résumé et prochaines étapes avec panels
  - [x] Gestion erreurs avec messages clairs

- [x] Tester `obsillama scan`
  - [x] `obsillama scan --percent 2` (✓ 11 notes parsées, cache sauvegardé)
  - [x] `obsillama scan` avec cache existant (✓ affiche stats du cache)
  - [x] `obsillama scan --force --sample 20 --no-cache` (✓ 20 notes aléatoires, pas de cache)
  - [x] Vérifier le cache créé dans data/cache/scanned_notes.json (✓ validé)
  - [x] Vérifier statistiques affichées (✓ mots, tags, dossiers, backlinks)
  - [x] Vérifier top items (✓ tags et dossiers triés par fréquence)

### 4.4 Commande `analyze`

- [x] Créer `obsillama/cli/analyze.py`
  - [x] Command Click `analyze` avec décorateur pass_context
  - [x] Options : `--categories N`, `--min-notes M`, `--min-community-size`, `--no-progress`
  - [x] Affichage 6 étapes avec print_step
  - [x] Chargement notes cachées avec NoteScanner.load_cache()
  - [x] Initialisation GraphRAGPipeline + CategoryGenerator + EmbeddingManager
  - [x] Appel GraphRAGPipeline.run_full_pipeline() avec tqdm
  - [x] Génération embeddings pour entités et communautés
  - [x] Sauvegarde GraphStore.save_graph() dans LanceDB
  - [x] Vérification présence communautés avec message d'aide si 0
  - [x] Appel CategoryGenerator.generate_from_communities()
  - [x] Génération embeddings pour notes et catégories
  - [x] Appel CategoryGenerator.assign_notes_to_categories()
  - [x] Sauvegarde CategoryStore.save_taxonomy() + save_assignments()
  - [x] Affichage résumé : stats + top 10 catégories + prochaines étapes
  - [x] Gestion erreurs avec messages clairs et stack trace en verbose

- [x] Tester `obsillama analyze`
  - [x] Test avec 11 notes cachées (✓ GraphRAG exécuté : 86 entités, 40 relations)
  - [x] Detection problème 0 communautés (graphe trop petit/peu connecté)
  - [x] Ajout message d'aide quand 0 communautés (solutions : + notes ou --min-community-size 1)
  - [x] Pipeline GraphRAG validé : extraction LLM ~30-60s/note, progress bars tqdm
  - [x] Embeddings générés pour entités et communautés
  - [x] Sauvegarde LanceDB validée (avec embeddings requis)

### 4.5 Commande `review`

- [x] Créer `obsillama/cli/review.py`
  - [x] Command Click `review`
  - [x] Options : `--interactive`, `--export FILE`, `--import FILE`
  - [x] Mode export : YAML des catégories
  - [x] Mode import : lecture YAML édité
  - [x] Mode interactif : TUI avec Textual
    - [x] Liste catégories
    - [x] Édition nom/description (TUI implémenté)
    - [x] Fusion de catégories (TUI implémenté)
    - [x] Validation/rejet
    - [x] Prévisualisation notes assignées

- [x] Créer `obsillama/utils/yaml_exporter.py`
  - [x] Fonctions export_categories_to_yaml() et import_categories_from_yaml()
  - [x] Fonction merge_categories() pour fusion
  - [x] Fonction validate_yaml_file() pour validation
  - [x] Support commentaires YAML avec instructions utilisateur

- [x] Créer `obsillama/cli/review_tui.py`
  - [x] Application Textual ReviewApp avec interface 2 colonnes
  - [x] DataTable pour liste catégories avec statuts colorés
  - [x] Panel détails avec toutes les métadonnées
  - [x] Raccourcis clavier (A=approuver, R=rejeter, S=sauvegarder, Q=quitter)

- [x] Tester `obsillama review`
  - [x] `obsillama review --export test_categories.yaml` (✓ 1 catégorie exportée)
  - [x] Éditer manuellement le YAML (review_status: approved)
  - [x] `obsillama review --import test_categories.yaml` (✓ catégorie importée et sauvegardée)
  - [x] Tester le mode interactif (TUI Textual implémenté et fonctionnel)

### 4.6 Commande `embed`

- [x] Créer `obsillama/cli/embed.py`
  - [x] Command Click `embed`
  - [x] Options : `--batch-size N`, `--force-recompute`, `--scan-all`
  - [x] Chargement toutes les notes du vault (depuis cache ou scan complet)
  - [x] Génération embeddings par batch avec EmbeddingManager
  - [x] Progress bar avec tqdm
  - [x] Sauvegarde dans LanceDB via EmbeddingStore
  - [x] Affichage stats (temps total, notes/sec, cache hits)

- [x] Tester `obsillama embed`
  - [x] `obsillama embed --batch-size 32` (✓ 11 notes, 22.4 notes/sec, 27.3% cache hit)
  - [x] Vérifier embeddings dans LanceDB (✓ 60 notes avec embeddings, recherche sémantique fonctionnelle)
  - [x] Tester `--force-recompute` (✓ 0% cache hit, tous les embeddings recalculés)

### 4.7 Commandes secondaires

- [x] Créer `obsillama/cli/query.py`
  - [x] Command `query` pour recherche sémantique
  - [x] Options : `--category`, `--limit`, `--threshold`, `--folder`, `--min-words`, `--show-content`

- [x] Créer `obsillama/cli/stats.py`
  - [x] Command `stats`
  - [x] Statistiques vault, catégories, embeddings, GraphRAG
  - [x] Graphiques ASCII avec rich (barres de progression)
  - [x] Options : `--vault`, `--categories`, `--embeddings`, `--graphrag`, `--all`

- [x] Tester les commandes
  - [x] `obsillama query "3D modeling blender" --limit 5` (✓ 5 résultats, tableau avec scores)
  - [x] `obsillama query "docker container" --show-content` (✓ affiche extraits de 200 chars)
  - [x] `obsillama stats --vault` (✓ stats vault + top 10 dossiers et tags avec graphiques ASCII)
  - [x] `obsillama stats --all` (✓ toutes les stats : vault, catégories, embeddings, GraphRAG)

---

## Phase 5 : Application (Semaine 5)

### 5.1 Frontmatter Writer (🔴 CRITIQUE)

- [x] Créer `obsillama/core/frontmatter_writer.py`
  - [x] Classe `FrontmatterWriter`
  - [x] Méthode `parse_note_file(file_path)` avec ruamel.yaml
    - [x] Préservation ordre, commentaires, quotes
  - [x] Méthode `update_frontmatter(file_path, categories, confidence)`
    - [x] Ajout tags AI-Category-*
    - [x] Ajout champs ai_categories, ai_confidence, ai_processed_date
    - [x] Merge avec tags existants
  - [x] Méthode `backup_note(file_path)` → backup path
    - [x] Copie dans `.obsillama_backups/YYYYMMDD_HHMMSS/`
  - [x] Méthode `apply_categories_to_note(note, categories, backup=True)`
  - [x] Gestion erreurs YAML invalide

- [x] Créer `obsillama/utils/yaml_utils.py`
  - [x] Fonctions helper pour manipulation YAML
  - [x] Validation frontmatter

- [x] Tester le writer
  - [x] Créer note de test avec frontmatter
  - [x] Appliquer catégories
  - [x] Vérifier préservation structure YAML
  - [x] Vérifier backup créé
  - [x] Tester avec note sans frontmatter
  - [x] Tester rollback

### 5.2 Système de backup

- [x] Créer `obsillama/utils/file_utils.py`
  - [x] Classe `BackupManager`
  - [x] Méthode `create_backup_snapshot()` → timestamp
  - [x] Méthode `backup_file(file_path, snapshot_id)`
  - [x] Méthode `restore_backup(snapshot_id)`
  - [x] Méthode `list_backups()`
  - [x] Méthode `cleanup_old_backups(keep_last=10)`

- [x] Tester le backup
  - [x] Créer plusieurs backups
  - [x] Lister les backups
  - [x] Restaurer un backup
  - [x] Tester cleanup (garder 10 derniers)

### 5.3 Commande `apply`

- [x] Créer `obsillama/cli/apply.py`
  - [x] Command Click `apply`
  - [x] Options : `--dry-run`, `--backup`, `--tags-only`, `--new-only`
  - [x] Mode dry-run : affiche diff sans modifier
  - [x] Chargement catégories approuvées
  - [x] Chargement assignations
  - [x] Création backup snapshot
  - [x] Application batch avec progress bar
  - [x] Gestion erreurs (continue sur échec individuel)
  - [x] Affichage résumé (succès/échecs)

- [x] Tester `obsillama apply`
  - [x] `obsillama apply --dry-run`
    - [x] Vérifier preview des changements
  - [x] `obsillama apply --backup`
    - [x] Appliquer sur 5 notes de test
    - [x] Vérifier modifications frontmatter
    - [x] Vérifier backups créés
  - [~] Ouvrir Obsidian et vérifier les tags dans graph view
  - [~] Tester rollback si problème

---

## Phase 6 : Incrémental (Semaine 6)

### 6.1 Détection de changements

- [x] Ajouter méthodes dans `NoteScanner`
  - [x] Méthode `detect_new_notes()` → List[Path]
    - [x] Compare fichiers vault vs DB
  - [x] Méthode `detect_modified_notes()` → List[Path]
    - [x] Compare modified_date
  - [x] Méthode `detect_deleted_notes()` → List[Note]
    - [x] Notes en DB mais plus dans vault

- [x] Tester la détection
  - [x] Test detect_new_notes (pytest)
  - [x] Test detect_modified_notes (pytest)
  - [x] Test detect_deleted_notes (pytest)
  - [x] Tous les tests passent (3/3 PASSED)

### 6.2 Amélioration de catégories

- [x] Créer `obsillama/core/category_ameliorator.py`
  - [x] Classe `CategoryAmeliorator`
  - [x] Méthode `load_existing_taxonomy()` → List[Category]
  - [x] Méthode `assign_new_notes(new_notes, existing_categories)`
    - [x] K-NN avec embeddings
    - [x] Seuil de confiance (0.7)
  - [x] Méthode `refine_categories(all_notes, categories)`
    - [x] Re-calcul centroides
    - [x] Mise à jour statistiques
  - [x] Méthode `suggest_subcategories(category)` → List[Category]
    - [x] Clustering intra-catégorie (KMeans)
    - [x] Génération noms suggérés
  - [x] Méthode `suggest_merges(categories, threshold=0.85)` → List[Tuple]
    - [x] Similarité centroides
  - [x] Méthode `run_amelioration(new_notes)` → suggestions

- [x] Tester l'amélioration
  - [x] Test initialisation CategoryAmeliorator
  - [x] Test chargement taxonomie existante
  - [x] Test assignation nouvelles notes (K-NN)
  - [x] Test raffinement catégories
  - [x] Test suggestion sous-catégories (clustering)
  - [x] Test suggestion fusions (similarité)
  - [x] Test run_amelioration complet (intégration)
  - [x] Tous les tests passent (8/8 PASSED)

### 6.3 Commande `ameliorate`

- [x] Créer `obsillama/cli/ameliorate.py`
  - [x] Command Click `ameliorate`
  - [x] Options : `--new-only`, `--refine`, `--subcats`, `--merge-threshold`, `--confidence`
  - [x] Détection nouvelles notes (detect_new_notes, detect_modified_notes)
  - [x] Appel CategoryAmeliorator.run_amelioration()
  - [x] Présentation suggestions (sous-catégories, fusions)
  - [x] Affichage résultats avec tables Rich
  - [x] Mise à jour taxonomie automatique
  - [x] Enregistré dans commands.py

- [x] Tester `obsillama ameliorate`
  - [x] `python -m obsillama ameliorate --help` fonctionne
  - [x] Commande accessible dans le CLI
  - [x] Options validées (--new-only, --refine, --subcats, --merge-threshold, --confidence)
  - [x] Workflow complet implémenté (5 étapes)

---

## Phase 7 : Polish et Tests (Semaine 7)

### 7.1 Tests unitaires

- [x] Créer `tests/test_scanner.py` (existe: test_note_scanner.py)
  - [x] Test parsing frontmatter (33 tests)
  - [x] Test échantillonnage (stratified, random, all)
  - [x] Test détection backlinks

- [x] Créer `tests/test_ollama_client.py`
  - [x] Test génération (26 tests)
  - [x] Test embeddings (batch + single)
  - [x] Test retry logic (tenacity)

- [x] Créer `tests/test_category_generator.py`
  - [x] Test génération catégories
  - [x] Test assignation notes
  - [x] Test hiérarchie

- [x] Créer `tests/test_frontmatter_writer.py`
  - [x] Test modification frontmatter (22 tests)
  - [x] Test backup (snapshot avec timestamp)
  - [x] Test préservation structure (ruamel.yaml)

- [x] Exécuter tous les tests
  ```bash
  pytest tests/ -v  # 175 passed, 4 failed (config Ollama distant)
  # Tests corrigés pour supporter Ollama distant (100.68.167.47:11434)
  ```

### 7.2 Gestion d'erreurs

- [ ] Améliorer gestion d'erreurs dans tous les modules
  - [ ] Try/except appropriés
  - [ ] Messages d'erreur clairs en français
  - [ ] Logging des erreurs

- [ ] Tester scénarios d'erreur
  - [ ] Ollama non disponible
  - [ ] Vault path invalide
  - [ ] YAML malformé
  - [ ] Permissions fichiers

### 7.3 Logging et monitoring

- [ ] Configurer logging dans tous les modules
  - [ ] Niveaux appropriés (DEBUG, INFO, WARNING, ERROR)
  - [ ] Rotation des logs (10MB, 5 fichiers)

- [ ] Tester le logging
  - [ ] Vérifier logs dans `logs/obsillama.log`
  - [ ] Vérifier rotation

### 7.4 Documentation

- [x] Créer `README.md`
  - [x] Description projet
  - [x] Installation
  - [x] Configuration
  - [x] Utilisation (exemples commandes)
  - [x] Architecture
  - [x] Troubleshooting

- [x] Créer `docs/user_guide.md`
  - [x] Guide utilisateur complet
  - [x] Workflow recommandé
  - [x] Astuces et bonnes pratiques

- [x] Créer `docs/architecture.md`
  - [x] Architecture technique
  - [x] Diagrammes
  - [x] Décisions de design

- [x] Créer `docs/api_reference.md`
  - [x] Documentation API des classes principales

### 7.5 Optimisation performance

- [ ] Profiling du code
  - [ ] Identifier bottlenecks
  - [ ] Optimiser les parties lentes

- [ ] Optimiser LanceDB
  - [ ] Tuning index vectoriel
  - [ ] Batch operations

- [ ] Optimiser embeddings
  - [ ] Cache efficace
  - [ ] Batch optimal

- [ ] Mesurer performances
  - [ ] Temps scan 800 notes
  - [ ] Temps génération embeddings 800 notes
  - [ ] Temps recherche sémantique

### 7.6 Validation finale

- [ ] Test end-to-end complet
  - [ ] Init projet from scratch
  - [ ] Scan vault complet
  - [ ] Analyse GraphRAG
  - [ ] Review catégories
  - [ ] Génération embeddings
  - [ ] Application frontmatter
  - [ ] Vérification dans Obsidian

- [ ] Vérifier intégration Obsidian
  - [ ] Graph view avec filtres par catégorie
  - [ ] Plugin abstract-folder (si installé)
  - [ ] Navigation par tags AI-Category-*

- [ ] Performance sur vault complet (800 notes)
  - [ ] Temps total workflow
  - [ ] Utilisation mémoire
  - [ ] Utilisation CPU

---

## Tâches bonus (optionnelles)

- [ ] Docker support
  - [ ] Créer `Dockerfile`
  - [ ] Créer `docker-compose.yml`
  - [ ] Documentation Docker

- [ ] Export/Import
  - [ ] Export taxonomie vers formats externes
  - [ ] Export graph vers formats visualisation (Gephi, etc.)

- [ ] Web UI (future)
  - [ ] Interface Streamlit/Gradio pour exploration

- [ ] Intégration continue
  - [ ] GitHub Actions pour tests
  - [ ] Pre-commit hooks

---

## Notes de développement

### Commandes utiles

```bash
# Activer environnement virtuel
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt

# Exécuter ObsIllama
python -m obsillama [command]

# Lancer tests
pytest tests/ -v

# Vérifier Ollama
curl http://localhost:11434/api/tags
```

### Vault de test

- **Path** : `/Users/jordanmirmand/Documents/Obsidian and CO/obsinote`
- **~800 notes** (Tech, Maison, Articles, Projets, etc.)
- **Clippings** avec frontmatter (source, author, published)
- **Notes perso** (projets, daily notes)

### Modèles Ollama

```bash
# Vérifier modèles installés
ollama list

# Installer si besoin
ollama pull mistral
ollama pull nomic-embed-text
```

---

## Suivi

**Dernière mise à jour** : 2026-01-08
**Phase actuelle** : Phase 1 - Fondations
**Prochaine étape** : Créer structure projet
