# Quantum Education Toolkit

Run the toolkit and simulator together with Docker. You don’t need to install Python or Node.js.

---

## What you need

- **Docker** — [Get Docker](https://docs.docker.com/get-docker/) (choose your OS). After installing, start Docker and keep it running.

---

## 1. Get the toolkit

1. Open **[Releases](https://github.com/Sahil624/qToolkit/releases)** and click the latest release.
2. Download the **zip file** from that release (e.g. `qToolkit-v1.0.0.zip`). Don’t use the green “Code” → “Download ZIP” — use the zip linked in the release.
3. Unzip it to a folder you can find (e.g. Desktop). Remember that folder.

---

## 2. Open a terminal in that folder

- **Windows:** Open PowerShell, then:
  ```powershell
  cd C:\Users\YourName\Desktop\qToolkit-v1.0.0
  ```
  (Change the path to where you actually unzipped.)

- **Mac / Linux:** Open Terminal, then:
  ```bash
  cd ~/Desktop/qToolkit-v1.0.0
  ```
  (Change the path if needed.)

---

## 3. Run the toolkit

In that same terminal, run:

```bash
docker compose up --build
```

Wait until you see a short message with two web links. Then in your browser open:

- **Notebooks:** [http://localhost:8888](http://localhost:8888)
- **Simulator:** [http://localhost:8001](http://localhost:8001)

---

## 4. AI / language model

**Default:** The toolkit uses **Ollama** on your computer (see section 5). Good if you have a capable GPU. When you run with Docker, it is already set up to use Ollama on your machine (the container reaches it via the host), so install and run Ollama on your computer before starting the toolkit.

**No GPU?** You can use a cloud API instead (e.g. Google Gemini). One way is [OpenRouter](https://openrouter.ai): get a free key, then run the toolkit with it.

### Example Run with Google Gemini

1. Get an API key from [OpenRouter](https://openrouter.ai/keys) (free tier available).
2. In the folder where you unzipped the toolkit, run this in your terminal. **Replace `YOUR_OPENROUTER_KEY` with your key.**

   **Mac / Linux:**
   ```bash
   OPENAI_API_KEY=YOUR_OPENROUTER_KEY LLM_PROVIDER=openai LLM_MODEL=google/gemini-2.0-flash-exp LLM_BASE_URL=https://openrouter.ai/api/v1 docker compose up --build
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:OPENAI_API_KEY="YOUR_OPENROUTER_KEY"; $env:LLM_PROVIDER="openai"; $env:LLM_MODEL="google/gemini-2.0-flash-exp"; $env:LLM_BASE_URL="https://openrouter.ai/api/v1"; docker compose up --build
   ```

3. When you see the message with the two URLs, open [http://localhost:8888](http://localhost:8888) and [http://localhost:8001](http://localhost:8001) in your browser.

### Other cloud APIs (OpenAI, etc.)

Same idea: set `OPENAI_API_KEY`, `LLM_PROVIDER=openai`, `LLM_MODEL`, and `LLM_BASE_URL` for your provider, then run `docker compose up`. For more options, see [DockerSetup.md](DockerSetup.md).

---

## 5. Using Ollama on your computer (recommended if you have a GPU)

Best experience if your machine has a **GPU with 6–8 GB VRAM** (or more) and **16 GB RAM**. Slower but possible on CPU only.

**Install Ollama:** [https://ollama.com](https://ollama.com) — pick your operating system and follow the steps.

**Linux (one command):**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Then download the two models** (run these in any terminal):

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text:latest
```

After that, run the toolkit as in section 3 (`docker compose up --build`). No extra setup needed. (When using Docker, the toolkit is configured to use Ollama on your host machine automatically.)

---

## 6. Stop the toolkit

Press **Ctrl+C** in the terminal. To remove the container as well:

```bash
docker compose down
```

---

## Need help?

See [DockerSetup.md](DockerSetup.md) for logs, support bundle, and troubleshooting.
