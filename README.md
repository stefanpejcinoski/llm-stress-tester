# LLM Stress Tester

A local-only load testing tool for any OpenAI-compatible LLM inference endpoint. Run it from source or download a pre-built binary — no data leaves your machine.

---

## Features

- **Any OpenAI-compatible endpoint** — point it at any server that speaks `/v1/chat/completions`
- **Public or authenticated** — skip token entry for open endpoints, or paste a CSV of API keys
- **RPS or RPM** — toggle between requests-per-second and requests-per-minute; the internal rate is always correct
- **Ramping schedule** — configurable initial rate, max rate, scaling factor, and time per stage
- **Multi-model traffic split** — define multiple models with percentage weights (e.g. 70 % model-A, 30 % model-B)
- **7 benchmark suites** — pre-written prompt sets covering coding, math, knowledge, instruction following, multi-turn, long context, and text processing
- **Live progress** — stage progress bar, achieved vs target rate cards, per-request counters, last-update age, all refreshing every 2 s without flickering
- **Results dashboard** — latency percentiles (P50/P95/P99), error rate, per-stage and per-model breakdowns, dual-axis RPS/RPM chart
- **Export** — download results as XLSX (5 sheets) or PDF

---

## Quick start — from source

**Requirements:** Python 3.13+, [uv](https://github.com/astral-sh/uv) or pip

```bash
# Clone
git clone https://github.com/your-org/llm-stress-tester.git
cd llm-stress-tester

# Install
pip install -e "."

# Run
streamlit run src/llm_stress_tester/app.py
```

The app opens at `http://localhost:8501` in your browser.

---

## Quick start — pre-built binary

1. Go to the **Actions** tab of this repository on GitHub.
2. Click the latest passing workflow run on `main`.
3. Scroll to **Artifacts** and download the binary for your platform:
   - `llm-stress-tester-windows-latest` → `llm-stress-tester.exe`
   - `llm-stress-tester-macos-latest` → `llm-stress-tester`
   - `llm-stress-tester-ubuntu-latest` → `llm-stress-tester`
4. Run the binary. It launches a local Streamlit server and opens your browser automatically.

> Artifacts are kept for **30 days**. Re-run the workflow to refresh them.

---

## macOS note

The pre-built binary is **not code-signed**. macOS Gatekeeper will block it on first launch with a message like _"cannot be opened because it is from an unidentified developer."_

**Option 1 — right-click bypass (no Terminal needed):**
1. Right-click (or Control-click) the binary.
2. Choose **Open** from the menu.
3. Click **Open** in the dialog that appears.

**Option 2 — Terminal:**
```bash
xattr -rd com.apple.quarantine ./llm-stress-tester
chmod +x ./llm-stress-tester
./llm-stress-tester
```

You only need to do this once per downloaded binary.

---

## Configuration guide

| Section | What to set |
|---|---|
| **1. Endpoint** | Base URL (e.g. `http://localhost:8000`) and API path (default: `v1/chat/completions`). Check **Public endpoint** to skip auth. |
| **2. API Tokens** | Paste tokens as CSV (`token,label` per row). One token is used per concurrent user. Skip if public. |
| **3. Rate & Schedule** | Pick RPS or RPM, then set initial rate, max rate, scaling factor (multiplier per stage), and seconds per stage. |
| **4. Users** | Min and max concurrent users, and how many to add per stage. Capped by token count for authenticated endpoints. |
| **5. Models & Traffic Split** | One or more model names with a traffic percentage each. Multiple models at 100 % send duplicated load to each. |
| **6. Benchmark Suite** | Choose a pre-written prompt set that matches your model's expected workload. |
| **7. Advanced** | Per-request timeout (seconds) and max rows shown in the raw metrics table. |

---

## Benchmark suites

| Suite | Focus |
|---|---|
| `coding` | Code generation, algorithms, data structures |
| `math` | Word problems, probability, calculus, linear algebra |
| `knowledge` | Science, history, geography, general reasoning |
| `instruction_following` | Format compliance, constraints, multi-step instructions |
| `multi_turn` | Conversation continuity, context retention |
| `long_context` | Summarisation, document analysis, extended reasoning |
| `text_processing` | Editing, rewriting, classification, extraction |

---

## Output & exports

After a test completes the dashboard shows:

- **Summary cards** — total requests, successful, failed, average latency
- **RPS/RPM chart** — dual y-axis: target rate (left) and achieved rate (right), independently scaled so a slow endpoint never appears as a flat line
- **Latency percentiles chart** — P50, P95, P99 over time
- **Error rate chart** — percentage of failed requests per stage
- **Requests per stage bar chart** — coloured green/red by success threshold
- **Per-model latency and success rate** — scatter plots
- **Raw metrics table** — every individual request with status, latency, token, model, stage

**Export XLSX** produces five sheets: `config`, `raw_requests`, `stage_summary`, `model_summary`, `errors`.  
**Export PDF** saves all six charts to a single PDF file.

Rate columns in exports (`target_rps`/`target_rpm`, `achieved_rps`/`achieved_rpm`) match the unit selected during the test.

---

## Development

```bash
# Install with dev extras
pip install -e ".[dev]"

# Lint
ruff check src/

# Tests
python -m pytest --tb=short -q

# Run app locally
streamlit run src/llm_stress_tester/app.py
```

CI runs on every push and pull request. The PyInstaller build runs automatically on pushes to `main`/`master` after lint and tests pass.
