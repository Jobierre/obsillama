# ObsIllama 🦙📚

> **Système d'organisation intelligente de notes Obsidian avec GraphRAG + Ollama**

ObsIllama est un outil CLI qui utilise GraphRAG (Graph Retrieval-Augmented Generation) et Ollama pour analyser automatiquement votre vault Obsidian et générer une taxonomie de catégories intelligentes. Il extrait des entités et relations depuis vos notes, détecte des communautés thématiques, puis assigne des catégories AI avec embeddings sémantiques.

## ✨ Fonctionnalités principales

- 🔍 **GraphRAG Pipeline** : Extraction d'entités, relations, et détection de communautés avec l'algorithme Leiden
- 🏷️ **Génération automatique de catégories** : Création de taxonomies à partir des communautés détectées
- 🧠 **Embeddings sémantiques** : Génération d'embeddings vectoriels (768 dims) avec `nomic-embed-text`
- 🔎 **Recherche sémantique** : Requêtes par similarité vectorielle dans LanceDB
- ⚙️ **Application au vault** : Ajout automatique de tags et métadonnées dans le frontmatter
- 📊 **TUI interactif** : Interface Textual pour reviewer et éditer les catégories
- 🔄 **Mode incrémental** : Détection de nouvelles notes et amélioration continue de la taxonomie
- 💾 **Backups automatiques** : Snapshots horodatés avant toute modification du vault

## 🚀 Installation

### Prérequis

- **Python 3.11+** (testé avec Python 3.11)
- **Ollama** avec les modèles :
  - `mistral` (génération de texte)
  - `nomic-embed-text` (embeddings)
- **Vault Obsidian** existant

### Installation des dépendances

```bash
# Cloner le repo
git clone https://github.com/votre-username/obsillama.git
cd obsillama

# Créer un environnement virtuel
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Installer ObsIllama en mode éditable (optionnel)
pip install -e .
```

### Vérifier Ollama

```bash
# Vérifier que Ollama est accessible
curl http://localhost:11434/api/tags

# Installer les modèles si nécessaire
ollama pull mistral
ollama pull nomic-embed-text
```

## ⚙️ Configuration

### Initialisation du projet

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Initialiser ObsIllama de manière interactive
python -m obsillama init

# Ou avec des options directes
python -m obsillama init \
  --vault "/Users/vous/Documents/ObsidianVault" \
  --ollama-url "http://localhost:11434" \
  --non-interactive
```

Cela créera :
- Un fichier `config/config.yaml` avec toute la configuration
- Les dossiers nécessaires : `data/lancedb/`, `data/categories/`, `data/cache/`, `logs/`

### Fichier de configuration

Le fichier `config/config.yaml` contient toutes les options :

```yaml
vault:
  path: "/Users/vous/Documents/ObsidianVault"
  backup_path: ".obsillama_backups"
  exclude_folders:
    - ".obsidian"
    - ".trash"

ollama:
  base_url: "http://localhost:11434"
  models:
    generation: "mistral"
    embedding: "nomic-embed-text"
  params:
    temperature: 0.3
    max_tokens: 2000

graphrag:
  community_algorithm: "leiden"
  resolution: 1.0
  min_community_size: 3

categorization:
  target_count: 10
  thresholds:
    assignment_confidence: 0.7
    merge_similarity: 0.85

logging:
  level: "INFO"
  file: "logs/obsillama.log"
```

## 📖 Utilisation

### Workflow typique complet

```bash
# 1. Scanner le vault (échantillon ou complet)
python -m obsillama scan --percent 10  # Scanner 10% des notes
# ou
python -m obsillama scan --all  # Scanner toutes les notes

# 2. Analyser avec GraphRAG et générer les catégories
python -m obsillama analyze --categories 15

# 3. Générer les embeddings pour les notes
python -m obsillama embed --batch-size 32

# 4. Reviewer les catégories (mode interactif)
python -m obsillama review --interactive
# ou exporter en YAML pour édition manuelle
python -m obsillama review --export categories.yaml

# 5. Appliquer les catégories au vault (avec backup automatique)
python -m obsillama apply --backup --dry-run  # Preview
python -m obsillama apply --backup  # Application réelle

# 6. Requêtes sémantiques
python -m obsillama query "machine learning python" --limit 10

# 7. Statistiques du vault
python -m obsillama stats --all
```

### Commandes principales

#### `init` - Initialiser le projet

```bash
python -m obsillama init [OPTIONS]

Options:
  --vault PATH            Chemin vers le vault Obsidian
  --ollama-url URL        URL de l'API Ollama (défaut: http://localhost:11434)
  --generation-model TEXT Modèle de génération (défaut: mistral)
  --embedding-model TEXT  Modèle d'embedding (défaut: nomic-embed-text)
  --non-interactive       Mode non-interactif
```

#### `scan` - Scanner les notes du vault

```bash
python -m obsillama scan [OPTIONS]

Options:
  --all               Scanner toutes les notes
  --sample N          Scanner N notes aléatoires
  --percent P         Scanner P% des notes
  --force             Forcer un nouveau scan même si cache existe
  --no-cache          Ne pas sauvegarder le cache
  --top N             Afficher top N tags/dossiers (défaut: 10)
```

#### `analyze` - Pipeline GraphRAG et génération de catégories

```bash
python -m obsillama analyze [OPTIONS]

Options:
  --categories N           Nombre de catégories cibles
  --min-notes M            Minimum de notes par catégorie
  --min-community-size N   Taille minimum d'une communauté
  --no-progress            Désactiver les barres de progression
```

#### `review` - Reviewer et éditer les catégories

```bash
python -m obsillama review [OPTIONS]

Options:
  --interactive          Mode TUI interactif (Textual)
  --export FILE          Exporter en YAML
  --import FILE          Importer depuis YAML édité
```

#### `embed` - Générer les embeddings

```bash
python -m obsillama embed [OPTIONS]

Options:
  --batch-size N       Taille des batchs (défaut: 32)
  --force-recompute    Recalculer tous les embeddings
  --scan-all           Scanner toutes les notes (pas seulement le cache)
```

#### `apply` - Appliquer les catégories au vault

```bash
python -m obsillama apply [OPTIONS]

Options:
  --dry-run          Prévisualiser sans modifier
  --backup           Créer un snapshot de backup (recommandé)
  --tags-only        Ajouter seulement les tags, pas les métadonnées AI
  --new-only         Appliquer seulement aux notes non traitées
```

#### `query` - Recherche sémantique

```bash
python -m obsillama query "TEXTE" [OPTIONS]

Options:
  --category CAT      Filtrer par catégorie
  --limit N           Nombre de résultats (défaut: 10)
  --threshold FLOAT   Seuil de similarité (0.0-1.0)
  --folder PATH       Filtrer par dossier
  --min-words N       Nombre minimum de mots
  --show-content      Afficher des extraits de contenu
```

#### `stats` - Statistiques du vault

```bash
python -m obsillama stats [OPTIONS]

Options:
  --vault        Stats du vault
  --categories   Stats des catégories
  --embeddings   Stats des embeddings
  --graphrag     Stats du graphe
  --all          Toutes les stats
```

#### `ameliorate` - Amélioration incrémentale

```bash
python -m obsillama ameliorate [OPTIONS]

Options:
  --new-only           Traiter seulement les nouvelles notes
  --refine             Raffiner les catégories existantes
  --subcats            Suggérer des sous-catégories
  --merge-threshold F  Seuil de similarité pour fusion (défaut: 0.85)
  --confidence F       Seuil de confiance (défaut: 0.7)
```

## 🏗️ Architecture

```
obsillama/
├── cli/              # Commandes Click CLI
│   ├── commands.py   # Groupe principal + contexte
│   ├── init.py       # Initialisation
│   ├── scan.py       # Scanner de notes
│   ├── analyze.py    # Pipeline GraphRAG
│   ├── review.py     # Review des catégories
│   ├── embed.py      # Génération embeddings
│   ├── apply.py      # Application au vault
│   ├── query.py      # Recherche sémantique
│   ├── stats.py      # Statistiques
│   └── ameliorate.py # Amélioration incrémentale
│
├── core/             # Logique métier
│   ├── note_scanner.py         # Parsing notes + frontmatter
│   ├── category_generator.py   # Génération catégories
│   ├── category_ameliorator.py # Amélioration taxonomie
│   ├── embedding_manager.py    # Gestion embeddings + cache
│   ├── frontmatter_writer.py   # Modification YAML safe
│   └── frontmatter_parser.py   # Parsing frontmatter
│
├── llm/              # Intégration LLM
│   ├── ollama_client.py        # Client Ollama avec retry
│   ├── graphrag_integration.py # Pipeline GraphRAG complet
│   └── prompts/                # Prompts français
│       ├── categorization.py
│       ├── analysis.py
│       └── refinement.py
│
├── storage/          # Persistance
│   ├── lancedb_manager.py  # Gestion LanceDB
│   ├── embedding_store.py  # Recherche vectorielle
│   ├── graph_store.py      # Stockage graphe
│   └── category_store.py   # Stockage taxonomie (JSON)
│
├── models/           # Modèles Pydantic
│   ├── note.py
│   ├── category.py
│   ├── embedding.py
│   └── graph_entity.py
│
├── config/           # Configuration
│   └── settings.py   # Modèle Pydantic config
│
└── utils/            # Utilitaires
    ├── progress.py   # Rich UI helpers
    ├── file_utils.py # BackupManager
    └── yaml_utils.py # YAML helpers
```

### Pipeline GraphRAG

```
Notes → Extraction Entités → Construction Graphe → Détection Communautés
            (LLM)                  (igraph)              (Leiden)
                                                              ↓
                                                      Résumés LLM
                                                              ↓
                                                     Génération Catégories
                                                              ↓
                                                      Assignation Notes
                                                        (Embeddings)
```

## 🐛 Troubleshooting

### Ollama non disponible

```bash
# Vérifier qu'Ollama tourne
curl http://localhost:11434/api/tags

# Si erreur, démarrer Ollama
ollama serve

# Vérifier les modèles installés
ollama list

# Installer les modèles si manquants
ollama pull mistral
ollama pull nomic-embed-text
```

### Erreurs de mémoire (OOM) lors de l'analyse

Si vous obtenez des erreurs mémoire avec un gros vault :

```bash
# Analyser par étapes avec échantillons
python -m obsillama scan --percent 5  # Commencer petit
python -m obsillama analyze --min-community-size 5  # Augmenter seuil

# Réduire le batch size des embeddings
python -m obsillama embed --batch-size 8
```

### Problèmes de parsing YAML

ObsIllama utilise `ruamel.yaml` pour préserver la structure YAML. Si vous avez des erreurs :

- Vérifiez que vos frontmatters sont valides YAML
- Les backups sont dans `.obsillama_backups/` si besoin de restauration
- Utilisez `--dry-run` avant d'appliquer pour prévisualiser

### Pas de communautés détectées

```
Aucune communauté détectée (graphe trop petit ou peu connecté)
```

Solutions :
- Scannez plus de notes : `--sample 50` au lieu de `--percent 2`
- Réduisez le seuil : `--min-community-size 1`
- Vérifiez que les notes ont du contenu substantiel

### Problèmes de configuration

```bash
# Réinitialiser la config
rm -rf config/config.yaml data/ logs/
python -m obsillama init
```

### Tests

```bash
# Lancer tous les tests
pytest tests/ -v

# Tests spécifiques
pytest tests/test_note_scanner.py -v
pytest tests/test_frontmatter_writer.py -v

# Avec coverage
pytest tests/ --cov=obsillama --cov-report=html
```

## 📊 Exemple de résultat

Après l'application au vault, vos notes Obsidian auront un frontmatter enrichi :

```yaml
---
title: "Ma note sur Docker"
tags:
  - docker
  - AI-Category-DevOps
  - AI-Category-Containerization
ai_categories:
  - DevOps
  - Containerization
ai_confidence: 0.87
ai_processed_date: 2026-01-11T22:30:00
ai_version: "1.0.0"
---

# Contenu de la note
...
```

Vous pouvez ensuite utiliser ces tags dans Obsidian :
- Graph view filtré par `#AI-Category-*`
- Requêtes Dataview : `FROM #AI-Category-DevOps`
- Plugin abstract-folder pour navigation

## 🤝 Contribution

Les contributions sont bienvenues ! Voir `CONTRIBUTING.md` pour les guidelines.

## 📝 License

MIT License - voir `LICENSE` pour détails

## 🙏 Remerciements

- [Ollama](https://ollama.ai/) pour l'exécution locale des LLMs
- [LanceDB](https://lancedb.com/) pour le stockage vectoriel
- [igraph](https://igraph.org/) pour les algorithmes de graphe
- [Textual](https://textual.textualize.io/) pour le TUI
- La communauté Obsidian

---

**Développé par** : Jobierre
**Statut** : Phase 7 - Polish et Tests
**Version** : 1.0.0-beta
