"""RunPod serverless handler: resume-to-skills matching with an open embedding model on a GPU.

Deployed as a RunPod Serverless Endpoint from runpod/Dockerfile (see runpod/README.md). The logic lives in skill_match.py.
"""

import runpod
import torch
from sentence_transformers import SentenceTransformer

from skill_match import MODEL_NAME, run

_model = SentenceTransformer(MODEL_NAME, device="cuda" if torch.cuda.is_available() else "cpu")   # loaded once per worker


def embed(texts):
    return _model.encode(list(texts), normalize_embeddings=True, batch_size=64)


def handler(job: dict) -> dict:
    return run(job, embed)


runpod.serverless.start({"handler": handler})
