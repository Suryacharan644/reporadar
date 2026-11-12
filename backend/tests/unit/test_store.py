"""Supabase persistence over PostgREST, exercised with a mock transport (no network)."""

import asyncio
import json

import httpx

from app.infra import SupabaseStore
from tests.helpers import healthy_snapshot
from app.report import build_report


def test_supabase_store_saves_and_loads_with_service_key_headers():
    captured: list[httpx.Request] = []
    saved_rows: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.method == "POST":
            saved_rows.append(json.loads(request.content))
            return httpx.Response(201)
        if request.method == "GET":
            wanted = request.url.params["id"].removeprefix("eq.")
            rows = [{"report": r["report"]} for r in saved_rows if r["id"] == wanted]
            return httpx.Response(200, json=rows)
        return httpx.Response(405)

    store = SupabaseStore("https://example.supabase.co", "service-key", transport=httpx.MockTransport(handler))
    report = build_report(healthy_snapshot())

    async def go():
        report_id = await store.save(report)
        loaded = await store.get(report_id)
        missing = await store.get("does-not-exist")
        await store.aclose()
        return report_id, loaded, missing

    report_id, loaded, missing = asyncio.run(go())
    assert loaded["repo"]["full_name"] == "octo/widget"
    assert missing is None
    assert len(report_id) >= 9

    post = captured[0]
    assert post.url.path == "/rest/v1/reports"
    assert post.headers["apikey"] == "service-key"
    assert post.headers["authorization"] == "Bearer service-key"
    row = saved_rows[0]
    assert row["repo_full_name"] == "octo/widget" and row["score"] == 100
