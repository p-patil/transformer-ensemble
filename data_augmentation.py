import argparse
import concurrent.futures
import os
import pickle
import random

import datasets
import nlpaug.augmenter.word as naw
import torch
import transformers
from tqdm import tqdm

from utils import create_encodings, create_tensor_dataset


# python3 -m data_augmentation --limit 10
# python3 -m data_augmentation --language fr --gpu 1
# python3 -m data_augmentation --language es --gpu 2
# python3 -m data_augmentation --language de --gpu 3
# python3 -m data_augmentation --language it --gpu 4
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save-dir", type=str, default="data/augmented_train_ds")
    ap.add_argument("--gpu", type=str, default="cuda:0")
    ap.add_argument("--dataset", type=str, default="sst2")
    ap.add_argument("--limit", type=int, default=-1)
    ap.add_argument("--language", type=str, default="fr")
    # ['fr', 'de', 'es', 'it'] == [french, german, spanish, italian]
    return ap.parse_args()


def augment_sentences(ds, language, gpu="cuda:0"):
    """
    Augment sentences with nlpaug
    """
    augmented_sentences = []
    idx = len(ds)
    aug = naw.BackTranslationAug(
        from_model_name=f"Helsinki-NLP/opus-mt-en-{language}",
        to_model_name=f"Helsinki-NLP/opus-mt-{language}-en",
        device=gpu,
        batch_size=1024,
    )
    for entry in tqdm(ds):
        sentence = aug.augment(entry["sentence"])
        augmented_sentences.append(
            {"idx": idx, "label": entry["label"], "sentence": sentence}
        )
        idx += 1
    return augmented_sentences


def main(args):
    print(f"Save dir: {args.save_dir}")

    if args.gpu is None or len(args.gpu) == 0:
        print("WARNING: Using CPU")
        gpu = ["cpu"]
    else:
        print(f"Using GPU: {args.gpu}")

    print(
        f"Augmenting the training split from dataset: {args.dataset}"
        f"using back translation with Helsinki-NLP/opus-mt-en-{args.language}"
    )
    if "TOKENIZERS_PARALLELISM" not in os.environ:
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
    tokenizer = transformers.BertTokenizer.from_pretrained("bert-base-uncased")
    ds = datasets.load_dataset("glue", args.dataset)

    train_ds = list(ds["train"])[: args.limit]
    print(f"Augmenting {len(train_ds)} sentences using {args.language}")
    aug_ds = augment_sentences(train_ds, args.language, args.gpu)
    print(f"Augmentation complete -- Saving tensor dataset to disk")
    encodings = create_encodings(
        dataset=train_ds, tokenizer=tokenizer, name=args.dataset
    )
    tensors_ds = create_tensor_dataset(
        dataset=train_ds, encodings=encodings, distillation=False
    )

    output_path = f"{args.save_dir}/{args.dataset}_{args.language}.pt"
    torch.save(obj=tensors_ds, f=output_path)
    print(f"Saved tensor dataset to {output_path}")


if __name__ == "__main__":
    main(parse_args())
