# Test Flow

1. Activate virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Start Ollama (ensure qwen3.5 is installed)

```bash
ollama serve
ollama list
```

3. Run the app

```bash
streamlit run app.py
```

4. In the app: select Example Med Device Co and run the sample query.
