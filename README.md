# 🛡️ Sentinel RAG

## Enterprise Tier 2 SOC Intelligence for Cloud Environments

Sentinel RAG is an enterprise-grade **Retrieval-Augmented Generation (RAG)** platform designed specifically for **Tier 2 Security Operations Center (SOC)** teams operating in cloud-first environments.

It transforms high-volume AWS and Windows security logs into structured, evidence-backed forensic intelligence — without AI hallucinations.

## 🎯 Why Sentinel?

Tier 2 SOC analysts deal with:

- Escalated alerts lacking context
- Massive CloudTrail & Windows log volumes
- False positives and alert fatigue
- AI tools that hallucinate when logs are incomplete

Traditional AI guesses.
**Sentinel enforces evidence-first reasoning.**

If relevant logs are not found → the AI does not respond.

# 🏗 Architecture Overview

Sentinel uses a structured 4-layer RAG pipeline:

## 1️⃣ Ingestion Layer

- CloudTrail logs
- Windows Event Logs
- Attack simulation datasets
- Background indexing workflow

## 2️⃣ Refinery Layer (Polars Engine)

High-speed log transformation and enrichment:

- Timeline reconstruction
- User activity correlation
- Privilege escalation detection
- Suspicious API clustering
- Baseline deviation detection

## 3️⃣ Memory Layer (Vector Intelligence)

- Vector Database: Qdrant
- Embeddings: `BAAI/bge-small-en-v1.5`
- Metadata-aware filtering (user, IP, timestamp, technique)
- Similarity threshold enforcement

If similarity score < `GROUNDING_THRESHOLD` → response blocked.

## 4️⃣ Agentic Analysis Layer

Dual-engine AI support:

- ☁️ Cloud LLM (Gemini)
- 🏠 Local LLM (Llama via Ollama)

Each response:

- Uses retrieved evidence only
- Maps activity to MITRE ATT&CK techniques
- Generates escalation-ready forensic reports
- Displays investigation confidence score

# ✨ Key Features

- 🔒 Grounding Filter (anti-hallucination circuit breaker)
- ⚡ Dual LLM Engine (Cloud / Local toggle)
- 📊 Streamlit SOC App
- 🧠 MITRE ATT&CK Mapping
- 📁 Timeline Reconstruction
- 📈 Confidence Scoring Model
- 🔎 Threat Hunting Mode

# 📂 Project Structure

```
Enterprise-RAG/
│
├── src/                          # Core application logic
│   ├── ai_agents.py               # LLM orchestration & grounding filter
│   ├── database.py                # Qdrant indexing & retrieval logic
│   ├── log_engine.py              # Log processing & correlation (Polars)
│   └── worker.py                  # Background event processing
│
├── data/                          # Data collection
│   ├── attack_sigs/               # Simulated adversary techniques (Splunk ATT&CK dataset)
│   ├── baseline/                  # Normal Windows system behavior logs (LogHub)
│   └── raw_logs/                  # AWS attack scenario logs (Invictus dataset)
│
├── infra_data/                    # Vector database persistent storage
│   └── qdrant/                    # Qdrant vector index files
│
├── app.py                         # SOC interface
│
├── .env                           # Environment configuration (DO NOT COMMIT)
├── .gitignore
├── .python-version
├── docker-compose.yml             # Infrastructure configuration
├── requirements.txt
└── README.md
```

# ⚙️ Environment Configuration

Create a `.env` file in the root directory:

```bash
touch .env
```

## 📄 `.env` Format

```env
# ==============================
# AI Configuration
# ==============================

AI_MODE=cloud
GEMINI_API_KEY=gemini_api_key
GEMINI_MODEL_ID=gemini-2.5-flash
LOCAL_MODEL_NAME=llama3.2:1b

# ==============================
# Database & Infrastructure
# ==============================

QDRANT_HOST=localhost
QDRANT_PORT=6333
GROUNDING_THRESHOLD=0.50

# ==============================
# Event Orchestration
# ==============================

INNGEST_EVENT_KEY=your_inngest_event_key
```

# 🚀 Quick Start

## 1️⃣ Start Vector Database

```bash
docker-compose up -d
```

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

## 3️⃣ First-Time Indexing

```bash
python -m src.database
```

This will:

- Parse logs
- Generate embeddings
- Store vectors in Qdrant

## 4️⃣ Run the Stack

**Terminal A – Worker**

```bash
python -m uvicorn src.worker:app --port 8000 --host 0.0.0.0
```

**Terminal B – App**

```bash
python -m streamlit run app.py
```

Open:

```
http://localhost:8501
```

# 🔎 Example Investigation Output

```
Potential Technique: T1078 – Valid Accounts
Confidence: HIGH (0.82)

Evidence:
- IAM user created new access key
- Same user launched EC2 instance
- Login from unusual IP range

Assessment:
Behavior consistent with credential misuse and cloud resource staging.
```

# 📊 Data Sources & Why They Were Chosen

Sentinel is trained and evaluated using realistic security datasets to simulate Tier 2 SOC investigations.

## 🔴 Attack Simulation Data

Source: Splunk Attack Data Repository
[https://github.com/splunk/attack_data/tree/master/datasets](https://github.com/splunk/attack_data/tree/master/datasets)

Folder Used:

```
data/attack_sigs
```

**Why:**

- Contains mapped ATT&CK simulation logs
- Provides structured adversary behavior patterns
- Used to train technique recognition logic

## ☁️ AWS Attack Scenario Data

Source: Invictus Incident Response AWS Dataset
[https://github.com/invictus-ir/aws_dataset](https://github.com/invictus-ir/aws_dataset)

Folder Used:

```
data/raw_logs
```

**Why:**

- Realistic CloudTrail attack traces
- Shows what actual AWS compromise behavior looks like
- Used to simulate credential abuse & privilege escalation

## 🖥 Windows Baseline Behavior

Source: LogPAI LogHub Windows Logs
[https://github.com/logpai/loghub/tree/master/Windows](https://github.com/logpai/loghub/tree/master/Windows)

Folder Used:

```
data/baseline
```

**Why:**

- Represents normal system behavior
- Used for anomaly detection comparison
- Enables baseline deviation analysis
