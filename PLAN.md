# Plan d'implémentation : ObsIllama

## Vue d'ensemble

**ObsIllama** est un système local d'organisation intelligente de notes Obsidian utilisant GraphRAG, LanceDB et Ollama pour catégoriser automatiquement 800+ notes markdown via analyse sémantique et graphe de connaissances.

### Configuration cible
- **Vault Obsidian** : `/Users/jordanmirmand/Documents/Obsidian and CO/obsinote`
- **Projet** : `/Users/jordanmirmand/code/obsillama` (vide, prêt)
- **Hardware** : MacBook Air M4, Ollama installé
- **Interface** : CLI (ligne de commande)
- **Modèles** : Mistral (génération) + nomic-embed-text (embeddings)
- **Base de données** : LanceDB (vecteurs + métadonnées)

---

## Architecture du projet

### Structure des dossiers

```
obsillama/
├── obsillama/                      # Package Python principal
│   ├── cli/                        # Interface ligne de commande
│   │   ├── commands.py             # Commandes Click
│   │   ├── scan.py                 # Scan du vault
│   │   ├── analyze.py              # Analyse GraphRAG
│   │   ├── review.py               # Interface de révision
│   │   ├── embed.py                # Génération embeddings
│   │   ├── apply.py                # Application au frontmatter
│   │   └── ameliorate.py           # Mode amélioration
│   ├── core/                       # Logique métier
│   │   ├── note_scanner.py         # 🔴 CRITIQUE - Scan des notes
│   │   ├── frontmatter_parser.py   # Parsing YAML
│   │   ├── category_generator.py   # Génération catégories
│   │   ├── embedding_manager.py    # Gestion embeddings
│   │   ├── graph_builder.py        # Construction graphe
│   │   └── frontmatter_writer.py   # 🔴 CRITIQUE - Écriture sécurisée
│   ├── llm/                        # Intégration LLM
│   │   ├── ollama_client.py        # 🔴 CRITIQUE - Client Ollama
│   │   ├── graphrag_integration.py # 🔴 CRITIQUE - Pipeline GraphRAG
│   │   └── prompts/                # Templates de prompts
│   │       ├── categorization.py   # Prompts FR pour catégorisation
│   │       ├── analysis.py         # Prompts d'analyse
│   │       └── refinement.py       # Prompts amélioration
│   ├── storage/                    # Persistance
│   │   ├── lancedb_manager.py      # 🔴 CRITIQUE - Gestion LanceDB
│   │   ├── category_store.py       # Base catégories
│   │   ├── embedding_store.py      # Stockage embeddings
│   │   └── graph_store.py          # Stockage graphe
│   ├── models/                     # Modèles de données
│   │   ├── note.py                 # Structure Note
│   │   ├── category.py             # Structure Catégorie
│   │   ├── embedding.py            # Structure Embedding
│   │   └── graph_entity.py         # Entités/relations GraphRAG
│   ├── utils/                      # Utilitaires
│   │   ├── file_utils.py
│   │   ├── yaml_utils.py
│   │   └── progress.py
│   └── config/
│       └── settings.py             # Configuration
├── data/                           # Données locales
│   ├── lancedb/                    # Base de données
│   │   ├── notes.lance
│   │   ├── categories.lance
│   │   ├── entities.lance
│   │   └── communities.lance
│   ├── categories/
│   │   ├── taxonomy.json           # Hiérarchie catégories
│   │   └── assignments.json        # Assignations
│   └── cache/                      # Cache temporaire
├── config/
│   └── config.yaml                 # Configuration utilisateur
├── logs/
│   └── obsillama.log
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Flux de données

### Phase 1 : Scan initial
```
Vault Obsidian → Note Scanner → Frontmatter Parser → Cache JSON
```

### Phase 2 : Analyse GraphRAG + Catégorisation
```
Notes en cache → GraphRAG Builder → Extraction entités/relations
                                   ↓
                            Détection communautés
                                   ↓
Ollama (mistral) ← Générateur catégories ← Contexte graphe
                         ↓
                  Catégories suggérées → LanceDB (categories.lance)
```

### Phase 3 : Embeddings
```
Contenu notes → Ollama (nomic-embed-text) → Embeddings → LanceDB (notes.lance)
```

### Phase 4 : Révision & application
```
LanceDB → Interface CLI → Édition utilisateur → Frontmatter Writer
                                                       ↓
                                                 Backup + Update YAML
```

### Phase 5 : Amélioration incrémentale
```
Nouvelles notes → Détection diff → Catégories existantes → Refinement
                                                                 ↓
                                                     Sous-catégories auto
```

---

## Commandes CLI principales

### `obsillama init`
Initialise le projet : config, connexion Ollama, création dossiers

```bash
obsillama init --vault "/Users/jordanmirmand/Documents/Obsidian and CO/obsinote"
```

### `obsillama scan`
Scan le vault, parse les notes, cache les métadonnées

```bash
obsillama scan --percent 15      # Scan 15% des notes
obsillama scan --sample 100      # Scan 100 notes exactement
obsillama scan --all             # Scan toutes les notes
```

### `obsillama analyze`
Construit le graphe de connaissances et génère les catégories

```bash
obsillama analyze --categories 20 --min-notes 5
```

### `obsillama review`
Interface interactive de révision des catégories

```bash
obsillama review --interactive
obsillama review --export categories.yaml    # Export pour édition manuelle
obsillama review --import categories.yaml    # Import après édition
```

### `obsillama embed`
Génère les embeddings pour toutes les notes

```bash
obsillama embed --batch-size 32
```

### `obsillama apply`
Applique les catégories au frontmatter

```bash
obsillama apply --dry-run      # Prévisualisation
obsillama apply --backup       # Avec backup timestampé
```

### `obsillama ameliorate`
Mode amélioration pour nouvelles notes et raffinement

```bash
obsillama ameliorate --new-only    # Seulement nouvelles notes
obsillama ameliorate --refine      # Raffine catégories existantes
obsillama ameliorate --subcats     # Crée sous-catégories auto
```

### `obsillama query`
Recherche sémantique dans les notes

```bash
obsillama query "self-hosting docker"
obsillama query --category "Tech" --limit 10
```

### `obsillama stats`
Statistiques du vault et des catégories

```bash
obsillama stats
obsillama stats --categories
```

---

## Schéma de base de données (LanceDB)

### Table `notes`
```python
{
    "id": str,                      # UUID
    "file_path": str,               # Chemin absolu
    "relative_path": str,           # Relatif au vault
    "title": str,
    "content": str,                 # Markdown complet
    "content_no_frontmatter": str,  # Sans YAML
    "embedding": List[float],       # Vecteur 768-dim
    "created_date": datetime,
    "modified_date": datetime,
    "existing_tags": List[str],     # Tags actuels
    "ai_categories": List[str],     # Catégories AI assignées
    "backlinks": List[str],
    "source_url": str,              # Pour clippings
    "author": List[str],
    "word_count": int,
    "graph_entities": List[str],    # Entités GraphRAG
    "graph_communities": List[int], # IDs communautés
    "processed": bool,
    "applied": bool                 # Catégories appliquées ?
}
```

### Table `categories`
```python
{
    "id": str,
    "name": str,                    # Ex: "Tech-Docker"
    "display_name": str,
    "description": str,             # Générée par LLM
    "parent_category": str,         # ID parent (null si racine)
    "subcategories": List[str],     # IDs enfants
    "tag_name": str,                # "AI-Category-Tech-Docker"
    "assigned_notes": List[str],    # IDs des notes
    "example_notes": List[str],     # Top 5 représentatives
    "keywords": List[str],
    "confidence_score": float,
    "review_status": str,           # "pending", "approved", "rejected"
    "user_modified": bool,
    "graph_community_ids": List[int],
    "note_count": int
}
```

### Table `graph_entities`
```python
{
    "id": str,
    "name": str,
    "type": str,                    # "person", "technology", "project"...
    "description": str,
    "source_notes": List[str],
    "embedding": List[float],
    "community_id": int,
    "relationships": List[dict],    # {target_id, type, weight}
    "importance_score": float
}
```

### Table `graph_communities`
```python
{
    "id": int,
    "name": str,
    "description": str,             # Résumé LLM
    "entities": List[str],
    "notes": List[str],
    "suggested_category": str,      # ID catégorie
    "coherence_score": float
}
```

---

## Configuration (config.yaml)

```yaml
vault:
  path: "/Users/jordanmirmand/Documents/Obsidian and CO/obsinote"
  backup_path: "${vault.path}/.obsillama_backups"
  exclude_folders: [".trash", ".obsidian", "templates"]

ollama:
  base_url: "http://localhost:11434"
  generation_model: "mistral"
  embedding_model: "nomic-embed-text"
  timeout: 300
  generation_params:
    temperature: 0.3
    top_p: 0.9
    max_tokens: 2048
  embedding_params:
    batch_size: 32

graphrag:
  enabled: true
  community_detection_algorithm: "leiden"
  min_community_size: 3
  entity_types:
    - "technology"
    - "project"
    - "person"
    - "concept"
    - "tool"
    - "organization"

categorization:
  target_category_count: 20
  min_notes_per_category: 5
  max_category_depth: 3
  tag_prefix: "AI-Category-"
  sample_strategy: "stratified"
  sample_percentage: 15
  confidence_threshold: 0.7

incremental:
  enabled: true
  track_new_notes: true
  auto_ameliorate: false
  subcategory_threshold: 20   # Créer sous-cat si parent > 20 notes

frontmatter:
  preserve_existing: true
  fields_to_add:
    - "ai_categories"
    - "ai_confidence"
    - "ai_processed_date"
  merge_strategy: "append"
  backup_before_modify: true

lancedb:
  path: "${project_root}/data/lancedb"
  vector_index_type: "IVF_PQ"
  nprobes: 20

processing:
  parallel_workers: 4
  batch_size: 50
  cache_enabled: true

logging:
  level: "INFO"
  file: "${project_root}/logs/obsillama.log"

language:
  primary: "fr"
```

---

## Stratégie GraphRAG

### Pourquoi GraphRAG + Embeddings ?

**Embeddings seuls** : similarité sémantique mais manque contexte relationnel

**GraphRAG ajoute** :
- Extraction d'entités (technologies, personnes, projets)
- Relations explicites (utilise, dépend-de, lié-à)
- Détection de communautés (clusters de concepts)
- Raisonnement multi-sauts

**Approche combinée** :
- GraphRAG → compréhension structurelle → hiérarchie catégories
- Embeddings → similarité sémantique → assignation notes
- Résultat : catégories cohérentes, hiérarchiques, sémantiquement groupées

### Pipeline GraphRAG

1. **Extraction entités** : LLM analyse chaque note pour extraire entités nommées
2. **Extraction relations** : LLM identifie liens entre entités
3. **Construction graphe** : Création graphe de connaissances
4. **Détection communautés** : Algorithme Leiden pour clustering
5. **Mapping catégories** : Communautés → catégories suggérées

---

## Modification frontmatter sécurisée

### Principes
- ✅ **JAMAIS modifier le contenu** des notes (seulement YAML frontmatter)
- ✅ **Toujours créer backup** avant modification
- ✅ **Préserver structure existante** (ordre, commentaires, quotes)
- ✅ **Mode dry-run** pour prévisualisation

### Format cible

```yaml
---
title: Ma note
source: https://example.com
author:
  - "[[Auteur]]"
published: 2025-12-19
created: 2025-12-19
description: Description...
tags:
  - clippings                    # Existant préservé
  - AI-Category-Tech             # ← Ajouté par ObsIllama
  - AI-Category-SelfHosting      # ← Ajouté par ObsIllama
ai_categories:                   # ← Nouveau champ
  - Tech
  - SelfHosting
ai_processed_date: 2026-01-07T22:30:00
ai_confidence: 0.89
---

Contenu de la note inchangé...
```

### Process de mise à jour

1. Lecture fichier complet
2. Parsing YAML avec `ruamel.yaml` (préserve formatting)
3. Ajout tags `AI-Category-XXX` (merge avec existants)
4. Ajout métadonnées AI
5. Backup original → `.obsillama_backups/YYYYMMDD_HHMMSS/`
6. Écriture nouveau contenu

---

## Stratégie incrémentale & amélioration

### Détection nouvelles notes

```python
# Compare fichiers vault vs base LanceDB
new_notes = scan_vault_files() - get_known_note_paths()
modified_notes = [n for n in known if file_mtime(n) > db_mtime(n)]
```

### Mode "Amélioration"

**Objectifs** :
1. Intégrer nouvelles notes sans recommencer de zéro
2. Raffiner catégories existantes
3. Créer sous-catégories si spécialisation émerge
4. Fusionner catégories similaires

**Workflow** :
1. Scan nouvelles notes
2. Chargement taxonomie existante
3. Pour chaque nouvelle note :
   - Génération embedding
   - Recherche K-NN dans catégories existantes
   - Assignation si confiance > seuil
   - Sinon → flagué pour révision
4. Analyse catégories surchargées → proposition sous-catégories
5. Calcul similarité inter-catégories → fusion si >0.85
6. Présentation suggestions → validation utilisateur

### Création sous-catégories

Si catégorie parent > 20 notes :
1. Clustering des notes dans la catégorie
2. Génération noms sous-catégories via LLM
3. Proposition utilisateur
4. Création hiérarchie `Tech` → `Tech-Docker`, `Tech-Kubernetes`

---

## Dépendances Python

### requirements.txt

```
# GraphRAG et graphes
graphrag==2.7.0
lancedb==0.15.0
igraph==0.11.8

# LLM
ollama==0.4.2
langchain==0.3.15

# CLI et UI
click==8.1.7
rich==13.7.1
textual==0.85.0
tqdm==4.67.1

# Parsing et data
ruamel.yaml==0.18.6
python-frontmatter==1.1.0
pydantic==2.9.2
pandas==2.2.2
numpy==1.26.4

# Utilitaires
scikit-learn==1.5.2
tenacity==9.0.0
chardet==5.2.0
pathlib2==2.3.7
```

---

## Exemple d'utilisation complète

### Setup initial

```bash
cd /Users/jordanmirmand/code/obsillama

# Initialisation
obsillama init --vault "/Users/jordanmirmand/Documents/Obsidian and CO/obsinote"

# Scan 15% du vault (échantillonnage stratifié)
obsillama scan --percent 15
# → Scanne ~120 notes sur 800

# Analyse GraphRAG + génération 20 catégories
obsillama analyze --categories 20
# → Construit graphe de connaissances
# → Détecte communautés
# → Génère catégories suggérées

# Révision interactive
obsillama review --interactive
# → Interface TUI pour éditer catégories
# → Utilisateur approuve 18, rejette 2, fusionne 3

# Génération embeddings pour TOUTES les notes
obsillama embed
# → 800 notes → embeddings nomic-embed-text

# Prévisualisation modifications
obsillama apply --dry-run
# → Affiche diff YAML

# Application finale
obsillama apply --backup
# → Backup dans .obsillama_backups/
# → Modification frontmatter

# Stats
obsillama stats --categories
```

### Après 2 semaines : 50 nouvelles notes

```bash
# Détection + amélioration
obsillama ameliorate --refine --subcats
# → Détecte 50 nouvelles notes
# → Réutilise catégories existantes
# → Assigne nouvelles notes
# → Propose 2 sous-catégories (Tech-Docker trop grande)

# Révision changements
obsillama review --new-only

# Application
obsillama apply --new-only
```

---

## Intégration Obsidian

### Plugin abstract-folder

Après catégorisation, configure le plugin :

```yaml
# .obsidian/plugins/abstract-folder/config.yaml
folders:
  - name: "📚 Tech"
    filter:
      tags: ["AI-Category-Tech*"]

  - name: "🏠 Maison"
    filter:
      tags: ["AI-Category-Maison*"]

  - name: "📰 Articles"
    filter:
      tags: ["AI-Category-Articles*"]
```

### Graph View

- Filtrage par tags AI-Category-*
- Coloration par catégorie
- Navigation arborescente virtuelle

---

## Optimisations performance

### Caching
- Cache notes parsées (évite re-lecture)
- Cache embeddings (hash contenu)
- Cache entités GraphRAG

### Traitement batch
- Notes : batches de 50
- Embeddings : batches de 32
- Inserts LanceDB : bulk insert

### Parallélisation
- ThreadPoolExecutor pour I/O (lecture fichiers, API Ollama)
- 4 workers par défaut (configurable)

### Index LanceDB
- IVF_PQ pour >10K vecteurs
- Index métadonnées sur `ai_categories`, `modified_date`

---

## Sécurité & résilience

### Backups
- **Toujours** backup avant modification
- Structure : `.obsillama_backups/YYYYMMDD_HHMMSS/relative/path.md`
- Rotation : garder 10 derniers backups

### Gestion erreurs
- Retry avec exponential backoff pour Ollama
- Validation YAML avant écriture
- Rollback si échec application batch

### Logs
- INFO : opérations normales
- WARNING : catégories faible confiance
- ERROR : échecs Ollama, parsing YAML
- Rotation logs : 10MB max, 5 fichiers

---

## Fichiers critiques à créer

### 🔴 Top 5 prioritaires

1. **`obsillama/core/note_scanner.py`**
   - Scan vault Obsidian
   - Parse frontmatter
   - Cache métadonnées

2. **`obsillama/llm/ollama_client.py`**
   - Wrapper API Ollama
   - Génération (mistral)
   - Embeddings (nomic-embed-text)
   - Retry logic

3. **`obsillama/storage/lancedb_manager.py`**
   - Abstraction LanceDB
   - CRUD pour notes, catégories, entités
   - Gestion index vectoriels

4. **`obsillama/llm/graphrag_integration.py`**
   - Pipeline GraphRAG
   - Extraction entités/relations
   - Détection communautés
   - Génération catégories

5. **`obsillama/core/frontmatter_writer.py`**
   - Modification YAML sécurisée
   - Backup automatique
   - Préservation structure

### 📦 Ensuite

6. `obsillama/cli/commands.py` - Structure CLI Click
7. `obsillama/core/category_generator.py` - Logique catégorisation
8. `obsillama/core/embedding_manager.py` - Gestion embeddings
9. `obsillama/models/*.py` - Modèles Pydantic
10. `config/config.yaml` - Configuration par défaut

---

## Roadmap implémentation

### Semaine 1 : Fondations
- [ ] Structure projet + scaffolding
- [ ] Configuration système
- [ ] Note scanner + frontmatter parser
- [ ] Client Ollama basique
- [ ] LanceDB setup

### Semaine 2 : GraphRAG
- [ ] Pipeline GraphRAG
- [ ] Extraction entités
- [ ] Détection communautés
- [ ] Générateur catégories
- [ ] Stockage LanceDB

### Semaine 3 : Embeddings
- [ ] Pipeline embeddings
- [ ] Batch processing
- [ ] Stockage vectoriel
- [ ] Recherche sémantique

### Semaine 4 : CLI
- [ ] Commandes Click
- [ ] Interface révision (Textual)
- [ ] Dry-run
- [ ] Progress bars

### Semaine 5 : Application
- [ ] Frontmatter writer
- [ ] Backup système
- [ ] Batch application
- [ ] Rollback

### Semaine 6 : Incrémental
- [ ] Détection nouvelles notes
- [ ] Réutilisation catégories
- [ ] Mode amélioration
- [ ] Sous-catégories auto

### Semaine 7 : Polish
- [ ] Tests
- [ ] Documentation
- [ ] Gestion erreurs
- [ ] Optimisation performance

---

## Points d'attention

### ⚠️ Langue française
- Tous prompts en français
- Mistral gère bien le français
- Tester avec accents, cédilles

### ⚠️ Structure existante vault
- Respecter dossiers physiques (01-Projets, etc.)
- NE PAS déplacer fichiers
- Tags virtuels via abstract-folder

### ⚠️ Clippings vs notes perso
- Clippings : `source`, `author`, `published`
- Notes perso : projets, daily notes
- GraphRAG distinguera naturellement

### ⚠️ Coût GraphRAG
- Extraction entités = 1 appel LLM/note
- Cache agressif
- Rebuild graphe seulement si nécessaire

### ⚠️ Apple Silicon
- Ollama optimisé M4
- Metal acceleration
- Embeddings rapides

---

## Résumé exécutif

ObsIllama combinera :
1. **GraphRAG** pour comprendre relations et communautés
2. **Embeddings** pour similarité sémantique
3. **LLM local** (Mistral) pour génération catégories
4. **LanceDB** pour stockage performant
5. **CLI** pour contrôle utilisateur
6. **Frontmatter tags** pour intégration Obsidian

Le système sera :
- ✅ 100% local (privacy)
- ✅ Non-destructif (backup systématique)
- ✅ Incrémental (réutilise données)
- ✅ Contrôlable (révision manuelle)
- ✅ Évolutif (amélioration continue)

**Prochaine étape** : Création structure projet et implémentation des 5 fichiers critiques.
