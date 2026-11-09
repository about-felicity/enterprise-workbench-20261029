-- Run outside a transaction so existing ingestion can continue during the build.
-- Hash the normalized prompt to keep index entries bounded for long questions.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ingest_original_prompt_hash
ON monitor_ingest_events (model_id, md5(btrim(regexp_replace(normalize(
    COALESCE(record->>'wire_question', record->>'prompt', record->>'question'), NFKC),
    '[[:space:]]+', ' ', 'g'))))
WHERE run_id <> '';
