import logging
import os

import requests
from dotenv import load_dotenv
from fastembed import TextEmbedding
from google import genai
from qdrant_client import QdrantClient

# Load variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class SOCAnalyst:
    def __init__(self, mode=None, api_key=None):
        """
        Initializes the Analyst.
        Priority: 1. Passed Arguments (from UI) -> 2. Environment Variables (.env) -> 3. Defaults
        """
        # Configuration Fallbacks
        self.mode = mode or os.getenv("AI_MODE", "cloud")
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_id = os.getenv("GEMINI_MODEL_ID", "gemini-2.0-flash")
        self.local_model = os.getenv("LOCAL_MODEL_NAME", "llama3")

        # Connection settings
        q_host = os.getenv("QDRANT_HOST", "localhost")
        q_port = int(os.getenv("QDRANT_PORT", 6333))

        # Core Components
        self.qdrant = QdrantClient(host=q_host, port=q_port)
        self.encoder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.collection_name = "soc_intelligence"

        if self.mode == "cloud":
            if not self.api_key:
                raise ValueError(
                    "API Key is required for cloud mode (check .env or UI)."
                )
            self.cloud_client = genai.Client(api_key=self.api_key)
            logger.info(f"Initialized Cloud Provider: {self.model_id}")
        else:
            self.local_url = "http://localhost:11434/api/generate"
            logger.info(f"Initialized Local Provider: Ollama ({self.local_model})")

    def _get_context_with_score(
        self, query: str, limit: int = 5, threshold: float = None
    ):
        """Retrieves logs based on similarity score."""
        # Use default threshold from .env if not passed
        if threshold is None:
            threshold = float(os.getenv("GROUNDING_THRESHOLD", 0.50))

        query_vector = list(self.encoder.embed([query]))[0]
        response = self.qdrant.query_points(
            collection_name=self.collection_name, query=query_vector, limit=limit
        )

        if not response.points:
            return "", 0.0

        max_score = response.points[0].score
        valid_points = [hit for hit in response.points if hit.score >= threshold]

        context = ""
        for hit in valid_points:
            p = hit.payload
            context += f"[{p.get('tactic')}] Severity {p.get('severity')}: {p.get('narrative')}\n"

        return context, max_score

    def _ask_gemini(self, prompt):
        try:
            response = self.cloud_client.models.generate_content(
                model=self.model_id, contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Gemini Cloud Error: {str(e)}"

    def _ask_ollama(self, prompt):
        data = {"model": self.local_model, "prompt": prompt, "stream": False}
        try:
            r = requests.post(self.local_url, json=data)
            return r.json().get("response")
        except Exception as e:
            return f"Local Ollama error: {e}"

    def investigate(self, user_query: str, threshold: float = None):
        """Orchestrates the investigation with a grounding check."""
        logs, confidence = self._get_context_with_score(user_query, threshold=threshold)

        # Use .env threshold if none provided
        target_threshold = (
            threshold
            if threshold is not None
            else float(os.getenv("GROUNDING_THRESHOLD", 0.50))
        )

        if confidence < target_threshold:
            return (
                f"🛡️ **No suspicious logs found.**\n\n"
                f"The highest similarity match was only **{confidence:.2f}**, "
                f"which is below our threshold of **{target_threshold}**."
            )

        full_prompt = f"""
        ROLE: Senior Cyber Security Forensic Analyst
        REPORT CONFIDENCE: {confidence:.2f}
        CONTEXT LOGS FROM DATABASE:
        {logs}
        USER INQUIRY: {user_query}
        Please provide a threat level, evidence summary, and MITRE mapping based ONLY on the logs above.
        """

        return (
            self._ask_gemini(full_prompt)
            if self.mode == "cloud"
            else self._ask_ollama(full_prompt)
        )


if __name__ == "__main__":
    analyst = SOCAnalyst()
    print(analyst.investigate("Show me lateral movement via winrm"))
