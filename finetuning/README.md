# Fine-tuning du modèle d'embeddings

Adapte le modèle d'embeddings multilingue au vocabulaire interne de l'entreprise, afin d'améliorer la recherche sémantique de DocuChat.

1. **Générer des paires** (question, passage) avec un LLM, à partir des documents internes :
   `GROQ_API_KEY=... python generate_pairs.py ../backend/sample_docs pairs.jsonl`
2. **Entraîner** le modèle avec `MultipleNegativesRankingLoss` (sentence-transformers) :
   `python train_embeddings.py pairs.jsonl ./docuchat-embeddings`
3. **Comparer** le modèle de base et le modèle fine-tuné sur le jeu d'évaluation annoté (`backend/eval/questions.json`) :
   `python compare_models.py ./docuchat-embeddings`

Installation : `pip install -r requirements.txt`. Ça tourne sur CPU pour un petit corpus, ou sur un GPU Colab gratuit.

> Le jeu de démonstration est très petit (7 documents) : le gain mesuré sert à valider la méthode, pas à tirer des conclusions générales. Sur un vrai corpus d'entreprise, il faut générer plusieurs milliers de paires et garder un jeu de test séparé.
