# DocuChat — portail RAG pour documents internes

DocuChat est un assistant qui répond aux questions des employés **à partir des documents internes de l'entreprise**. Chaque réponse cite ses sources, et chaque utilisateur ne voit que les documents de ses groupes.

![CI](https://github.com/maherbenaicha/docuchat/actions/workflows/ci.yml/badge.svg)

## Fonctionnalités

| Fonctionnalité | Implémentation |
|---|---|
| **Questions sur les documents internes** | Ingestion PDF / DOCX / Markdown / TXT, découpage en passages avec chevauchement, embeddings multilingues (FastEmbed, ONNX, sans GPU) |
| **Recherche hybride** | Recherche sémantique `pgvector` (index HNSW) + recherche plein texte PostgreSQL, fusionnées par *Reciprocal Rank Fusion* |
| **Tolérance aux fautes de frappe** | Correction des requêtes par similarité trigramme (`pg_trgm`) sur une forme sans accents (`teletravial` → `télétravail`) |
| **Droits d'accès par utilisateur** | Groupes par document et par utilisateur. Le filtrage est fait **dans la requête SQL** : un passage interdit ne peut ni être retrouvé, ni être envoyé au LLM, ni apparaître dans les corrections de requête |
| **Sources affichées** | Le LLM doit citer `[n]`. Les citations inventées sont supprimées, et seules les sources réellement citées sont renvoyées |
| **Garde-fou anti-hallucination** | Sans passage pertinent, le LLM n'est pas appelé et l'assistant répond qu'il n'a rien trouvé |
| **API** | FastAPI, authentification JWT, documentation OpenAPI sur `/docs` |
| **Fine-tuning** | Pipeline de fine-tuning du modèle d'embeddings sur des paires (question, passage) générées par LLM ([`finetuning/`](finetuning/)) |
| **DevOps** | Docker Compose (PostgreSQL + API + front Nginx), CI GitHub Actions (lint, 28 tests d'intégration sur un vrai PostgreSQL, build des images) |

## Architecture

```mermaid
flowchart LR
    U[Utilisateur] --> F[React + Vite<br/>servi par Nginx]
    F -->|/api, JWT| A[FastAPI]
    A --> C[Correction de requête<br/>pg_trgm]
    C --> R[Recherche hybride<br/>pgvector + full-text + RRF]
    R -->|filtre par groupes en SQL| DB[(PostgreSQL 16<br/>pgvector)]
    R --> G[Génération<br/>Llama 3.3 70B via Groq]
    G --> V[Vérification des citations]
    V --> F
    I[Upload admin<br/>PDF/DOCX/MD] --> P[Parsing → chunks → embeddings] --> DB
```

## Démarrage rapide

Prérequis : Docker Desktop.

```bash
git clone https://github.com/maherbenaicha/docuchat.git
cd docuchat
cp .env.example .env        # ajoutez votre clé GROQ_API_KEY (gratuite sur console.groq.com)
docker compose up --build
```

- Application : http://localhost:8080
- Documentation de l'API : http://localhost:8000/docs

Au premier lancement, le modèle d'embeddings (environ 220 Mo) est téléchargé, puis les documents de démonstration sont indexés.

| Compte de démo | Mot de passe | Accès |
|---|---|---|
| `admin@docuchat.local` | `admin123` | tous les documents, gestion des utilisateurs |
| `alice@docuchat.local` | `demo1234` | public + **rh** (grille de salaires, recrutement) |
| `bob@docuchat.local` | `demo1234` | public + **tech** (architecture, runbook) |
| `chloe@docuchat.local` | `demo1234` | documents publics uniquement |

**Test des droits d'accès :** demandez « Quel est le salaire d'un ingénieur junior ? » avec Chloé, puis avec Alice.

Sans clé Groq, l'application fonctionne en **mode extractif** : elle renvoie le passage le plus pertinent, sans génération.

## Développement local

```bash
# Base de données
docker compose up db -d

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://docuchat:docuchat@localhost:5432/docuchat
python -m app.seed            # utilisateurs et documents de démo
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

## Tests et évaluation

```bash
cd backend
pytest                          # 28 tests (PostgreSQL requis, voir TEST_DATABASE_URL)
python -m eval.evaluate_retrieval   # Hit@1, Hit@5 et MRR sur 16 questions annotées
```

Les tests couvrent l'authentification, l'isolation des droits (listing, recherche, correction de requête, contexte envoyé au LLM), le filtrage des citations, le garde-fou sans contexte et l'isolation des conversations.

## Structure

```
backend/
  app/
    routers/       auth, documents, chat, admin
    services/      parsing, chunking, embeddings, query_correction, retrieval, llm, rag
  eval/            évaluation de la recherche
  sample_docs/     documents d'une entreprise fictive
  tests/
frontend/          React + TypeScript (Vite)
finetuning/        fine-tuning du modèle d'embeddings
.github/workflows/ CI
```

## Pistes d'amélioration

- Réponses en streaming (SSE)
- Re-ranking par cross-encoder
- Ingestion asynchrone (file de tâches) pour les gros documents
- Migrations Alembic, observabilité (Prometheus / OpenTelemetry)
- Connecteurs SharePoint / Confluence

## Auteur

Maher Ben Aicha, étudiant ingénieur en génie logiciel à l'ENIT.
