"""Fine-tune the multilingual embedding model on domain (question, passage) pairs.

Uses MultipleNegativesRankingLoss: for each question, its passage is the positive and the
other passages of the batch are negatives. Runs on CPU in a few minutes for small datasets,
or on a free Colab GPU.

    python train_embeddings.py pairs.jsonl ./docuchat-embeddings
"""

import sys

from datasets import load_dataset
from sentence_transformers import SentenceTransformer, losses
from sentence_transformers.trainer import SentenceTransformerTrainer
from sentence_transformers.training_args import SentenceTransformerTrainingArguments

BASE_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main(pairs_path: str, output_dir: str) -> None:
    data = load_dataset("json", data_files=pairs_path)["train"].remove_columns(["source"])
    split = data.train_test_split(test_size=0.1, seed=42)

    model = SentenceTransformer(BASE_MODEL)
    args = SentenceTransformerTrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
        warmup_ratio=0.1,
        eval_strategy="epoch",
        save_strategy="no",
        logging_steps=10,
    )
    trainer = SentenceTransformerTrainer(
        model=model,
        args=args,
        train_dataset=split["train"],
        eval_dataset=split["test"],
        loss=losses.MultipleNegativesRankingLoss(model),
    )
    trainer.train()
    model.save(output_dir)
    print(f"Saved fine-tuned model to {output_dir}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
