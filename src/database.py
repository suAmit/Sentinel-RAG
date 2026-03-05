import logging
import uuid

import polars as pl
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SOCDatabase:
    def __init__(self, host: str = "localhost", port: int = 6333):
        try:
            self.client = QdrantClient(host=host, port=port)
            # Lightweight but powerful embedding model
            self.encoder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            self.collection_name = "soc_intelligence"
            self.vector_size = 384
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant or load model: {e}")
            raise

    def init_collection(self):
        """Creates the collection if it doesn't exist in Docker."""
        if not self.client.collection_exists(self.collection_name):
            logger.info(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=Distance.COSINE
                ),
            )
        else:
            logger.info(f"Collection '{self.collection_name}' already exists.")

    def upload_data(self, df: pl.DataFrame, batch_size: int = 500):
        """Sanitizes the Polars DF and pushes to Qdrant."""
        if df.is_empty():
            logger.warning("No data found to upload.")
            return

        # SANITIZATION: Critical for preventing the TypeError
        df = df.with_columns(
            pl.col("narrative").fill_null("Empty narrative").cast(pl.String)
        )

        records = df.to_dicts()
        total = len(records)
        narratives = [r["narrative"] for r in records]

        logger.info(f"Generating vectors for {total} unique narratives...")

        # Generator handles memory efficiently for large datasets
        embeddings_gen = self.encoder.embed(narratives, batch_size=batch_size)

        for i in range(0, total, batch_size):
            batch_data = records[i : i + batch_size]
            points = []

            for record in batch_data:
                try:
                    vector = next(embeddings_gen).tolist()
                    points.append(
                        PointStruct(id=str(uuid.uuid4()), vector=vector, payload=record)
                    )
                except StopIteration:
                    break

            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=False,  # Async indexing for speed
            )
            logger.info(f"Progress: {min(i + batch_size, total)}/{total} indexed.")

        logger.info("Indexing complete.")


if __name__ == "__main__":
    from src.log_engine import Tier2Refinery

    # 1. Run the Refinery
    refinery = Tier2Refinery(data_dir="data")
    intelligence_df = refinery.generate_intelligence_stream()

    # 2. Store in Qdrant
    if not intelligence_df.is_empty():
        db = SOCDatabase()
        db.init_collection()
        db.upload_data(intelligence_df)
    else:
        logger.error("The refinery stream is empty. Check your data paths.")
