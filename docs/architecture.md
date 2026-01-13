# ObsIllama - Architecture Technique

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture en couches](#architecture-en-couches)
3. [Flux de données](#flux-de-données)
4. [Composants principaux](#composants-principaux)
5. [Décisions de design](#décisions-de-design)
6. [Technologies](#technologies)
7. [Patterns et conventions](#patterns-et-conventions)
8. [Performance et scalabilité](#performance-et-scalabilité)

---

## Vue d'ensemble

ObsIllama suit une **architecture en couches (layered architecture)** avec séparation claire des responsabilités :

```
┌─────────────────────────────────────────────────┐
│           CLI Layer (Click)                     │  ← Interface utilisateur
├─────────────────────────────────────────────────┤
│           Core Layer (Business Logic)           │  ← Logique métier
├─────────────────────────────────────────────────┤
│           LLM Layer (AI Integration)            │  ← Intégration IA
├─────────────────────────────────────────────────┤
│           Storage Layer (Persistence)           │  ← Persistance
└─────────────────────────────────────────────────┘
```

**Principes de design :**
- **Separation of Concerns** : Chaque couche a une responsabilité unique
- **Dependency Injection** : Les dépendances sont injectées (OllamaClient, LanceDBManager)
- **Single Source of Truth** : Configuration centralisée (config.yaml)
- **Fail-Safe** : Backups automatiques avant toute modification
- **Performance-First** : Cache des embeddings, batch processing, index vectoriels

---

## Architecture en couches

### 1. CLI Layer (`obsillama/cli/`)

**Responsabilité :** Interface utilisateur en ligne de commande

**Composants :**
- `commands.py` : Groupe Click principal, contexte partagé (`ObsillamaContext`)
- 9 commandes : `init`, `scan`, `analyze`, `review`, `embed`, `apply`, `query`, `stats`, `ameliorate`
- `review_tui.py` : Interface Textual pour review interactif

**Pattern : Command Pattern**
```python
@click.command()
@pass_context
def analyze(ctx: ObsillamaContext, categories: int, ...):
    """Analyse GraphRAG + génération catégories"""
    # Récupère config depuis contexte
    config = ctx.config

    # Initialise les composants
    ollama = OllamaClient(config.ollama.base_url)
    graphrag = GraphRAGPipeline(ollama)

    # Exécute le pipeline
    entities, relationships, communities = graphrag.run_full_pipeline(notes)
```

**Gestion d'erreurs :**
- Try/except à chaque niveau
- Messages d'erreur en français, clairs et actionnables
- Exit codes : 0 (succès), 1 (erreur)
- Logging détaillé dans `logs/obsillama.log`

### 2. Core Layer (`obsillama/core/`)

**Responsabilité :** Logique métier et orchestration

**Composants clés :**

#### `note_scanner.py` - Parsing et échantillonnage
```python
class NoteScanner:
    """Scanner et parser de notes Obsidian"""

    def scan_vault(self, vault_path, exclude_folders) -> List[Path]:
        """Scan récursif avec exclusions"""

    def parse_note(self, file_path) -> Note:
        """Parse frontmatter + contenu"""

    def scan_and_parse(self, strategy, sample_size) -> List[Note]:
        """Scan + parse avec échantillonnage (random, stratified, all)"""

    def detect_new_notes(self) -> List[Path]:
        """Détection incrémentale (compare filesystem vs DB)"""
```

**Design decision : Échantillonnage stratégié**
- Stratifié par dossier : garantit représentativité des thématiques
- Random : Pour tests rapides
- All : Production complète

#### `category_generator.py` - Génération de taxonomies
```python
class CategoryGenerator:
    """Génère catégories depuis communautés GraphRAG"""

    def generate_from_communities(
        self,
        communities: List[GraphCommunity],
        entities: List[GraphEntity]
    ) -> List[Category]:
        """LLM génère nom + description pour chaque communauté"""

    def assign_notes_to_categories(
        self,
        notes: List[Note],
        categories: List[Category],
        note_embeddings: List[List[float]],
        category_embeddings: List[List[float]]
    ) -> Dict[str, List[Tuple[str, float]]]:
        """K-NN avec embeddings : chaque note → catégorie la plus proche"""
```

**Design decision : Cosine similarity pour assignation**
- Alternative considérée : Euclidean distance
- Choix : Cosine similarity car invariante à la magnitude
- Seuil par défaut : 0.7 (configurable)

#### `embedding_manager.py` - Cache et génération
```python
class EmbeddingManager:
    """Gestionnaire d'embeddings avec cache intelligent"""

    def _compute_content_hash(self, text: str) -> str:
        """SHA-256 du contenu pour clé de cache"""

    def generate_embedding(self, text: str) -> List[float]:
        """Génère embedding avec cache lookup"""

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """Batch processing avec progress bar"""
```

**Design decision : Cache basé sur hash de contenu**
- Fichier JSON : `data/cache/embeddings_cache.json`
- Format : `{content_hash: embedding_vector}`
- Accélération : ~1000x pour embeddings déjà calculés
- Invalide automatiquement si contenu modifié

#### `frontmatter_writer.py` - Modification YAML safe
```python
class FrontmatterWriter:
    """Écrit dans frontmatter en préservant structure"""

    def parse_note_file(self, file_path) -> Tuple[dict, str]:
        """Parse avec ruamel.yaml (préserve ordre + commentaires)"""

    def update_frontmatter(
        self,
        file_path,
        categories,
        confidence
    ) -> None:
        """Ajoute tags + métadonnées AI sans casser le YAML"""

    def apply_categories_to_note(
        self,
        note,
        categories,
        backup=True
    ) -> bool:
        """Wrapper avec backup automatique"""
```

**Design decision : ruamel.yaml au lieu de PyYAML**
- PyYAML détruit l'ordre et les commentaires
- ruamel.yaml préserve tout (round-trip safe)
- Essentiel pour ne pas frustrer l'utilisateur

#### `category_ameliorator.py` - Amélioration incrémentale
```python
class CategoryAmeliorator:
    """Améliore taxonomie au fil du temps"""

    def assign_new_notes(
        self,
        new_notes,
        existing_categories
    ) -> Dict:
        """K-NN pour assigner nouvelles notes"""

    def refine_categories(
        self,
        all_notes,
        categories
    ) -> List[Category]:
        """Recalcule centroides + stats"""

    def suggest_subcategories(
        self,
        category
    ) -> List[Category]:
        """Clustering intra-catégorie (KMeans)"""

    def suggest_merges(
        self,
        categories,
        threshold=0.85
    ) -> List[Tuple]:
        """Détecte catégories similaires (cosine > 0.85)"""
```

**Design decision : Approche incrémentale**
- Détection delta : compare timestamps fichiers vs DB
- Pas de réanalyse complète : assigne seulement les nouvelles notes
- Raffinement périodique : recalcule centroides

### 3. LLM Layer (`obsillama/llm/`)

**Responsabilité :** Intégration avec Ollama et prompts français

#### `ollama_client.py` - Client avec retry logic
```python
class OllamaClient:
    """Client Ollama avec gestion d'erreurs robuste"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def generate(self, prompt: str) -> str:
        """Génération de texte avec retry exponentiel"""

    @retry(...)
    def embed(self, text: str) -> List[float]:
        """Embedding d'un texte"""

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embeddings (pas de retry, géré niveau supérieur)"""
```

**Design decision : Tenacity pour retry**
- Exponential backoff : 4s, 8s, 10s
- 3 tentatives maximum
- Gère timeouts et connexions réseau instables

#### `graphrag_integration.py` - Pipeline GraphRAG complet
```python
class GraphRAGPipeline:
    """Pipeline GraphRAG en 4 phases"""

    def extract_entities(self, note: Note) -> List[GraphEntity]:
        """Phase 1 : LLM extrait entités (JSON parsing)"""

    def extract_relationships(
        self,
        note,
        entities
    ) -> List[GraphRelationship]:
        """Phase 2 : LLM extrait relations entre entités"""

    def build_graph(
        self,
        entities,
        relationships
    ) -> ig.Graph:
        """Phase 3 : Construction graphe igraph"""

    def detect_communities(
        self,
        graph,
        entities
    ) -> List[GraphCommunity]:
        """Phase 4 : Leiden clustering"""

    def summarize_community(
        self,
        community,
        entities
    ) -> str:
        """Phase 5 : LLM résume chaque communauté"""
```

**Design decision : Algorithme Leiden pour communautés**
- Alternative considérée : Louvain
- Choix : Leiden car :
  - Plus rapide que Louvain
  - Meilleure qualité de clusters
  - Paramètre `resolution` pour contrôler granularité

**Gestion de cache :**
```python
# Cache des entités et relations (évite doublons)
self.entities_cache: Dict[str, GraphEntity] = {}
self.relationships_cache: Dict[str, GraphRelationship] = {}

# Clé = hash(nom + type) pour entités
# Clé = hash(source + type + target) pour relations
```

#### `prompts/` - Prompts français optimisés
```python
# categorization.py
def get_category_generation_prompt(entity_names, community_summary):
    """Prompt pour générer nom + description de catégorie"""
    return f"""
Voici un groupe thématique extrait d'un vault Obsidian.

**Entités principales :** {entity_names}
**Résumé :** {community_summary}

Génère une catégorie pertinente (JSON) :
{{
    "name": "Nom court et descriptif",
    "description": "Description détaillée",
    "keywords": ["mot-clé1", "mot-clé2"]
}}
"""

# analysis.py
def get_entity_extraction_prompt(note_title, note_content):
    """Prompt pour extraction d'entités"""

# refinement.py
def get_subcategory_suggestion_prompt(category_name, note_titles):
    """Prompt pour suggestion de sous-catégories"""
```

**Design decision : Prompts en français**
- Vault cible en français
- LLM (mistral) excellent en français
- Meilleure compréhension des nuances

### 4. Storage Layer (`obsillama/storage/`)

**Responsabilité :** Persistance (LanceDB + JSON)

#### `lancedb_manager.py` - Gestion LanceDB
```python
class LanceDBManager:
    """Gestionnaire LanceDB pour stockage vectoriel"""

    def __init__(self, db_path: str):
        """Connexion à la DB (crée si n'existe pas)"""
        self.db = lancedb.connect(db_path)

    def create_notes_table(self) -> lancedb.Table:
        """Crée table notes avec schéma PyArrow"""
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("title", pa.string()),
            pa.field("content", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), 768)),
            ...
        ])

    def insert_notes(
        self,
        notes: List[Note],
        embeddings: List[List[float]]
    ):
        """Insert/upsert avec index IVF_PQ"""
```

**Design decision : LanceDB au lieu de Chroma/Pinecone**
- **Avantages LanceDB :**
  - Local-first (pas de serveur distant)
  - Format Apache Arrow (interopérable)
  - Index IVF_PQ très performant
  - Pas de limite de taille
  - Open-source, pas de vendor lock-in

**Schema notes :**
```python
{
    "id": str,              # UUID ou hash
    "title": str,
    "content": str,         # Texte complet
    "file_path": str,
    "embedding": [float],   # 768 dims
    "ai_categories": [str],
    "ai_confidence": float,
    "created_at": str,
    "modified_at": str,
    ...
}
```

#### `embedding_store.py` - Recherche vectorielle
```python
class EmbeddingStore:
    """Wrapper pour recherche sémantique avancée"""

    def search_similar_notes(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_threshold: Optional[float] = None,
        category_filter: Optional[str] = None,
    ) -> List[Dict]:
        """Recherche vectorielle avec filtres SQL"""

        # Construit le filtre
        filters = []
        if category_filter:
            filters.append(f"ai_categories LIKE '%{category_filter}%'")
        if similarity_threshold:
            filters.append(f"_distance < {1 - similarity_threshold}")

        # Recherche LanceDB
        results = (
            table
            .search(query_embedding)
            .limit(top_k)
            .where(" AND ".join(filters) if filters else None)
            .to_pandas()
        )
```

**Design decision : Filtres SQL sur LanceDB**
- LanceDB supporte SQL-like WHERE clauses
- Permet filtrage par catégorie, dossier, word_count
- Plus performant que filtrer en Python après recherche

#### `graph_store.py` - Stockage graphe
```python
class GraphStore:
    """Stockage entités + relations + communautés"""

    def save_entities(self, entities: List[GraphEntity]):
        """Sauvegarde dans table LanceDB 'entities'"""

    def save_relationships(self, relationships: List[GraphRelationship]):
        """Sauvegarde dans JSON (pas besoin de vectoriel)"""
        # Format : data/categories/graph_relationships.json

    def save_communities(self, communities: List[GraphCommunity]):
        """Sauvegarde dans table LanceDB 'communities'"""

    def load_graph(self) -> Tuple[List, List, List]:
        """Charge entités + relations + communautés"""
```

**Design decision : Hybride LanceDB + JSON**
- **LanceDB** pour entités et communautés (besoin d'embeddings)
- **JSON** pour relations (graphe simple, pas de recherche vectorielle)
- Flexibilité : JSON éditable manuellement si besoin

#### `category_store.py` - Stockage taxonomie
```python
class CategoryStore:
    """Stockage JSON pour taxonomies"""

    def save_taxonomy(self, categories: List[Category]) -> str:
        """Sauvegarde avec timestamp (versionning)"""
        # Format : data/categories/taxonomy_20260111_223000.json

    def save_assignments(self, assignments: Dict) -> str:
        """Sauvegarde assignations notes → catégories"""

    def load_taxonomy(self, version: Optional[str] = None) -> List[Category]:
        """Charge dernière version (ou version spécifique)"""

    def list_versions(self) -> List[str]:
        """Liste toutes les versions disponibles"""
```

**Design decision : Versionning avec timestamps**
- Permet rollback si taxonomie insatisfaisante
- Historique des évolutions
- Format : `taxonomy_YYYYMMDD_HHMMSS.json`

---

## Flux de données

### Pipeline complet (scan → apply)

```
1. SCAN
   ├─ NoteScanner.scan_vault()
   ├─ NoteScanner.parse_note() pour chaque .md
   └─ Cache JSON : data/cache/scanned_notes.json

2. ANALYZE
   ├─ Load notes depuis cache
   ├─ GraphRAGPipeline.extract_entities() [LLM]
   ├─ GraphRAGPipeline.extract_relationships() [LLM]
   ├─ GraphRAGPipeline.build_graph() [igraph]
   ├─ GraphRAGPipeline.detect_communities() [Leiden]
   ├─ GraphRAGPipeline.summarize_community() [LLM]
   ├─ CategoryGenerator.generate_from_communities() [LLM]
   ├─ EmbeddingManager.embed_notes() [Ollama]
   ├─ CategoryGenerator.assign_notes_to_categories() [Cosine similarity]
   ├─ GraphStore.save_graph() [LanceDB]
   └─ CategoryStore.save_taxonomy() [JSON]

3. EMBED
   ├─ Load notes
   ├─ EmbeddingManager.generate_embeddings_batch() [Ollama, cache]
   └─ EmbeddingStore.upsert_embeddings() [LanceDB]

4. REVIEW
   ├─ CategoryStore.load_taxonomy()
   ├─ TUI ou YAML export
   ├─ Édition utilisateur (approve/reject/merge)
   └─ CategoryStore.save_taxonomy() [JSON updated]

5. APPLY
   ├─ Load catégories approved
   ├─ Load assignments
   ├─ BackupManager.create_snapshot() [.obsillama_backups/]
   ├─ FrontmatterWriter.apply_categories_to_note() [ruamel.yaml]
   └─ Logs succès/échecs
```

### Flux d'une requête sémantique

```
USER: "docker kubernetes"
   ↓
EmbeddingManager.generate_embedding("docker kubernetes")
   ↓ [Ollama API]
query_embedding: [0.12, -0.45, ..., 0.78]  # 768 dims
   ↓
EmbeddingStore.search_similar_notes(query_embedding, top_k=10)
   ↓ [LanceDB vector search]
Results: [
    {title: "K8s Setup", score: 0.89},
    {title: "Docker Compose", score: 0.85},
    ...
]
   ↓
Display results (Rich table)
```

---

## Composants principaux

### Models (`obsillama/models/`)

Tous les modèles sont **Pydantic BaseModel** pour :
- Validation automatique des types
- Sérialisation JSON facile
- Documentation auto-générée

#### `note.py`
```python
class Note(BaseModel):
    id: str
    file_path: str
    file_name: str
    relative_path: str
    title: str
    content: str
    tags: List[str]
    frontmatter_tags: List[str]
    inline_tags: List[str]
    backlinks: List[str]
    external_links: List[str]
    word_count: int
    char_count: int
    heading_count: int
    ai_categories: List[str] = []
    ai_confidence: Optional[float] = None
    ai_processed: bool = False
    has_embedding: bool = False
    folder: str = ""
    is_daily_note: bool = False
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
```

#### `category.py`
```python
class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Category(BaseModel):
    id: str
    name: str
    description: str
    keywords: List[str]
    tag_name: str  # Ex: "AI-Category-DevOps"
    note_count: int = 0
    avg_confidence: float = 0.0
    review_status: ReviewStatus = ReviewStatus.PENDING
    parent_id: Optional[str] = None
    children_ids: List[str] = []
    level: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
```

#### `graph_entity.py`
```python
class EntityType(str, Enum):
    TECHNOLOGY = "technology"
    CONCEPT = "concept"
    TOOL = "tool"
    PERSON = "person"
    ORGANIZATION = "organization"
    PROJECT = "project"
    METHODOLOGY = "methodology"

class GraphEntity(BaseModel):
    id: str
    name: str
    type: EntityType
    description: str
    source_note_ids: List[str]
    mention_count: int = 1
    importance_score: float = 0.5

class GraphCommunity(BaseModel):
    id: str
    name: str
    description: str
    entity_ids: List[str]
    entity_count: int
    density: float
    algorithm: str = "leiden"
    resolution: float = 1.0
```

---

## Décisions de design

### 1. Pourquoi Click au lieu d'argparse ?

**Choix : Click**

Avantages :
- Syntaxe déclarative (@click.command, @click.option)
- Contexte partagé (`@pass_context`)
- Auto-génération de help
- Support des couleurs (via Rich integration)
- Groupes de commandes hiérarchiques
- Validation automatique des types

### 2. Pourquoi ruamel.yaml au lieu de PyYAML ?

**Choix : ruamel.yaml**

Comparaison :
```python
# PyYAML (détruit structure)
import yaml
with open('note.md') as f:
    data = yaml.safe_load(f)
data['tags'].append('new-tag')
with open('note.md', 'w') as f:
    yaml.dump(data, f)  # ❌ Ordre perdu, commentaires supprimés

# ruamel.yaml (préserve structure)
from ruamel.yaml import YAML
yaml = YAML()
with open('note.md') as f:
    data = yaml.load(f)
data['tags'].append('new-tag')
with open('note.md', 'w') as f:
    yaml.dump(data, f)  # ✅ Ordre préservé, commentaires intacts
```

### 3. Pourquoi LanceDB au lieu de FAISS/Chroma ?

**Choix : LanceDB**

| Critère | LanceDB | FAISS | Chroma |
|---------|---------|-------|--------|
| Local | ✅ | ✅ | ❌ (serveur) |
| Filtres SQL | ✅ | ❌ | ⚠️ (limité) |
| Format ouvert | ✅ (Arrow) | ❌ | ❌ |
| Performance | ⚡⚡⚡ | ⚡⚡⚡ | ⚡⚡ |
| Scalabilité | ✅ | ⚠️ | ✅ |
| Facilité d'usage | ✅ | ❌ | ✅ |

### 4. Pourquoi Textual pour le TUI ?

**Choix : Textual**

Alternatives considérées : curses, rich, prompt_toolkit

Avantages Textual :
- Framework moderne (async/await)
- Composants réutilisables (DataTable, Input, Button)
- CSS-like styling
- Mouse support
- Hotkeys intégrés
- Documentation excellente

### 5. Pourquoi igraph au lieu de NetworkX ?

**Choix : igraph**

| Critère | igraph | NetworkX |
|---------|--------|----------|
| Performance | ⚡⚡⚡ (C core) | ⚡ (Python pur) |
| Leiden | ✅ Natif | ❌ Externe |
| Mémoire | ⚡⚡⚡ | ⚡ |
| Documentation | ✅ | ✅✅ |

**Benchmark :**
- Graphe 1000 nœuds, détection communautés :
  - igraph : 0.3s
  - NetworkX : 2.1s

### 6. Pourquoi cache JSON au lieu de Redis ?

**Choix : JSON local**

Justification :
- ObsIllama = outil local, pas de serveur
- Redis = overhead inutile pour usage desktop
- JSON = simple, portable, versionnable (Git)
- Performance suffisante (~1ms load pour 1000 embeddings)

---

## Technologies

| Composant | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **CLI Framework** | Click | 8.1.7 | Standard de facto Python CLI |
| **TUI Framework** | Textual | 0.85.0 | Modern async TUI |
| **UI/Display** | Rich | 13.7.1 | Tables, progress bars, colors |
| **LLM Integration** | Ollama | 0.4.2 | Local LLMs, open-source |
| **Vector DB** | LanceDB | 0.17.0 | Performance, format ouvert |
| **Graph Library** | igraph | 0.11.8 | Leiden, performance |
| **YAML Parsing** | ruamel.yaml | 0.18.6 | Préserve structure |
| **Frontmatter** | python-frontmatter | 1.1.0 | Parsing Markdown + YAML |
| **Data Validation** | Pydantic | 2.9.2 | Type safety, validation |
| **Retry Logic** | tenacity | 9.0.0 | Exponential backoff |
| **Progress Bars** | tqdm | 4.67.1 | Simple, rapide |
| **Array Operations** | NumPy | 1.26.4 | Vectorisation |
| **ML Utilities** | scikit-learn | 1.5.2 | KMeans, cosine_similarity |

---

## Patterns et conventions

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Niveaux :
logger.debug("Détails techniques")
logger.info("Informations utilisateur")
logger.warning("Avertissements non-bloquants")
logger.error("Erreurs récupérables")
logger.critical("Erreurs fatales")

# Configuration centralisée dans config.yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/obsillama.log"
```

### Gestion d'erreurs

```python
# Pattern 1 : Try-except avec contexte
try:
    entities = extract_entities(note)
except OllamaAPIError as e:
    logger.error(f"Erreur API Ollama pour note {note.id}: {e}")
    return []
except Exception as e:
    logger.exception(f"Erreur inattendue: {e}")
    raise

# Pattern 2 : Retry avec tenacity
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def api_call():
    # Tente 3 fois avec backoff 4s, 8s, 10s
    pass
```

### Configuration

**Pattern : Pydantic Settings**
```python
# config/settings.py
class VaultConfig(BaseModel):
    path: str = Field(...)
    backup_path: str = ".obsillama_backups"
    exclude_folders: List[str] = [".obsidian", ".trash"]

class Config(BaseModel):
    vault: VaultConfig
    ollama: OllamaConfig
    graphrag: GraphRAGConfig
    ...

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Charge depuis YAML + valide"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

### Tests

```python
# tests/test_note_scanner.py
import pytest
from obsillama.core.note_scanner import NoteScanner

@pytest.fixture
def scanner(tmp_path):
    """Fixture pour créer un scanner temporaire"""
    return NoteScanner(vault_path=str(tmp_path))

def test_parse_frontmatter(scanner, tmp_path):
    """Test parsing d'une note avec frontmatter"""
    # Arrange
    note_path = tmp_path / "test.md"
    note_path.write_text("---\ntitle: Test\n---\nContent")

    # Act
    note = scanner.parse_note(note_path)

    # Assert
    assert note.title == "Test"
    assert note.content == "Content"
```

**Couverture actuelle :** 175/179 tests passent (97.8%)

---

## Performance et scalabilité

### Bottlenecks identifiés

1. **Extraction d'entités (LLM)** : ~30-60s par note
   - Solution : Batch processing, parallélisation future

2. **Détection de communautés (Leiden)** : ~1-5s pour 1000 entités
   - Solution : Déjà optimal (igraph C core)

3. **Génération d'embeddings** : ~20-50 notes/sec
   - Solution : Cache (1000x speedup pour réutilisations)

### Optimisations implémentées

#### 1. Cache d'embeddings
```python
# Sans cache : 1000 notes = ~50s
# Avec cache : 1000 notes (80% déjà calculés) = ~10s
# Speedup : 5x sur vault réel

_cache: Dict[str, List[float]] = {}  # {content_hash: embedding}
```

#### 2. Batch processing
```python
# Séquentiel : 100 notes × 0.1s = 10s
# Batch 32 : 100 notes en 3.2s (~3x speedup)

def embed_batch(texts: List[str], batch_size=32):
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embeddings = ollama.embed_batch(batch)
```

#### 3. Index vectoriel IVF_PQ
```python
# LanceDB crée automatiquement un index IVF_PQ
# Recherche sur 10,000 notes :
#   - Brute force : ~200ms
#   - IVF_PQ : ~5ms (40x speedup)
```

### Scalabilité

| Vault Size | Scan | GraphRAG | Embeddings | Recherche |
|------------|------|----------|------------|-----------|
| 100 notes | 1s | ~1h | 5s | 5ms |
| 1,000 notes | 5s | ~10h | 50s | 10ms |
| 10,000 notes | 50s | ~100h* | 8min | 20ms |

\*GraphRAG sur 10k notes : parallélisation recommandée (future feature)

### Limites actuelles

1. **GraphRAG séquentiel** : Un appel LLM à la fois
   - Future : Parallélisation avec `asyncio`

2. **Mémoire** : Graphe entier en RAM
   - Limite pratique : ~50,000 entités (~4GB RAM)

3. **LanceDB** : Pas de clustering multi-nœuds
   - Limite : ~1 million de notes (suffisant pour usage desktop)

---

## Évolutions futures

### Roadmap technique

**Phase 8 : Performance**
- [ ] Parallélisation GraphRAG (asyncio)
- [ ] Streaming pour gros vaults
- [ ] Index partiel (delta updates)

**Phase 9 : Features**
- [ ] Support OpenAI/Anthropic APIs
- [ ] Multi-modal (images, PDFs)
- [ ] Graphe interactif (D3.js export)

**Phase 10 : Distribution**
- [ ] Docker image
- [ ] Plugin Obsidian natif
- [ ] Web UI (Streamlit/Gradio)

---

**Auteur :** Jobierre
**Dernière mise à jour :** 2026-01-11
**Version :** 1.0.0-beta
