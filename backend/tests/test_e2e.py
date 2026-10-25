"""
End-to-end integration test against the running backend server.
"""

import time
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_e2e():
    print("--- 1. Testing Health and Status ---")
    health = requests.get(f"{BASE_URL}/health").json()
    print("Health response:", json.dumps(health, indent=2))
    assert health["status"] in ("healthy", "degraded")

    status = requests.get(f"{BASE_URL}/api/status").json()
    print("Status response:", json.dumps(status, indent=2))
    assert status["gemini_configured"] is True
    assert status["pinecone_configured"] is True

    print("\n--- 2. Uploading Test Document ---")
    doc_path = "data/data_structures_notes.txt"
    with open(doc_path, "rb") as f:
        files = {"file": ("data_structures_notes.txt", f, "text/plain")}
        upload_resp = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
    
    assert upload_resp.status_code == 200
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    print(f"Uploaded Document ID: {doc_id}, initial status: {doc_data['processing_status']}")

    print("\n--- 3. Waiting for Document Processing (Extraction -> Chunking -> Embedding -> Pinecone) ---")
    max_wait = 40
    start = time.time()
    final_doc = None
    while time.time() - start < max_wait:
        resp = requests.get(f"{BASE_URL}/api/documents/{doc_id}")
        if resp.status_code == 200:
            doc_detail = resp.json()
            doc_status = doc_detail["document"]["processing_status"]
            print(f"Current status: {doc_status} (chunks: {len(doc_detail.get('chunks', []))})")
            if doc_status == "READY":
                final_doc = doc_detail
                break
            elif doc_status == "FAILED":
                print("Document processing failed:", doc_detail["document"].get("error_message"))
                break
        time.sleep(2)

    assert final_doc is not None, "Document did not reach READY state"
    print(f"Document is READY with {len(final_doc['chunks'])} chunks indexed!")

    print("\n--- 4. Testing Semantic RAG Chat Query ---")
    chat_payload = {
        "question": "What is the balance factor of an AVL tree and what rotations are performed to rebalance it?",
        "document_ids": [doc_id],
        "mode": "documents_only"
    }
    chat_resp = requests.post(f"{BASE_URL}/api/chat", json=chat_payload)
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    print("Chat Answer:")
    print(chat_data["answer"][:300] + "...")
    print("Provenance:", chat_data["provenance"])
    print("Citations Count:", len(chat_data["citations"]))
    print("Context Verification:", chat_data.get("context_verification"))
    print("Answer Verification:", chat_data.get("answer_verification"))
    assert len(chat_data["citations"]) > 0

    time.sleep(2)
    print("\n--- 5. Testing Interactive MCQ Generation ---")
    mcq_payload = {
        "question": "Create 3 MCQs on AVL and Red-Black trees with options and explanations",
        "document_ids": [doc_id],
        "mode": "documents_only"
    }
    mcq_resp = requests.post(f"{BASE_URL}/api/chat", json=mcq_payload)
    assert mcq_resp.status_code == 200
    mcq_data = mcq_resp.json()
    print("MCQ Intent Detected:", mcq_data.get("intent"))
    print("Structured Content Generated:", type(mcq_data.get("structured_content")))

    print("\n--- 6. Testing Study Workbench Summarize ---")
    sum_resp = requests.post(f"{BASE_URL}/api/study/summarize", json={
        "document_ids": [doc_id],
        "detail_level": "standard"
    })
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    print("Summary Title:", sum_data.get("title"))
    print("Summary Content Excerpt:", sum_data.get("content")[:200] + "...")

    print("\n=== ALL END-TO-END TESTS COMPLETED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_e2e()
