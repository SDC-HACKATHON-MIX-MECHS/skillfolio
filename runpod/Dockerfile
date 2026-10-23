# RunPod Serverless worker for SkillFolio: resume-to-skills matching on a GPU.
# Build context = the repo root (RunPod console: Dockerfile path "runpod/Dockerfile", build context ".").
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 HF_HOME=/models
WORKDIR /worker

COPY runpod/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the model into the image so a cold worker does not download it (faster start, no network needed).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"

COPY runpod/skill_match.py runpod/handler.py ./
CMD ["python", "-u", "handler.py"]
