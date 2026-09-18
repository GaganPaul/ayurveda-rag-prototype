"""Test suite to verify pre-built TF-IDF index loading, health checks, retrieval, admin reindexing, and error handling."""
import os
from pathlib import Path
import sys
import tempfile
from fastapi.testclient import TestClient

import app as backend_app
from rag_index import (
    CHUNKS_FILE,
    MATRIX_FILE,
    METADATA_FILE,
    VECTORIZER_FILE,
    atomic_reindex,
    validate_index,
)


def test_all():
    print("--- Starting Test Suite for Pre-built RAG Index ---")

    # Ensure index exists before testing startup
    if not (backend_app.INDEX_DIR / CHUNKS_FILE).exists():
        print("Pre-built index not found in backend/index; building it now for tests...")
        atomic_reindex(
            data_dir=backend_app.DATA_DIR,
            index_dir=backend_app.INDEX_DIR,
            tmp_dir=backend_app.INDEX_BUILD_TMP_DIR,
        )

    # 1. Test startup with pre-built index
    with TestClient(backend_app.app) as client:
        print("Checking /api/health with pre-built index...")
        r_health = client.get("/api/health")
        assert r_health.status_code == 200
        health_json = r_health.json()
        print("Health response:", health_json)
        assert health_json["status"] == "ok"
        assert health_json["index_ready"] is True
        assert health_json["index_loading"] is False
        assert health_json["index_type"] == "prebuilt_tfidf"
        assert health_json["documents_loaded"] > 0
        chunks_count = health_json["documents_loaded"]

        # 2. Test root /health endpoint
        r_root_health = client.get("/health")
        assert r_root_health.status_code == 200
        assert r_root_health.json()["index_ready"] is True

        # 3. Test /api/sources endpoint
        r_sources = client.get("/api/sources")
        assert r_sources.status_code == 200
        docs = r_sources.json()["documents"]
        assert len(docs) > 0
        names = [d["name"] for d in docs]
        print(f"Sources endpoint returned {len(docs)} documents.")
        assert any(n.endswith(".pdf") for n in names), "PDF files should be present in sources"
        assert any(n.endswith(".txt") for n in names), "TXT files should be present in sources"

        # 4. Test retrieval function
        retrieved_turmeric = backend_app.retrieve("turmeric benefits", top_k=4)
        print(f"Retrieved {len(retrieved_turmeric)} passages for 'turmeric benefits'")
        assert len(retrieved_turmeric) > 0
        assert any(
            "turmeric" in item["text"].lower() or "curcuma" in item["text"].lower()
            for item in retrieved_turmeric
        )
        # Check enriched metadata fields
        sample = retrieved_turmeric[0]
        assert "name" in sample
        assert "page" in sample
        assert "id" in sample
        assert "category" in sample

        # 5. Test nonexistent query retrieval
        retrieved_xyz = backend_app.retrieve("xyz123randomnonexistenttopic999", top_k=4)
        assert isinstance(retrieved_xyz, list)

        # 6. Test /api/chat when knowledge base is ready
        if backend_app.client is not None:
            print("Testing /api/chat with Gemini...")
            r_chat = client.post("/api/chat", json={"message": "What is Ayurveda?", "top_k": 3})
            print("Chat response status:", r_chat.status_code)
            if r_chat.status_code == 200:
                print("Answer preview:", r_chat.json()["answer"][:100], "...")
                print("Sources returned:", len(r_chat.json()["sources"]))
            else:
                print("Chat API returned:", r_chat.json())
        else:
            print("Gemini client not configured; testing 500 handling...")
            r_chat = client.post("/api/chat", json={"message": "What is Ayurveda?"})
            assert r_chat.status_code == 500

        # 7. Test 503 response during loading state simulation
        with backend_app.knowledge_base._lock:
            backend_app.knowledge_base.index_loading = True
            backend_app.knowledge_base.index_ready = False

        r_chat_loading = client.post("/api/chat", json={"message": "What is vata?"})
        assert r_chat_loading.status_code == 503
        assert "currently loading" in r_chat_loading.json()["detail"]

        # 8. Test 503 response and degraded status during error state simulation
        with backend_app.knowledge_base._lock:
            backend_app.knowledge_base.index_loading = False
            backend_app.knowledge_base.index_ready = False
            backend_app.knowledge_base.index_error = "Test simulated failure"

        r_health_degraded = client.get("/api/health")
        assert r_health_degraded.json()["status"] == "degraded"
        assert r_health_degraded.json()["index_error"] == "Test simulated failure"

        r_chat_degraded = client.post("/api/chat", json={"message": "What is pitta?"})
        assert r_chat_degraded.status_code == 503
        assert "temporarily unavailable" in r_chat_degraded.json()["detail"]

        # Restore normal state
        with backend_app.knowledge_base._lock:
            backend_app.knowledge_base.index_error = None
            backend_app.knowledge_base.index_loading = False
            backend_app.knowledge_base.index_ready = True

        # 9. Test admin endpoints
        admin_token = backend_app.ADMIN_TOKEN or "local-development-token"
        backend_app.ADMIN_TOKEN = admin_token

        # Test unauthorized admin request
        r_admin_unauth = client.post("/api/admin/reindex")
        assert r_admin_unauth.status_code == 401

        # Test authorized admin status
        r_admin_status = client.get(
            "/api/admin/status",
            headers={"X-Admin-Token": admin_token},
        )
        assert r_admin_status.status_code == 200
        assert r_admin_status.json()["index_ready"] is True

        # Test authorized admin reindex
        print("Testing admin reindex...")
        r_admin_reindex = client.post(
            "/api/admin/reindex",
            headers={"X-Admin-Token": admin_token},
        )
        assert r_admin_reindex.status_code == 200
        reindex_json = r_admin_reindex.json()
        print("Admin reindex response:", reindex_json)
        assert reindex_json["status"] == "ok"
        assert reindex_json["chunks"] > 0

    print("--- All Tests Passed Successfully! ---")


if __name__ == "__main__":
    test_all()
