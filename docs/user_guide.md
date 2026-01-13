# ObsIllama - Guide Utilisateur

## Table des matières

1. [Introduction](#introduction)
2. [Concepts de base](#concepts-de-base)
3. [Premier lancement](#premier-lancement)
4. [Workflow complet](#workflow-complet)
5. [Cas d'usage](#cas-dusage)
6. [Astuces et bonnes pratiques](#astuces-et-bonnes-pratiques)
7. [FAQ](#faq)

---

## Introduction

ObsIllama est un outil d'organisation intelligente pour vos notes Obsidian. Il utilise des techniques avancées d'IA (GraphRAG, embeddings vectoriels) pour :

1. **Comprendre le contenu** de vos notes en extrayant entités et relations
2. **Détecter des thématiques** en construisant un graphe de connaissances
3. **Générer automatiquement** une taxonomie de catégories pertinentes
4. **Assigner intelligemment** vos notes aux bonnes catégories
5. **Enrichir le frontmatter** avec tags et métadonnées AI

**Avantages :**
- Gain de temps : plus besoin de catégoriser manuellement des centaines de notes
- Découverte : révèle des connexions et thématiques non évidentes
- Cohérence : taxonomie uniforme et basée sur le contenu réel
- Évolutif : amélioration continue avec le mode incrémental

---

## Concepts de base

### GraphRAG

**GraphRAG** (Graph Retrieval-Augmented Generation) est une technique qui combine :

1. **Extraction d'entités** : Le LLM identifie les concepts importants (technologies, outils, personnes, projets...)
2. **Extraction de relations** : Comment ces entités sont liées (utilise, implémente, dépend de...)
3. **Construction de graphe** : Représentation en graphe avec igraph
4. **Détection de communautés** : Algorithme Leiden pour trouver des clusters thématiques
5. **Génération de résumés** : Le LLM résume chaque communauté

**Pourquoi GraphRAG ?**
- Meilleure compréhension du contexte global
- Détection de thématiques émergentes
- Catégories basées sur les relations réelles entre concepts

### Embeddings vectoriels

Les **embeddings** transforment le texte en vecteurs numériques (768 dimensions avec `nomic-embed-text`).

**Utilité :**
- Mesurer la similarité sémantique entre notes
- Assigner notes aux catégories par proximité vectorielle
- Recherche sémantique : "docker containers" trouve aussi "containerization", "kubernetes"

**Cache intelligent :**
- Les embeddings sont cachés (hash du contenu)
- Évite de recalculer pour les notes non modifiées
- Accélération ~1000x pour les réutilisations

### LanceDB

**LanceDB** est une base de données vectorielle qui stocke :
- Notes avec leurs embeddings
- Catégories avec leurs centroides
- Entités et communautés du graphe

**Avantages :**
- Recherche vectorielle ultra-rapide (index IVF_PQ)
- Stockage efficace (format colonnaire)
- Requêtes SQL-like avec filtres

---

## Premier lancement

### 1. Installation des prérequis

```bash
# Vérifier Python 3.11+
python3.11 --version

# Vérifier Ollama
ollama list

# Si les modèles manquent
ollama pull mistral
ollama pull nomic-embed-text
```

### 2. Installation ObsIllama

```bash
cd /path/to/obsillama
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Initialisation

```bash
# Mode interactif (recommandé pour débutants)
python -m obsillama init

# Mode automatique
python -m obsillama init \
  --vault "/Users/vous/Documents/ObsidianVault" \
  --ollama-url "http://localhost:11434" \
  --non-interactive
```

**Ce qui est créé :**
- `config/config.yaml` : configuration complète
- `data/lancedb/` : base vectorielle
- `data/categories/` : taxonomies JSON
- `data/cache/` : cache des embeddings
- `logs/` : logs de l'application

### 4. Vérification

```bash
# Vérifier la config
cat config/config.yaml

# Tester la connexion Ollama
curl http://localhost:11434/api/tags
```

---

## Workflow complet

### Vue d'ensemble

```
1. SCAN → 2. ANALYZE → 3. EMBED → 4. REVIEW → 5. APPLY → 6. QUERY/STATS
   ↓          ↓           ↓          ↓          ↓           ↓
 Notes   GraphRAG+   Embeddings  Validation  Frontmatter Recherche
 cachées Catégories   générés    humaine    modifié     sémantique
```

### Étape 1 : Scanner le vault

**Objectif :** Parser les notes et créer un cache

```bash
# Option A : Scanner un échantillon (recommandé pour test)
python -m obsillama scan --percent 10

# Option B : Scanner un nombre fixe de notes
python -m obsillama scan --sample 50

# Option C : Scanner TOUT le vault (peut être long)
python -m obsillama scan --all

# Forcer un nouveau scan (ignore le cache existant)
python -m obsillama scan --all --force
```

**Sortie :**
```
✓ 84 notes scannées
📊 Statistiques :
  • Mots totaux : 125,430
  • Tags uniques : 67
  • Dossiers : 12
  • Backlinks : 234

Top 10 tags :
  1. #docker (23)
  2. #python (19)
  3. #self-hosting (15)
  ...

📁 Cache sauvegardé : data/cache/scanned_notes.json
```

**Que faire ensuite ?**
- Examinez les stats pour comprendre votre vault
- Si trop peu de notes, relancez avec `--percent 20` ou plus
- Le cache est réutilisé automatiquement pour les prochaines commandes

### Étape 2 : Analyser avec GraphRAG

**Objectif :** Extraire entités, construire le graphe, générer les catégories

```bash
# Analyse standard
python -m obsillama analyze

# Avec options personnalisées
python -m obsillama analyze \
  --categories 15 \
  --min-notes 3 \
  --min-community-size 5

# Sans barres de progression (pour logs propres)
python -m obsillama analyze --no-progress
```

**Ce qui se passe :**

1. **Chargement des notes** : Depuis le cache (étape 1)
2. **Extraction d'entités** : ~30-60s par note (appels LLM)
   ```
   Note: "Docker Compose Setup"
   → Entités: Docker, Compose, Container, YAML, Service
   ```
3. **Construction du graphe** : igraph avec entités comme nœuds
4. **Détection de communautés** : Algorithme Leiden
   ```
   Communauté 1 (23 entités) : DevOps, Docker, Kubernetes, CI/CD
   Communauté 2 (18 entités) : Python, FastAPI, Django, Flask
   ```
5. **Génération de catégories** : LLM résume chaque communauté
   ```
   Communauté 1 → Catégorie "DevOps & Containerization"
   Communauté 2 → Catégorie "Python Web Development"
   ```
6. **Assignation des notes** : Par similarité d'embeddings

**Sortie :**
```
✓ Pipeline GraphRAG terminé
  → 115 entités extraites
  → 67 relations détectées
  → 8 communautés trouvées

✓ 8 catégories générées
  → 84 notes assignées
  → Confidence moyenne : 0.78

📁 Sauvegardé :
  • data/lancedb/ (graphe)
  • data/categories/taxonomy.json
  • data/categories/assignments.json
```

**Problème : 0 communautés ?**
```
⚠️  Aucune communauté détectée (graphe trop petit ou peu connecté)
```
Solutions :
- Augmentez l'échantillon : `scan --sample 100`
- Réduisez `--min-community-size 1`
- Vérifiez que vos notes ont du contenu substantiel

### Étape 3 : Générer les embeddings

**Objectif :** Créer les vecteurs sémantiques pour toutes les notes

```bash
# Génération standard (batch 32)
python -m obsillama embed

# Batch plus petit (si mémoire limitée)
python -m obsillama embed --batch-size 8

# Forcer le recalcul (ignore le cache)
python -m obsillama embed --force-recompute

# Scanner TOUTES les notes (pas seulement le cache)
python -m obsillama embed --scan-all
```

**Sortie :**
```
Génération embeddings: 100%|████████| 84/84 [00:03<00:00, 22.4 notes/sec]

✓ Embeddings générés
  → 84 notes traitées
  → Vitesse : 22.4 notes/sec
  → Cache hit : 27.3%
  → Temps total : 3.8s

📁 Sauvegardé dans LanceDB (table: notes)
```

**Astuce :** Les embeddings sont cachés. Si vous relancez, seules les notes modifiées seront recalculées.

### Étape 4 : Reviewer les catégories

**Objectif :** Valider, éditer, fusionner, ou rejeter les catégories générées

#### Option A : Mode TUI interactif (recommandé)

```bash
python -m obsillama review --interactive
```

**Interface Textual :**
```
┌─ Catégories ─────────────────────────────────────┐
│ ID    Name                     Status   Notes    │
│ cat1  DevOps & Containers      pending  23       │
│ cat2  Python Development       pending  18       │
│ cat3  Machine Learning         pending  12       │
└──────────────────────────────────────────────────┘

Raccourcis :
  A - Approuver | R - Rejeter | E - Éditer
  M - Fusionner | S - Sauvegarder | Q - Quitter
```

**Actions possibles :**
- **A** : Approuver une catégorie (status → approved)
- **R** : Rejeter (status → rejected, ne sera pas appliquée)
- **E** : Éditer nom/description
- **M** : Fusionner deux catégories similaires
- **S** : Sauvegarder les modifications
- **Q** : Quitter

#### Option B : Export/Import YAML

```bash
# 1. Exporter en YAML
python -m obsillama review --export categories.yaml

# 2. Éditer manuellement dans votre éditeur
vim categories.yaml

# 3. Réimporter
python -m obsillama review --import categories.yaml
```

**Fichier YAML :**
```yaml
categories:
  - id: cat_abc123
    name: "DevOps & Containerization"
    description: "Technologies de containerization et DevOps"
    keywords:
      - docker
      - kubernetes
      - ci/cd
    tag_name: "AI-Category-DevOps"
    note_count: 23
    avg_confidence: 0.82
    review_status: "approved"  # Changez ici !
    parent_id: null
    children_ids: []
    level: 0
```

**Modification recommandée :**
- Changez `review_status: "pending"` → `"approved"` pour valider
- Modifiez `name` et `description` si besoin
- Ajoutez/retirez des `keywords`

### Étape 5 : Appliquer au vault

**Objectif :** Ajouter les tags et métadonnées AI dans le frontmatter des notes

⚠️ **IMPORTANT : Cette étape modifie vos notes ! Utilisez --dry-run d'abord.**

```bash
# 1. Prévisualiser sans modifier (DRY RUN)
python -m obsillama apply --dry-run

# 2. Appliquer avec backup automatique (RECOMMANDÉ)
python -m obsillama apply --backup

# 3. Appliquer seulement les tags (sans métadonnées)
python -m obsillama apply --backup --tags-only

# 4. Appliquer seulement aux notes non traitées
python -m obsillama apply --backup --new-only
```

**Sortie :**
```
Chargement des catégories approuvées : 6 catégories
Chargement des assignations : 78 notes assignées

Backup créé : .obsillama_backups/20260111_223000/

Application des catégories: 100%|████████| 78/78 [00:02<00:00, 32.1 notes/sec]

✓ Application terminée
  → 78 notes modifiées
  → 0 échecs
  → Backup : .obsillama_backups/20260111_223000/
```

**Résultat dans une note :**

Avant :
```yaml
---
title: "Docker Compose pour Self-Hosting"
tags:
  - docker
---
```

Après :
```yaml
---
title: "Docker Compose pour Self-Hosting"
tags:
  - docker
  - AI-Category-DevOps
  - AI-Category-Self-Hosting
ai_categories:
  - DevOps & Containerization
  - Self-Hosting Infrastructure
ai_confidence: 0.87
ai_processed_date: 2026-01-11T22:30:00
ai_version: "1.0.0"
---
```

**Restaurer un backup si problème :**
```bash
# Lister les backups
ls .obsillama_backups/

# Restaurer manuellement (copier les fichiers)
cp -r .obsillama_backups/20260111_223000/* /path/to/vault/
```

### Étape 6 : Utiliser les catégories

#### Recherche sémantique

```bash
# Recherche simple
python -m obsillama query "machine learning python"

# Avec filtres
python -m obsillama query "docker kubernetes" \
  --category "DevOps" \
  --limit 5 \
  --threshold 0.7

# Avec extraits de contenu
python -m obsillama query "neural networks" --show-content
```

**Sortie :**
```
Résultats pour : "machine learning python"

┌────────────────────────────────────────────────────┐
│ Titre                    Score   Catégorie         │
├────────────────────────────────────────────────────┤
│ PyTorch Tutorial          0.89    ML & AI          │
│ Scikit-learn Basics       0.85    ML & AI          │
│ TensorFlow Setup          0.82    ML & AI          │
└────────────────────────────────────────────────────┘
```

#### Statistiques

```bash
# Stats complètes
python -m obsillama stats --all

# Stats spécifiques
python -m obsillama stats --vault      # Vault uniquement
python -m obsillama stats --categories # Catégories uniquement
python -m obsillama stats --embeddings # Embeddings uniquement
python -m obsillama stats --graphrag   # GraphRAG uniquement
```

**Sortie :**
```
📊 Statistiques du Vault
  • Total notes : 542
  • Mots totaux : 234,567
  • Tags uniques : 89
  • Notes AI-processed : 78

📈 Statistiques des Catégories
  • Catégories actives : 6
  • Approuvées : 6
  • Rejetées : 2
  • Notes assignées : 78

🧠 Statistiques des Embeddings
  • Notes avec embeddings : 542
  • Dimension : 768
  • Modèle : nomic-embed-text
  • Cache size : 512
```

#### Dans Obsidian

**Graph View :**
- Filtrer par tag : `tag:#AI-Category-DevOps`
- Voir les connexions entre catégories

**Dataview Plugin :**
```dataview
TABLE ai_confidence as Confidence, ai_categories as Categories
FROM #AI-Category-DevOps
SORT ai_confidence DESC
```

**Abstract Folder Plugin :**
- Créer des dossiers virtuels basés sur `#AI-Category-*`
- Navigation par thématique au lieu de structure physique

---

## Cas d'usage

### Cas 1 : Vault de veille technologique (800 notes)

**Contexte :** Articles web clippés, notes de blog, documentation

**Workflow :**
```bash
# 1. Scanner tout le vault
python -m obsillama scan --all

# 2. Analyser avec paramètres adaptés
python -m obsillama analyze --categories 20 --min-notes 5

# 3. Embeddings
python -m obsillama embed

# 4. Review (export/import pour édition confortable)
python -m obsillama review --export tech_categories.yaml
# Éditer à la main
python -m obsillama review --import tech_categories.yaml

# 5. Appliquer
python -m obsillama apply --backup

# 6. Recherche quotidienne
python -m obsillama query "kubernetes deployment strategies"
```

**Résultat :**
- 18 catégories pertinentes (Frontend, Backend, DevOps, Cloud, AI/ML, etc.)
- 742/800 notes assignées (92%)
- Recherche sémantique opérationnelle

### Cas 2 : Notes de cours universitaires (200 notes)

**Contexte :** Cours de CS, maths, physics

**Workflow :**
```bash
# 1. Scanner avec échantillon
python -m obsillama scan --percent 50  # Test

# 2. Analyser
python -m obsillama analyze --categories 10

# 3. Review interactif
python -m obsillama review --interactive

# 4. Apply tags-only (garder frontmatter simple)
python -m obsillama apply --backup --tags-only
```

**Résultat :**
- Catégories : Algorithms, Data Structures, Calculus, Linear Algebra, etc.
- Facilite la révision par thématique

### Cas 3 : Vault personnel multi-thématique (500 notes)

**Contexte :** Tech, santé, finance, projets perso, daily notes

**Workflow :**
```bash
# 1. Exclure les daily notes (trop peu de contenu)
# Éditer config.yaml:
# vault:
#   exclude_folders:
#     - "Daily Notes"
#     - "Templates"

# 2. Scanner
python -m obsillama scan --all

# 3. Analyser avec plus de catégories
python -m obsillama analyze --categories 25

# 4. Review et fusionner les similaires
python -m obsillama review --interactive
# Fusionner "Health" et "Wellness" par exemple

# 5. Appliquer
python -m obsillama apply --backup
```

**Résultat :**
- Taxonomie multi-domaine cohérente
- Graph view révèle connexions insoupçonnées (ex: Stoïcisme + Productivité)

---

## Astuces et bonnes pratiques

### 1. Démarrez petit

❌ **À éviter :**
```bash
# Analyser 5000 notes d'un coup
python -m obsillama scan --all
python -m obsillama analyze
# → Peut prendre des heures, risque d'erreur
```

✅ **Recommandé :**
```bash
# Commencez avec 50-100 notes
python -m obsillama scan --sample 100
python -m obsillama analyze
# → Testez le workflow, ajustez les paramètres
```

### 2. Utilisez toujours --dry-run avant apply

```bash
# TOUJOURS prévisualiser d'abord
python -m obsillama apply --dry-run

# Examinez les changements, puis appliquez
python -m obsillama apply --backup
```

### 3. Gardez les backups

```bash
# Les backups sont dans .obsillama_backups/
ls -lh .obsillama_backups/

# Ne supprimez pas avant d'être sûr !
# Ajoutez à .gitignore si votre vault est versionné
echo ".obsillama_backups/" >> .gitignore
```

### 4. Ajustez les seuils selon votre vault

```yaml
# config.yaml
categorization:
  thresholds:
    assignment_confidence: 0.7  # Réduire à 0.6 si trop peu de notes assignées
    merge_similarity: 0.85      # Augmenter à 0.9 pour éviter les fusions excessives
```

### 5. Profitez du cache

```bash
# Le cache d'embeddings accélère ÉNORMÉMENT
# Ne pas utiliser --force-recompute sauf si vraiment nécessaire
python -m obsillama embed  # Utilise le cache

# Seulement si vous avez modifié beaucoup de notes :
python -m obsillama embed --force-recompute
```

### 6. Mode incrémental pour maintenance

```bash
# Après avoir ajouté 50 nouvelles notes
python -m obsillama scan --all  # Met à jour le cache
python -m obsillama ameliorate --new-only

# Périodiquement, raffiner la taxonomie
python -m obsillama ameliorate --refine --subcats
```

### 7. Excluez les dossiers non pertinents

```yaml
# config.yaml
vault:
  exclude_folders:
    - ".obsidian"
    - ".trash"
    - "Templates"
    - "Daily Notes"  # Trop peu de contenu substantiel
    - "Archive"
```

### 8. Monitoring avec logs

```bash
# Logs détaillés
tail -f logs/obsillama.log

# En cas d'erreur, activer DEBUG
# config.yaml :
# logging:
#   level: "DEBUG"
```

---

## FAQ

### Q : Combien de temps prend l'analyse ?

**R :** Dépend du nombre de notes et de la puissance de votre machine.

- Scan : ~100-200 notes/sec
- GraphRAG (extraction LLM) : ~30-60s par note
- Embeddings : ~20-50 notes/sec
- Apply : ~30-50 notes/sec

**Exemple pour 100 notes :**
- Scan : 1s
- GraphRAG : 50-100 min (appels LLM)
- Embeddings : 2-5s
- Total : ~1h

### Q : ObsIllama modifie-t-il mes notes ?

**R :** OUI, mais seulement avec la commande `apply`, et avec votre consentement.

- Les commandes `scan`, `analyze`, `embed`, `review` sont en lecture seule
- `apply` modifie le frontmatter YAML (ajoute tags et métadonnées)
- La structure YAML est préservée (grâce à ruamel.yaml)
- Backup automatique si vous utilisez `--backup`

### Q : Puis-je utiliser un Ollama distant ?

**R :** OUI !

```yaml
# config.yaml
ollama:
  base_url: "http://192.168.1.100:11434"
```

Ou via la commande init :
```bash
python -m obsillama init --ollama-url "http://192.168.1.100:11434"
```

### Q : Quels modèles Ollama sont requis ?

**R :** Deux modèles :

1. **Génération** : `mistral` (ou `llama2`, `mixtral`, `phi3`)
2. **Embedding** : `nomic-embed-text` (768 dims)

```bash
ollama pull mistral
ollama pull nomic-embed-text
```

### Q : Puis-je utiliser d'autres modèles de génération ?

**R :** OUI, modifiez `config.yaml` :

```yaml
ollama:
  models:
    generation: "llama2"  # ou mixtral, phi3, etc.
    embedding: "nomic-embed-text"  # Ne changez pas celui-ci
```

### Q : Les catégories générées ne sont pas bonnes, que faire ?

**R :** Plusieurs options :

1. **Augmenter l'échantillon** : Plus de notes = meilleure compréhension
   ```bash
   python -m obsillama scan --sample 200
   python -m obsillama analyze
   ```

2. **Ajuster les paramètres GraphRAG** :
   ```yaml
   graphrag:
     min_community_size: 5  # Augmenter pour catégories plus larges
     resolution: 1.5        # Augmenter pour plus de catégories
   ```

3. **Éditer manuellement** :
   ```bash
   python -m obsillama review --interactive
   # Fusionner, renommer, rejeter
   ```

4. **Réanalyser après modifications** :
   ```bash
   python -m obsillama analyze --force
   ```

### Q : Comment restaurer mes notes si problème ?

**R :** Les backups sont dans `.obsillama_backups/TIMESTAMP/`

```bash
# Lister les backups
ls .obsillama_backups/

# Restaurer (exemple)
cp -r .obsillama_backups/20260111_223000/* /path/to/vault/

# Ou utiliser BackupManager (futur)
# python -m obsillama restore --snapshot 20260111_223000
```

### Q : ObsIllama fonctionne-t-il hors ligne ?

**R :** OUI, si :
- Ollama tourne localement
- Les modèles sont téléchargés

Pas besoin d'Internet une fois les modèles installés.

### Q : Combien d'espace disque nécessaire ?

**R :** Dépend de la taille du vault.

- **LanceDB** : ~5-10 MB pour 100 notes avec embeddings
- **Cache** : ~1-2 MB pour 100 notes
- **Backups** : 1:1 avec la taille des notes modifiées

**Exemple pour 1000 notes :**
- LanceDB : ~50-100 MB
- Cache : ~10-20 MB
- Backups : ~20-50 MB (si toutes modifiées)

### Q : Puis-je versionner le projet avec Git ?

**R :** OUI, mais ajoutez à `.gitignore` :

```gitignore
# ObsIllama
data/
logs/
.obsillama_backups/
config/config.yaml  # Contient des chemins locaux
```

Versionnez :
- `config/config.yaml.example` (template)
- Code source
- Documentation

### Q : Comment améliorer les performances ?

**R :** Plusieurs leviers :

1. **Batch size** plus grand (si RAM suffisante) :
   ```bash
   python -m obsillama embed --batch-size 64
   ```

2. **Cache** : Réutilisez le cache au maximum

3. **Ollama** : GPU pour accélérer les embeddings

4. **Échantillonnage** : Ne pas tout analyser d'un coup
   ```bash
   # Analyser par lots de 100 notes
   python -m obsillama scan --sample 100
   python -m obsillama analyze
   # Puis augmenter progressivement
   ```

### Q : Puis-je contribuer au projet ?

**R :** Absolument ! Voir `CONTRIBUTING.md` pour les guidelines.

**Idées de contribution :**
- Nouveaux prompts optimisés
- Support d'autres LLM providers (OpenAI, Anthropic)
- Plugins Obsidian natifs
- Amélioration de l'UI (TUI Textual)
- Documentation et traductions

---

**Besoin d'aide ?** Ouvrez une issue sur GitHub ou consultez la [documentation technique](architecture.md).
