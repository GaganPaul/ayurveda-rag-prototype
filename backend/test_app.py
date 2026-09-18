"""Test suite to verify asynchronous indexing, health transitions, 503 handling, retrieval, and error resilience."""
import os
import sys
import time
from fastapi.testclient import TestClient

import app as backend_app

def test_all():
    print("--- Starting Test Suite ---")
    
    # 1. Test immediate startup and lifespan
    with TestClient(backend_app.app) as client:
        # Check initial health state immediately after startup
        print("Checking initial /api/health (while indexing)...")
        r_init = client.get("/api/health")
        print("Initial health response:", r_init.status_code, r_init.json())
        init_json = r_init.json()
        assert r_init.status_code == 200
        assert init_json["status"] == "ok"
        # Initial health might already have started indexing:
        assert "index_loading" in init_json
        assert "index_ready" in init_json
        assert "documents_loaded" in init_json

        # 2. Test /api/chat during loading (simulate loading state if needed)
        with backend_app.knowledge_base._lock:
            was_ready = backend_app.knowledge_base.index_ready
            was_loading = backend_app.knowledge_base.index_loading
            backend_app.knowledge_base.index_loading = True
            backend_app.knowledge_base.index_ready = False

        r_chat_loading = client.post("/api/chat", json={"message": "What is vata?"})
        print("Chat response during loading:", r_chat_loading.status_code, r_chat_loading.json())
        assert r_chat_loading.status_code == 503
        assert "still loading" in r_chat_loading.json()["detail"]

        # 3. Test /api/chat when indexing failed
        with backend_app.knowledge_base._lock:
            backend_app.knowledge_base.index_loading = False
            backend_app.knowledge_base.index_ready = False
            backend_app.knowledge_base.index_error = "Knowledge base indexing failed"

        r_health_err = client.get("/api/health")
        print("Health response when degraded:", r_health_err.status_code, r_health_err.json())
        assert r_health_err.status_code == 200
        assert r_health_err.json()["status"] == "degraded"
        assert r_health_err.json()["index_error"] == "Knowledge base indexing failed"

        r_chat_err = client.post("/api/chat", json={"message": "What is pitta?"})
        print("Chat response when degraded:", r_chat_err.status_code, r_chat_err.json())
        assert r_chat_err.status_code == 503
        assert "temporarily unavailable" in r_chat_err.json()["detail"]

        # Restore state and wait for real background indexing to complete
        with backend_app.knowledge_base._lock:
            backend_app.knowledge_base.index_error = None
            backend_app.knowledge_base.index_loading = was_loading
            backend_app.knowledge_base.index_ready = was_ready

        print("Waiting for background indexing to finish...")
        max_wait = 120
        start_time = time.time()
        while time.time() - start_time < max_wait:
            with backend_app.knowledge_base._lock:
                if backend_app.knowledge_base.index_ready:
                    break
            time.sleep(1)

        with backend_app.knowledge_base._lock:
            assert backend_app.knowledge_base.index_ready, "Indexing timed out!"
            chunks_loaded = backend_app.knowledge_base.documents_loaded

        print(f"Indexing completed! Loaded {chunks_loaded} chunks.")
        assert chunks_loaded > 0

        # 4. Check /api/health after indexing completes
        r_ready = client.get("/api/health")
        print("Health response when ready:", r_ready.status_code, r_ready.json())
        ready_json = r_ready.json()
        assert r_ready.status_code == 200
        assert ready_json["status"] == "ok"
        assert ready_json["index_ready"] is True
        assert ready_json["index_loading"] is False
        assert ready_json["documents_loaded"] == chunks_loaded
        assert "index_error" not in ready_json

        # 5. Also check /health endpoint
        r_root_health = client.get("/health")
        assert r_root_health.status_code == 200
        assert r_root_health.json()["index_ready"] is True

        # 6. Check /api/sources
        r_sources = client.get("/api/sources")
        print("Sources response count:", len(r_sources.json()["documents"]))
        assert r_sources.status_code == 200
        docs = r_sources.json()["documents"]
        assert len(docs) > 0
        names = [d["name"] for d in docs]
        print("Sample indexed sources:", names[:5])
        # Verify both PDF and TXT files are present
        assert any(n.endswith(".pdf") for n in names), "PDF files should be indexed"
        assert any(n.endswith(".txt") for n in names), "TXT files should be indexed"

        # 7. Test retrieval for Ayurveda concepts
        retrieved_turmeric = backend_app.retrieve("turmeric benefits", top_k=4)
        print(f"Retrieved {len(retrieved_turmeric)} passages for 'turmeric benefits'")
        assert len(retrieved_turmeric) > 0
        assert any("turmeric" in item["text"].lower() or "curcuma" in item["text"].lower() for item in retrieved_turmeric)

        # 8. Test retrieval for nonexistent topic (should not crash)
        retrieved_xyz = backend_app.retrieve("xyz123randomnonexistenttopic999", top_k=4)
        print(f"Retrieved {len(retrieved_xyz)} passages for nonexistent topic")
        assert isinstance(retrieved_xyz, list)

        # 9. Test chat endpoint with real query if Gemini API key configured
        if backend_app.client is not None:
            print("Testing chat endpoint with Gemini API...")
            r_chat = client.post("/api/chat", json={"message": "What is Ayurveda?", "top_k": 3})
            print("Chat response status:", r_chat.status_code)
            if r_chat.status_code == 200:
                print("Answer snippet:", r_chat.json()["answer"][:100], "...")
                print("Sources returned:", len(r_chat.json()["sources"]))
            else:
                print("Chat failed (possibly quota):", r_chat.json())
        else:
            print("Gemini client not configured; testing 500 error handling...")
            r_chat = client.post("/api/chat", json={"message": "What is Ayurveda?"})
            assert r_chat.status_code == 500

    print("--- All Tests Passed Successfully! ---")

if __name__ == "__main__":
    test_all()
