import logging

import inngest
import inngest.fast_api
import polars as pl
from fastapi import FastAPI

from app.database import SOCDatabase
from app.log_engine import Tier2Refinery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

inngest_client = inngest.Inngest(
    app_id="sentinel_rag_engine", logger=logger, is_production=False
)


@inngest_client.create_function(
    fn_id="ingest_and_index_logs",
    trigger=inngest.TriggerEvent(event="logs/uploaded"),
)
async def process_log_stream(ctx: inngest.Context):
    file_path = ctx.event.data.get("file_path")

    async def run_refinery():
        refinery = Tier2Refinery()
        df = refinery.process_cloud(file_path)

        if isinstance(df, pl.DataFrame):
            return df.to_dicts()
        return df

    refined_data = await ctx.step.run("refine_logs", run_refinery)

    async def run_indexing():
        if not refined_data:
            return 0

        db = SOCDatabase()
        df_to_upload = pl.DataFrame(refined_data)
        db.upload_data(df_to_upload)

        return len(refined_data)

    count = await ctx.step.run("index_to_qdrant", run_indexing)

    return {"status": "completed", "count": count}


@inngest_client.create_function(
    fn_id="log_qa_audit",
    trigger=inngest.TriggerEvent(event="audit/question_asked"),
)
async def log_qa_audit(ctx: inngest.Context):
    data = ctx.event.data

    logger.info(f"AUDIT | Query: {data.get('question')}")
    logger.info(f"CONFIDENCE | {data.get('score')}")

    return {"status": "recorded"}


app = FastAPI()
inngest.fast_api.serve(app, inngest_client, [process_log_stream, log_qa_audit])
