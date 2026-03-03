import re
from pathlib import Path

import polars as pl


class Tier2Refinery:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir).expanduser()

    def process_all_attacks(self) -> pl.DataFrame:
        attack_base = self.data_dir / "attack_sigs" / "attack_techniques"
        dfs = []
        for log_file in attack_base.rglob("*.log"):
            parts = log_file.parts
            tech_id, tactic_name = "Unknown", "General Attack"
            for i, part in enumerate(parts):
                if re.match(r"T\d{4}", part):
                    tech_id = part
                    if i + 1 < len(parts):
                        tactic_name = parts[i + 1].replace("_", " ").title()
                    break
            try:
                df = pl.read_csv(
                    log_file,
                    has_header=False,
                    separator="\n",
                    new_columns=["raw_text"],
                    truncate_ragged_lines=True,
                )
                df = df.with_columns(
                    [
                        pl.lit(tech_id).alias("mitre_id"),
                        pl.lit(tactic_name).alias("tactic"),
                        pl.lit(3).alias("severity"),
                        pl.format(
                            "CRITICAL: {} ({}) | Log: {}",
                            pl.lit(tactic_name),
                            pl.lit(tech_id),
                            pl.col("raw_text").str.slice(0, 150),
                        ).alias("narrative"),
                    ]
                )
                dfs.append(df)
            except Exception:
                continue
        return pl.concat(dfs) if dfs else pl.DataFrame()

    def process_baseline(self) -> pl.DataFrame:
        dfs = []
        for f in self.data_dir.glob("baseline/*.log"):
            system = f.stem.split("_")[0]
            try:
                df = pl.read_csv(
                    f, has_header=False, separator="\n", new_columns=["raw_text"]
                )
                df = df.with_columns(
                    [
                        pl.lit("N/A").alias("mitre_id"),
                        pl.lit("Normal Operations").alias("tactic"),
                        pl.lit(0).alias("severity"),
                        pl.format(
                            "BASELINE ({}): {}",
                            pl.lit(system),
                            pl.col("raw_text").str.slice(0, 150),
                        ).alias("narrative"),
                    ]
                )
                dfs.append(df)
            except Exception:
                continue
        return pl.concat(dfs) if dfs else pl.DataFrame()

    def process_cloud(self) -> pl.DataFrame:
        dfs = []
        for f in self.data_dir.glob("raw_logs/CloudTrail/*.json"):
            try:
                df = (
                    pl.read_json(f)
                    .select(pl.col("Records"))
                    .explode("Records")
                    .unnest("Records")
                )
                df = df.with_columns(
                    [
                        pl.lit("T1078").alias("mitre_id"),
                        pl.lit("Cloud Telemetry").alias("tactic"),
                        pl.lit(1).alias("severity"),
                        pl.format(
                            "OBSERVATION: Cloud event '{}' via user '{}'",
                            pl.col("eventName"),
                            pl.col("userIdentity")
                            .struct.field("userName")
                            .fill_null("unknown"),
                        ).alias("narrative"),
                    ]
                )
                dfs.append(df.select(["mitre_id", "tactic", "severity", "narrative"]))
            except Exception:
                continue
        return pl.concat(dfs) if dfs else pl.DataFrame()

    def generate_intelligence_stream(self) -> pl.DataFrame:
        data_sources = [
            self.process_all_attacks(),
            self.process_baseline(),
            self.process_cloud(),
        ]
        valid_dfs = [df for df in data_sources if not df.is_empty()]
        if not valid_dfs:
            return pl.DataFrame()
        # Deduplicate to keep the RAG lean
        return pl.concat(valid_dfs, how="diagonal").unique(subset=["narrative"])
