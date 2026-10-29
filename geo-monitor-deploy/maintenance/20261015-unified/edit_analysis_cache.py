from pathlib import Path
path=Path('geo-monitor-deploy/server-source/doubao_dashboard_server.py')
text=path.read_text('utf-8-sig')
start=text.index('        # A completed date-scoped payload is safe to paint immediately after')
end=text.index('        try:\n            database_cached =',start)
text=text[:start]+'''        # A disk payload has no authoritative scope version. A matching date
        # alone cannot prove freshness after ingestion/backfill. Prefer the
        # PostgreSQL cache, whose version is checked in the same transaction.
'''+text[end:]
anchor='def _unified_analytics(params):'
helper='''def _analytics_result_state(result, *, current):
    # Return a copy: never mark an underlying cached snapshot as validated.
    return {**result, "cache_status": {
        "state": "current" if current else "refreshing",
        "message": "统计已核对数据库版本；快照时间：" if current else "统计正在刷新，以下为上次完整快照：",
        "generated_at": result.get("generated_at", ""),
    }}


'''
assert anchor in text;text=text.replace(anchor,helper+anchor,1)
start=text.index(anchor);end=text.index('\n\ndef _source_intersection_cache_path',start)
part=text[start:end]
part=part.replace('                    return cached[1]','                    return _analytics_result_state(cached[1], current=True)')
part=part.replace('        return cached[1]','        return _analytics_result_state(cached[1], current=False)')
part=part.replace('        return _unified_analytics_without_coalescing(params)', '''        result = _unified_analytics_without_coalescing(params)
        try:
            with _ANALYTICS_LOCK:
                entry = _ANALYTICS_CACHE.get(cache_key)
            current = bool(entry and entry[0] == _analytics_data_version(cache_key))
        except Exception:
            current = False
        return _analytics_result_state(result, current=current)''')
text=text[:start]+part+text[end:]
text=text.replace('                run["answer"] = clean_answer','''                # Audit display preserves every captured character. Analysis
                # may exclude a related-content drawer, but the user must be
                # able to inspect the exact stored answer, including formatting.
                run["answer"] = raw_answer''')
text=text.replace('                run["answer_trailing_content_removed"] = clean_answer != raw_answer.strip()',
                  '                run["answer_trailing_content_removed"] = False\n                run["analysis_body_differs_from_raw"] = clean_answer != raw_answer.strip()')
path.write_text(text,encoding='utf8')
