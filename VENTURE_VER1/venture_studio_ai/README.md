# Venture Studio AI - Stage 1 MVP

Local-first, modular Streamlit app that uses a local LLM (qwen3.5 via Ollama).

Quick start

1. Create and activate a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start Ollama (ensure `qwen3.5:latest` is installed and Ollama is running):

```bash
ollama serve
ollama list
```

3. Run the app

```bash
streamlit run app.py
```

Notes
- This Stage 1 uses a simple TF-IDF retrieval as a placeholder for embeddings and vector DB. It's modular so you can swap in Chroma/LlamaIndex later.
- All data stays local; do not add secrets to prompts.

Success test
- Use the sample company profile in the prompt and ask for a first draft checklist for quality management. The app should return a single structured answer.
