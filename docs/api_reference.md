# ObsIllama - Référence API

## Table des matières

1. [Core Layer](#core-layer)
2. [LLM Layer](#llm-layer)
3. [Storage Layer](#storage-layer)
4. [Models](#models)
5. [Utils](#utils)
6. [Config](#config)

---

## Core Layer

### NoteScanner

**Path:** `obsillama/core/note_scanner.py`

Scanner et parser de notes Obsidian avec support d'échantillonnage.

#### Constructeur

```python
def __init__(
    self,
    vault_path: str,
    cache_path: Optional[Path] = None,
    exclude_folders: List[str] = None
)
```

**Paramètres :**
- `vault_path` (str): Chemin vers le vault Obsidian
- `cache_path` (Optional[Path]): Chemin vers le fichier de cache JSON
- `exclude_folders` (List[str]): Dossiers à exclure (défaut: `.obsidian`, `.trash`)

**Exemple :**
```python
from obsillama.core.note_scanner import NoteScanner

scanner = NoteScanner(
    vault_path="/Users/you/Documents/ObsidianVault",
    cache_path=Path("data/cache/scanned_notes.json"),
    exclude_folders=[".obsidian", ".trash", "Templates"]
)
```

#### Méthodes

##### `scan_vault()`

Scan récursif du vault pour trouver tous les fichiers `.md`.

```python
def scan_vault(
    self,
    exclude_folders: Optional[List[str]] = None
) -> List[Path]:
```

**Retour :** Liste des chemins vers fichiers Markdown

**Exemple :**
```python
md_files = scanner.scan_vault()
print(f"{len(md_files)} fichiers trouvés")
```

##### `parse_note()`

Parse une note (frontmatter + contenu).

```python
def parse_note(
    self,
    file_path: Path
) -> Note:
```

**Paramètres :**
- `file_path` (Path): Chemin vers la note

**Retour :** Objet `Note` avec frontmatter parsé et métadonnées

**Raises :**
- `ValueError`: Si le fichier n'existe pas
- `yaml.YAMLError`: Si le frontmatter est invalide

**Exemple :**
```python
note = scanner.parse_note(Path("vault/MyNote.md"))
print(note.title)
print(note.tags)
print(note.word_count)
```

##### `scan_and_parse()`

Scan + parse avec échantillonnage.

```python
def scan_and_parse(
    self,
    sample_strategy: Literal["random", "stratified", "all"] = "random",
    sample_size: Optional[int] = None,
    sample_percent: Optional[float] = None,
) -> List[Note]:
```

**Paramètres :**
- `sample_strategy` ("random" | "stratified" | "all"): Stratégie d'échantillonnage
- `sample_size` (Optional[int]): Nombre de notes (pour "random")
- `sample_percent` (Optional[float]): Pourcentage (pour "random" ou "stratified")

**Retour :** Liste des notes parsées

**Exemple :**
```python
# 10% des notes, échantillonnage stratifié par dossier
notes = scanner.scan_and_parse(
    sample_strategy="stratified",
    sample_percent=10.0
)

# 50 notes aléatoires
notes = scanner.scan_and_parse(
    sample_strategy="random",
    sample_size=50
)

# Toutes les notes
notes = scanner.scan_and_parse(sample_strategy="all")
```

##### `detect_new_notes()`

Détecte les notes nouvelles (pas dans la DB).

```python
def detect_new_notes(
    self,
    db_manager: LanceDBManager
) -> List[Path]:
```

**Retour :** Chemins vers notes nouvelles

##### `save_cache()` / `load_cache()`

Sauvegarde/chargement du cache JSON.

```python
def save_cache(self, notes: List[Note]) -> None
def load_cache(self) -> List[Note]
```

---

### CategoryGenerator

**Path:** `obsillama/core/category_generator.py`

Génère des catégories à partir des communautés GraphRAG.

#### Constructeur

```python
def __init__(
    self,
    ollama_client: OllamaClient,
    confidence_threshold: float = 0.7,
    min_notes_per_category: int = 3
)
```

**Paramètres :**
- `ollama_client` (OllamaClient): Client pour appels LLM
- `confidence_threshold` (float): Seuil de confiance pour assignation (0.0-1.0)
- `min_notes_per_category` (int): Minimum de notes par catégorie

**Exemple :**
```python
from obsillama.core.category_generator import CategoryGenerator
from obsillama.llm.ollama_client import OllamaClient

ollama = OllamaClient("http://localhost:11434")
generator = CategoryGenerator(
    ollama_client=ollama,
    confidence_threshold=0.75,
    min_notes_per_category=5
)
```

#### Méthodes

##### `generate_from_communities()`

Génère catégories depuis communautés GraphRAG.

```python
def generate_from_communities(
    self,
    communities: List[GraphCommunity],
    entities: List[GraphEntity]
) -> List[Category]:
```

**Retour :** Liste des catégories générées

**Exemple :**
```python
# Après GraphRAG
entities, relationships, communities = graphrag.run_full_pipeline(notes)

# Générer catégories
categories = generator.generate_from_communities(
    communities=communities,
    entities=entities
)

print(f"{len(categories)} catégories générées")
for cat in categories:
    print(f"- {cat.name}: {cat.description}")
```

##### `assign_notes_to_categories()`

Assigne notes aux catégories par similarité d'embeddings.

```python
def assign_notes_to_categories(
    self,
    notes: List[Note],
    categories: List[Category],
    note_embeddings: List[List[float]],
    category_embeddings: List[List[float]]
) -> Dict[str, List[Tuple[str, float]]]:
```

**Retour :** Dict `{category_id: [(note_id, confidence), ...]}`

**Exemple :**
```python
# Générer embeddings
note_embeddings = embedding_manager.embed_notes(notes)
category_embeddings = embedding_manager.generate_embeddings_batch(
    [cat.description for cat in categories]
)

# Assigner
assignments = generator.assign_notes_to_categories(
    notes=notes,
    categories=categories,
    note_embeddings=note_embeddings,
    category_embeddings=category_embeddings
)

# Afficher
for cat_id, note_list in assignments.items():
    print(f"Category {cat_id}: {len(note_list)} notes")
```

##### `suggest_subcategories()`

Suggère sous-catégories par clustering intra-catégorie.

```python
def suggest_subcategories(
    self,
    parent_category: Category,
    notes: List[Note],
    note_embeddings: List[List[float]],
    n_clusters: int = 3,
    min_notes_per_subcat: int = 5
) -> List[Category]:
```

**Retour :** Liste de sous-catégories suggérées

**Exemple :**
```python
# Pour une grosse catégorie (50+ notes)
subcats = generator.suggest_subcategories(
    parent_category=big_category,
    notes=category_notes,
    note_embeddings=category_note_embeddings,
    n_clusters=3
)
```

---

### EmbeddingManager

**Path:** `obsillama/core/embedding_manager.py`

Gestionnaire d'embeddings avec cache intelligent.

#### Constructeur

```python
def __init__(
    self,
    ollama_client: OllamaClient,
    cache_path: Optional[Path] = None,
    model_name: str = "nomic-embed-text",
    model_dimension: int = 768
)
```

**Paramètres :**
- `ollama_client` (OllamaClient): Client Ollama
- `cache_path` (Optional[Path]): Chemin vers cache JSON
- `model_name` (str): Nom du modèle d'embedding
- `model_dimension` (int): Dimension des vecteurs (768 pour nomic-embed-text)

**Exemple :**
```python
from obsillama.core.embedding_manager import EmbeddingManager

embedding_manager = EmbeddingManager(
    ollama_client=ollama,
    cache_path=Path("data/cache/embeddings_cache.json"),
    model_name="nomic-embed-text",
    model_dimension=768
)
```

#### Méthodes

##### `generate_embedding()`

Génère un embedding pour un texte.

```python
def generate_embedding(
    self,
    text: str,
    use_cache: bool = True,
    max_length: int = 2000
) -> List[float]:
```

**Paramètres :**
- `text` (str): Texte à encoder
- `use_cache` (bool): Utiliser le cache
- `max_length` (int): Longueur max (troncature auto)

**Retour :** Vecteur d'embedding (768 dims)

**Raises :**
- `ValueError`: Si texte vide

**Exemple :**
```python
embedding = embedding_manager.generate_embedding(
    "Docker containerization and Kubernetes orchestration"
)
print(len(embedding))  # 768
```

##### `generate_embeddings_batch()`

Génère embeddings par batch.

```python
def generate_embeddings_batch(
    self,
    texts: List[str],
    batch_size: int = 32,
    use_cache: bool = True,
    show_progress: bool = True
) -> List[List[float]]:
```

**Retour :** Liste de vecteurs

**Exemple :**
```python
texts = [note.content for note in notes]
embeddings = embedding_manager.generate_embeddings_batch(
    texts=texts,
    batch_size=32,
    show_progress=True
)
# Progress bar affichée automatiquement
```

##### `embed_notes()`

Génère embeddings pour des notes (wrapper).

```python
def embed_notes(
    self,
    notes: List[Note],
    batch_size: int = 8,
    use_cache: bool = True,
    show_progress: bool = True,
    max_length: int = 2000
) -> List[Note]:
```

**Retour :** Notes avec métadonnées embeddings mises à jour

**Exemple :**
```python
notes_with_embeddings = embedding_manager.embed_notes(
    notes=notes,
    batch_size=16
)

for note in notes_with_embeddings:
    print(f"{note.title}: has_embedding={note.has_embedding}")
```

---

### FrontmatterWriter

**Path:** `obsillama/core/frontmatter_writer.py`

Écrit dans le frontmatter en préservant la structure YAML.

#### Constructeur

```python
def __init__(
    self,
    vault_path: str,
    backup_manager: Optional[BackupManager] = None
)
```

**Exemple :**
```python
from obsillama.core.frontmatter_writer import FrontmatterWriter
from obsillama.utils.file_utils import BackupManager

backup_mgr = BackupManager(vault_path)
writer = FrontmatterWriter(
    vault_path="/Users/you/vault",
    backup_manager=backup_mgr
)
```

#### Méthodes

##### `parse_note_file()`

Parse une note avec ruamel.yaml.

```python
def parse_note_file(
    self,
    file_path: str
) -> Tuple[dict, str]:
```

**Retour :** `(frontmatter_dict, content_str)`

**Exemple :**
```python
fm, content = writer.parse_note_file("vault/MyNote.md")
print(fm['title'])
print(content)
```

##### `update_frontmatter()`

Met à jour le frontmatter avec catégories AI.

```python
def update_frontmatter(
    self,
    file_path: str,
    categories: List[str],
    confidence: float,
    backup: bool = True
) -> bool:
```

**Paramètres :**
- `file_path` (str): Chemin vers la note
- `categories` (List[str]): Catégories à ajouter
- `confidence` (float): Score de confiance
- `backup` (bool): Créer un backup avant modification

**Retour :** `True` si succès

**Exemple :**
```python
success = writer.update_frontmatter(
    file_path="vault/MyNote.md",
    categories=["DevOps", "Containerization"],
    confidence=0.87,
    backup=True
)
```

**Résultat dans la note :**
```yaml
---
title: "My Note"
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
```

##### `apply_categories_to_note()`

Wrapper haut niveau.

```python
def apply_categories_to_note(
    self,
    note: Note,
    categories: List[Category],
    backup: bool = True
) -> bool:
```

**Exemple :**
```python
result = writer.apply_categories_to_note(
    note=my_note,
    categories=assigned_categories,
    backup=True
)
```

---

### CategoryAmeliorator

**Path:** `obsillama/core/category_ameliorator.py`

Amélioration incrémentale de la taxonomie.

#### Constructeur

```python
def __init__(
    self,
    ollama_client: OllamaClient,
    lancedb_manager: LanceDBManager,
    confidence_threshold: float = 0.7
)
```

#### Méthodes

##### `assign_new_notes()`

Assigne nouvelles notes aux catégories existantes.

```python
def assign_new_notes(
    self,
    new_notes: List[Note],
    existing_categories: List[Category],
    category_embeddings: List[List[float]]
) -> Dict[str, List[Tuple[str, float]]]:
```

**Exemple :**
```python
# Détecter nouvelles notes
new_notes = scanner.detect_new_notes(db_manager)

# Assigner aux catégories existantes
assignments = ameliorator.assign_new_notes(
    new_notes=new_notes,
    existing_categories=categories,
    category_embeddings=cat_embeddings
)
```

##### `suggest_merges()`

Suggère fusion de catégories similaires.

```python
def suggest_merges(
    self,
    categories: List[Category],
    category_embeddings: List[List[float]],
    threshold: float = 0.85
) -> List[Tuple[Category, Category, float]]:
```

**Retour :** Liste de `(cat1, cat2, similarity_score)`

**Exemple :**
```python
merges = ameliorator.suggest_merges(
    categories=categories,
    category_embeddings=embeddings,
    threshold=0.88
)

for cat1, cat2, score in merges:
    print(f"Fusionner '{cat1.name}' + '{cat2.name}' ? (similarité: {score:.2f})")
```

---

## LLM Layer

### OllamaClient

**Path:** `obsillama/llm/ollama_client.py`

Client Ollama avec retry logic et gestion d'erreurs.

#### Constructeur

```python
def __init__(
    self,
    base_url: str = "http://localhost:11434",
    timeout: int = 120,
    max_retries: int = 3
)
```

**Exemple :**
```python
from obsillama.llm.ollama_client import OllamaClient

ollama = OllamaClient(
    base_url="http://100.68.167.47:11434",  # Ollama distant
    timeout=180,
    max_retries=3
)
```

#### Méthodes

##### `generate()`

Génération de texte avec retry automatique.

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def generate(
    self,
    prompt: str,
    model: str = "mistral",
    temperature: float = 0.3,
    max_tokens: int = 2000
) -> str:
```

**Retour :** Texte généré

**Raises :**
- `OllamaAPIError`: Si échec après 3 tentatives

**Exemple :**
```python
prompt = "Génère une description pour une catégorie 'DevOps'"
response = ollama.generate(
    prompt=prompt,
    model="mistral",
    temperature=0.5
)
print(response)
```

##### `embed()`

Génère embedding pour un texte.

```python
@retry(...)
def embed(
    self,
    text: str,
    model: str = "nomic-embed-text"
) -> List[float]:
```

**Retour :** Vecteur 768 dims

**Exemple :**
```python
embedding = ollama.embed("Docker and Kubernetes")
print(len(embedding))  # 768
```

##### `embed_batch()`

Batch embeddings (pas de retry, géré au niveau supérieur).

```python
def embed_batch(
    self,
    texts: List[str],
    model: str = "nomic-embed-text"
) -> List[List[float]]:
```

**Exemple :**
```python
texts = ["Docker", "Kubernetes", "Python"]
embeddings = ollama.embed_batch(texts)
# [[0.1, ...], [0.2, ...], [0.3, ...]]
```

---

### GraphRAGPipeline

**Path:** `obsillama/llm/graphrag_integration.py`

Pipeline GraphRAG complet : entités → relations → graphe → communautés → résumés.

#### Constructeur

```python
def __init__(
    self,
    ollama_client: OllamaClient,
    min_community_size: int = 3,
    leiden_resolution: float = 1.0,
    max_entities_per_note: int = 15
)
```

**Exemple :**
```python
from obsillama.llm.graphrag_integration import GraphRAGPipeline

graphrag = GraphRAGPipeline(
    ollama_client=ollama,
    min_community_size=5,
    leiden_resolution=1.2,
    max_entities_per_note=20
)
```

#### Méthodes

##### `extract_entities()`

Extrait entités d'une note via LLM.

```python
def extract_entities(
    self,
    note: Note
) -> List[GraphEntity]:
```

**Retour :** Liste d'entités

**Exemple :**
```python
entities = graphrag.extract_entities(note)
for entity in entities:
    print(f"{entity.name} ({entity.type}): {entity.description}")
```

##### `extract_relationships()`

Extrait relations entre entités.

```python
def extract_relationships(
    self,
    note: Note,
    entities: List[GraphEntity]
) -> List[GraphRelationship]:
```

##### `build_graph()`

Construit graphe igraph.

```python
def build_graph(
    self,
    entities: List[GraphEntity],
    relationships: List[GraphRelationship]
) -> ig.Graph:
```

**Retour :** Graphe igraph

**Exemple :**
```python
graph = graphrag.build_graph(entities, relationships)
print(f"{graph.vcount()} sommets, {graph.ecount()} arêtes")
print(f"Connecté: {graph.is_connected()}")
```

##### `detect_communities()`

Détection de communautés avec Leiden.

```python
def detect_communities(
    self,
    graph: ig.Graph,
    entities: List[GraphEntity]
) -> List[GraphCommunity]:
```

**Retour :** Liste de communautés

**Exemple :**
```python
communities = graphrag.detect_communities(graph, entities)
for comm in communities:
    print(f"Communauté {comm.id}: {comm.entity_count} entités, densité={comm.density:.2f}")
```

##### `run_full_pipeline()`

Exécute le pipeline complet.

```python
def run_full_pipeline(
    self,
    notes: List[Note],
    show_progress: bool = True
) -> Tuple[List[GraphEntity], List[GraphRelationship], List[GraphCommunity]]:
```

**Retour :** `(entities, relationships, communities)`

**Exemple :**
```python
entities, rels, comms = graphrag.run_full_pipeline(
    notes=notes,
    show_progress=True
)

print(f"{len(entities)} entités")
print(f"{len(rels)} relations")
print(f"{len(comms)} communautés")
```

---

## Storage Layer

### LanceDBManager

**Path:** `obsillama/storage/lancedb_manager.py`

Gestionnaire LanceDB pour stockage vectoriel.

#### Constructeur

```python
def __init__(
    self,
    db_path: str = "data/lancedb"
)
```

**Exemple :**
```python
from obsillama.storage.lancedb_manager import LanceDBManager

db_manager = LanceDBManager(db_path="data/lancedb")
```

#### Méthodes

##### `create_notes_table()`

Crée table pour notes avec schéma PyArrow.

```python
def create_notes_table(self) -> lancedb.Table:
```

**Exemple :**
```python
notes_table = db_manager.create_notes_table()
```

##### `insert_notes()`

Insert/upsert notes avec embeddings.

```python
def insert_notes(
    self,
    notes: List[Note],
    embeddings: List[List[float]]
) -> None:
```

**Exemple :**
```python
db_manager.insert_notes(
    notes=notes,
    embeddings=embeddings
)
```

##### `get_note_by_id()`

Récupère une note par ID.

```python
def get_note_by_id(
    self,
    note_id: str
) -> Optional[Note]:
```

##### `count_records()`

Compte les enregistrements dans une table.

```python
def count_records(
    self,
    table_name: str
) -> int:
```

**Exemple :**
```python
count = db_manager.count_records("notes")
print(f"{count} notes dans la DB")
```

---

### EmbeddingStore

**Path:** `obsillama/storage/embedding_store.py`

Wrapper pour recherche vectorielle avancée.

#### Constructeur

```python
def __init__(
    self,
    lancedb_manager: LanceDBManager
)
```

#### Méthodes

##### `search_similar_notes()`

Recherche sémantique avec filtres.

```python
def search_similar_notes(
    self,
    query_embedding: List[float],
    top_k: int = 10,
    similarity_threshold: Optional[float] = None,
    category_filter: Optional[str] = None,
    folder_filter: Optional[str] = None,
    min_word_count: Optional[int] = None
) -> List[Dict[str, Any]]:
```

**Retour :** Liste de notes avec scores

**Exemple :**
```python
from obsillama.storage.embedding_store import EmbeddingStore

store = EmbeddingStore(db_manager)

query_emb = ollama.embed("machine learning python")
results = store.search_similar_notes(
    query_embedding=query_emb,
    top_k=5,
    similarity_threshold=0.7,
    category_filter="AI & ML"
)

for result in results:
    print(f"{result['title']}: {result['_distance']:.3f}")
```

##### `search_by_text()`

Recherche par texte libre (wrapper).

```python
def search_by_text(
    self,
    query_text: str,
    embedding_generator,
    top_k: int = 10,
    **kwargs
) -> List[Dict[str, Any]]:
```

**Exemple :**
```python
results = store.search_by_text(
    query_text="kubernetes deployment",
    embedding_generator=ollama.embed,
    top_k=5,
    category_filter="DevOps"
)
```

##### `get_category_centroid()`

Calcule centroide d'une catégorie.

```python
def get_category_centroid(
    self,
    category_id: str,
    category_name: Optional[str] = None
) -> Optional[List[float]]:
```

**Retour :** Vecteur centroide (moyenne des embeddings des notes)

**Exemple :**
```python
centroid = store.get_category_centroid("cat_devops")
# Utiliser pour calculer similarité avec autres catégories
```

---

### GraphStore

**Path:** `obsillama/storage/graph_store.py`

Stockage du graphe (entités, relations, communautés).

#### Méthodes

##### `save_graph()`

Sauvegarde le graphe complet.

```python
def save_graph(
    self,
    entities: List[GraphEntity],
    relationships: List[GraphRelationship],
    communities: List[GraphCommunity],
    entity_embeddings: List[List[float]],
    community_embeddings: List[List[float]]
) -> None:
```

**Exemple :**
```python
from obsillama.storage.graph_store import GraphStore

graph_store = GraphStore(db_manager)

graph_store.save_graph(
    entities=entities,
    relationships=relationships,
    communities=communities,
    entity_embeddings=entity_embs,
    community_embeddings=comm_embs
)
```

##### `load_graph()`

Charge le graphe complet.

```python
def load_graph(
    self
) -> Tuple[List[GraphEntity], List[GraphRelationship], List[GraphCommunity]]:
```

**Exemple :**
```python
entities, rels, comms = graph_store.load_graph()
```

---

### CategoryStore

**Path:** `obsillama/storage/category_store.py`

Stockage JSON pour taxonomies.

#### Méthodes

##### `save_taxonomy()`

Sauvegarde taxonomie avec versionning.

```python
def save_taxonomy(
    self,
    categories: List[Category]
) -> str:
```

**Retour :** Chemin vers fichier sauvegardé (avec timestamp)

**Exemple :**
```python
from obsillama.storage.category_store import CategoryStore

cat_store = CategoryStore(base_path="data/categories")

saved_path = cat_store.save_taxonomy(categories)
# data/categories/taxonomy_20260111_223000.json
```

##### `load_taxonomy()`

Charge taxonomie (dernière version ou version spécifique).

```python
def load_taxonomy(
    self,
    version: Optional[str] = None
) -> List[Category]:
```

**Exemple :**
```python
# Dernière version
categories = cat_store.load_taxonomy()

# Version spécifique
categories = cat_store.load_taxonomy(version="20260111_223000")
```

##### `save_assignments()`

Sauvegarde assignations notes → catégories.

```python
def save_assignments(
    self,
    assignments: Dict[str, List[Tuple[str, float]]]
) -> str:
```

**Exemple :**
```python
cat_store.save_assignments(assignments)
```

---

## Models

### Note

**Path:** `obsillama/models/note.py`

Modèle Pydantic pour une note Obsidian.

```python
class Note(BaseModel):
    """Modèle d'une note Obsidian"""

    # Identifiants
    id: str
    file_path: str
    file_name: str
    relative_path: str

    # Contenu
    title: str
    content: str

    # Tags
    tags: List[str] = []
    frontmatter_tags: List[str] = []
    inline_tags: List[str] = []

    # Liens
    backlinks: List[str] = []
    external_links: List[str] = []

    # Statistiques
    word_count: int = 0
    char_count: int = 0
    heading_count: int = 0

    # Catégorisation AI
    ai_categories: List[str] = []
    ai_confidence: Optional[float] = None
    ai_processed: bool = False
    ai_processed_date: Optional[datetime] = None
    ai_version: Optional[str] = None

    # Embedding
    has_embedding: bool = False
    embedding_model: Optional[str] = None
    embedding_date: Optional[datetime] = None

    # Métadonnées
    folder: str = ""
    is_daily_note: bool = False
    created_at: Optional[datetime] = None
    modified_at: Optional[datetime] = None
```

**Méthodes helper :**

```python
def get_all_tags(self) -> List[str]:
    """Retourne tous les tags (frontmatter + inline)"""

def has_tag(self, tag: str) -> bool:
    """Vérifie si la note a un tag donné"""

def to_dict(self) -> dict:
    """Convertit en dict"""

@classmethod
def from_dict(cls, data: dict) -> "Note":
    """Crée depuis dict"""
```

**Exemple :**
```python
note = Note(
    id="abc123",
    file_path="/vault/MyNote.md",
    file_name="MyNote.md",
    relative_path="Projects/MyNote.md",
    title="My Note",
    content="Content here...",
    tags=["docker", "python"],
    word_count=350
)

all_tags = note.get_all_tags()
has_docker = note.has_tag("docker")
```

---

### Category

**Path:** `obsillama/models/category.py`

Modèle pour une catégorie de notes.

```python
class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Category(BaseModel):
    """Modèle d'une catégorie"""

    # Identité
    id: str
    name: str
    description: str
    keywords: List[str] = []

    # Tag Obsidian
    tag_name: str  # Ex: "AI-Category-DevOps"

    # Statistiques
    note_count: int = 0
    avg_confidence: float = 0.0

    # Review
    review_status: ReviewStatus = ReviewStatus.PENDING

    # Hiérarchie
    parent_id: Optional[str] = None
    children_ids: List[str] = []
    level: int = 0

    # Métadonnées
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
```

**Méthodes :**

```python
def approve(self) -> None:
    """Approuve la catégorie"""
    self.review_status = ReviewStatus.APPROVED

def reject(self) -> None:
    """Rejette la catégorie"""
    self.review_status = ReviewStatus.REJECTED

def update_stats(self, note_count: int, avg_confidence: float) -> None:
    """Met à jour les stats"""
    self.note_count = note_count
    self.avg_confidence = avg_confidence
    self.updated_at = datetime.now()
```

---

### GraphEntity

**Path:** `obsillama/models/graph_entity.py`

Modèle pour une entité du graphe de connaissances.

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
    """Entité du graphe"""

    id: str
    name: str
    type: EntityType
    description: str
    source_note_ids: List[str]
    mention_count: int = 1
    importance_score: float = 0.5
```

**Exemple :**
```python
entity = GraphEntity(
    id="ent_docker",
    name="Docker",
    type=EntityType.TECHNOLOGY,
    description="Containerization platform",
    source_note_ids=["note1", "note2", "note3"],
    mention_count=3,
    importance_score=0.9
)
```

---

### GraphCommunity

**Path:** `obsillama/models/graph_entity.py`

Modèle pour une communauté détectée par Leiden.

```python
class GraphCommunity(BaseModel):
    """Communauté d'entités"""

    id: str
    name: str = ""
    description: str = ""
    entity_ids: List[str]
    entity_count: int
    density: float = 0.0
    top_entities: List[str] = []
    keywords: List[str] = []

    # Algorithme
    algorithm: str = "leiden"
    resolution: float = 1.0
    modularity: float = 0.0

    # Métadonnées
    detected_at: datetime = Field(default_factory=datetime.now)
    associated_note_ids: List[str] = []
```

**Méthodes :**

```python
def calculate_density(self) -> float:
    """Calcule la densité : edges / possible_edges"""
    # Implémenté dans le modèle
```

---

## Utils

### BackupManager

**Path:** `obsillama/utils/file_utils.py`

Gestionnaire de backups avec snapshots horodatés.

#### Constructeur

```python
def __init__(
    self,
    vault_path: str,
    backup_root: str = ".obsillama_backups"
)
```

#### Méthodes

```python
def create_backup_snapshot(self) -> str:
    """Crée un snapshot avec timestamp"""
    # Retourne: "20260111_223000"

def backup_file(
    self,
    file_path: str,
    snapshot_id: str
) -> None:
    """Backup un fichier dans le snapshot"""

def restore_backup(
    self,
    snapshot_id: str
) -> None:
    """Restaure un snapshot complet"""

def list_backups(self) -> List[str]:
    """Liste les snapshots disponibles"""

def cleanup_old_backups(
    self,
    keep_last: int = 10
) -> None:
    """Nettoie les vieux backups"""
```

**Exemple :**
```python
from obsillama.utils.file_utils import BackupManager

backup_mgr = BackupManager(vault_path="/Users/you/vault")

# Créer snapshot
snapshot_id = backup_mgr.create_backup_snapshot()

# Backup fichier
backup_mgr.backup_file("vault/MyNote.md", snapshot_id)

# Lister
snapshots = backup_mgr.list_backups()

# Restaurer
backup_mgr.restore_backup("20260111_223000")
```

---

## Config

### Config

**Path:** `obsillama/config/settings.py`

Configuration Pydantic pour toute l'application.

```python
class Config(BaseModel):
    """Configuration globale"""

    vault: VaultConfig
    ollama: OllamaConfig
    graphrag: GraphRAGConfig
    categorization: CategorizationConfig
    incremental: IncrementalConfig
    frontmatter: FrontmatterConfig
    lancedb: LanceDBConfig
    processing: ProcessingConfig
    logging: LoggingConfig

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Charge depuis YAML"""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str) -> None:
        """Sauvegarde en YAML"""
        with open(path, 'w') as f:
            yaml.dump(self.dict(), f)
```

**Exemple :**
```python
from obsillama.config.settings import Config

# Charger
config = Config.from_yaml("config/config.yaml")

# Utiliser
print(config.vault.path)
print(config.ollama.base_url)
print(config.graphrag.min_community_size)

# Modifier et sauvegarder
config.categorization.thresholds.assignment_confidence = 0.75
config.to_yaml("config/config.yaml")
```

---

## Exemples complets

### Exemple 1 : Pipeline complet de A à Z

```python
from pathlib import Path
from obsillama.config.settings import Config
from obsillama.core.note_scanner import NoteScanner
from obsillama.llm.ollama_client import OllamaClient
from obsillama.llm.graphrag_integration import GraphRAGPipeline
from obsillama.core.category_generator import CategoryGenerator
from obsillama.core.embedding_manager import EmbeddingManager
from obsillama.storage.lancedb_manager import LanceDBManager
from obsillama.storage.graph_store import GraphStore
from obsillama.storage.category_store import CategoryStore

# 1. Charger config
config = Config.from_yaml("config/config.yaml")

# 2. Initialiser les composants
ollama = OllamaClient(config.ollama.base_url)
db_manager = LanceDBManager(config.lancedb.path)
scanner = NoteScanner(
    vault_path=config.vault.path,
    cache_path=Path("data/cache/scanned_notes.json")
)

# 3. Scanner les notes
notes = scanner.scan_and_parse(
    sample_strategy="stratified",
    sample_percent=10.0
)
print(f"{len(notes)} notes scannées")

# 4. GraphRAG
graphrag = GraphRAGPipeline(
    ollama_client=ollama,
    min_community_size=config.graphrag.min_community_size
)
entities, rels, comms = graphrag.run_full_pipeline(notes)
print(f"{len(entities)} entités, {len(rels)} relations, {len(comms)} communautés")

# 5. Générer catégories
generator = CategoryGenerator(ollama)
categories = generator.generate_from_communities(comms, entities)
print(f"{len(categories)} catégories générées")

# 6. Embeddings
emb_manager = EmbeddingManager(
    ollama,
    cache_path=Path("data/cache/embeddings.json")
)
note_embeddings = emb_manager.generate_embeddings_batch(
    [note.content for note in notes]
)
cat_embeddings = emb_manager.generate_embeddings_batch(
    [cat.description for cat in categories]
)

# 7. Assigner notes
assignments = generator.assign_notes_to_categories(
    notes, categories, note_embeddings, cat_embeddings
)

# 8. Sauvegarder
graph_store = GraphStore(db_manager)
graph_store.save_graph(entities, rels, comms, entity_embs, comm_embs)

cat_store = CategoryStore()
cat_store.save_taxonomy(categories)
cat_store.save_assignments(assignments)

print("Pipeline terminé !")
```

### Exemple 2 : Recherche sémantique

```python
from obsillama.storage.embedding_store import EmbeddingStore

# Initialiser
store = EmbeddingStore(db_manager)

# Recherche par texte
results = store.search_by_text(
    query_text="kubernetes docker deployment",
    embedding_generator=ollama.embed,
    top_k=10,
    similarity_threshold=0.7,
    category_filter="DevOps"
)

# Afficher
for result in results:
    print(f"{result['title']}: {result['_distance']:.3f}")
    print(f"  Catégories: {result['ai_categories']}")
    print()
```

---

**Documentation générée automatiquement pour ObsIllama v1.0.0-beta**
**Dernière mise à jour :** 2026-01-11
