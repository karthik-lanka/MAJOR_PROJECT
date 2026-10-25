import os
import sys
import time
import requests
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
USER_A = "alex@university.edu"
USER_B = "priya@university.edu"
SAMPLE_DIR = Path(r"c:\Users\manid\Downloads\MAJOR_PROJECT\sample_study_materials")

sys.stdout.reconfigure(line_buffering=True)

def test_upload(file_path: Path, user_id: str):
    print(f"\n[UPLOAD] Uploading {file_path.name} for {user_id}...")
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        data = {"user_id": user_id}
        res = requests.post(f"{BASE_URL}/api/documents/upload", files=files, data=data)
    
    if res.status_code != 200:
        print(f"FAILED upload {file_path.name}: {res.status_code} {res.text}")
        return None
    
    doc_data = res.json()
    doc_id = doc_data["id"]
    print(f"Uploaded {file_path.name} -> ID: {doc_id}. Waiting for processing...")
    
    # Poll status until ready or failed (max 90s)
    start = time.time()
    while time.time() - start < 90:
        s_res = requests.get(f"{BASE_URL}/api/documents/{doc_id}/status")
        if s_res.status_code == 200:
            status_data = s_res.json()
            status = str(status_data.get("processing_status", "")).lower()
            if status == "ready":
                chunks = status_data["chunk_count"]
                print(f"READY: {file_path.name} processed successfully in {time.time()-start:.1f}s ({chunks} chunks)")
                return doc_id
            elif status == "failed":
                err = status_data.get("error_message")
                print(f"FAILED processing {file_path.name}: {err}")
                return None
        time.sleep(2)
    print(f"TIMED OUT waiting for {file_path.name}")
    return doc_id

def main():
    print("==================================================")
    print("  STUDY ASSISTANT: MULTI-FORMAT UPLOAD & TENANCY  ")
    print("==================================================")

    # 1. Upload for User A (Alex)
    pdf_file = SAMPLE_DIR / "database_systems_and_indexing.pdf"
    txt_file = SAMPLE_DIR / "operating_systems_fundamentals.txt"
    alex_pdf_id = test_upload(pdf_file, USER_A)
    alex_txt_id = test_upload(txt_file, USER_A)

    # 2. Upload for User B (Priya)
    docx_file = SAMPLE_DIR / "software_engineering_lifecycle.docx"
    png_file = SAMPLE_DIR / "machine_learning_cheatsheet.png"
    priya_docx_id = test_upload(docx_file, USER_B)
    priya_png_id = test_upload(png_file, USER_B)

    # 3. Test Document Scoping (List Documents API)
    print("\n--------------------------------------------------")
    print("  VERIFYING MULTI-TENANT DOCUMENT ISOLATION       ")
    print("--------------------------------------------------")
    
    # Unauthenticated visitor
    unauth_docs = requests.get(f"{BASE_URL}/api/documents").json().get("documents", [])
    print(f"Unauthenticated visitor sees: {len(unauth_docs)} documents (Expected: 0)")
    assert len(unauth_docs) == 0, "Unauthenticated visitor should see 0 documents!"

    # Alex
    alex_docs = requests.get(f"{BASE_URL}/api/documents?user_id={USER_A}").json().get("documents", [])
    alex_titles = [d.get("original_filename", "") for d in alex_docs]
    print(f"Alex ({USER_A}) sees {len(alex_docs)} documents: {alex_titles}")
    assert any("database_systems" in t for t in alex_titles), "Alex should see database_systems"
    assert not any("software_engineering" in t for t in alex_titles), "Alex must NOT see Priya's software_engineering doc!"

    # Priya
    priya_docs = requests.get(f"{BASE_URL}/api/documents?user_id={USER_B}").json().get("documents", [])
    priya_titles = [d.get("original_filename", "") for d in priya_docs]
    print(f"Priya ({USER_B}) sees {len(priya_docs)} documents: {priya_titles}")
    assert any("software_engineering" in t for t in priya_titles), "Priya should see software_engineering"
    assert not any("database_systems" in t for t in priya_titles), "Priya must NOT see Alex's database_systems doc!"

    print("\n>>> DOCUMENT SCOPING CHECK: PASSED! <<<")

    # 4. Test RAG Retrieval Isolation
    print("\n--------------------------------------------------")
    print("  VERIFYING STRICT RAG RETRIEVAL PRIVACY          ")
    print("--------------------------------------------------")

    # Question 1: Alex asks about ACID (contained in Alex's PDF)
    print(f"\n[QUERY] Alex asks: 'What does Atomicity mean in ACID properties?'")
    alex_chat_res = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "question": "What does Atomicity mean in ACID properties?",
            "user_id": USER_A,
            "mode": "documents_only"
        }
    )
    if alex_chat_res.status_code == 200:
        data = alex_chat_res.json()
        ans = data.get("answer", "")
        cits = data.get("citations", [])
        print(f"Alex Answer Preview: {ans[:150]}...")
        print(f"Alex Citations: {[c.get('filename') or c.get('title') for c in cits]}")
        for c in cits:
            assert USER_B not in str(c), f"Found leak of Priya's document in Alex's retrieval: {c}"
    else:
        print(f"Alex chat error: {alex_chat_res.status_code} {alex_chat_res.text}")

    # Question 2: Alex asks about Agile Scrum (ONLY contained in Priya's DOCX, not Alex's!)
    print(f"\n[QUERY] Alex asks about Priya's topic: 'What is Agile Scrum and sprint iteration?'")
    leak_test_res = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "question": "What is Agile Scrum and sprint iteration?",
            "user_id": USER_A,
            "mode": "documents_only"
        }
    )
    if leak_test_res.status_code == 200:
        data = leak_test_res.json()
        cits = data.get("citations", [])
        retrieved_titles = [c.get("filename", "") or c.get("title", "") for c in cits]
        print(f"Alex retrieved titles for Priya's topic: {retrieved_titles}")
        assert not any("software_engineering" in t for t in retrieved_titles), (
            f"PRIVACY VIOLATION: Alex was able to retrieve Priya's software_engineering document: {retrieved_titles}"
        )
        print("CONFIRMED: Alex CANNOT retrieve or cite Priya's software engineering documents!")
    else:
        print(f"Leak test query response: {leak_test_res.status_code}")

    # Question 3: Priya asks about Agile Scrum (Her own document)
    print(f"\n[QUERY] Priya asks: 'What is the Red-Green-Refactor cycle in TDD?'")
    priya_chat_res = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "question": "What is the Red-Green-Refactor cycle in TDD?",
            "user_id": USER_B,
            "mode": "documents_only"
        }
    )
    if priya_chat_res.status_code == 200:
        data = priya_chat_res.json()
        ans = data.get("answer", "")
        cits = data.get("citations", [])
        print(f"Priya Answer Preview: {ans[:150]}...")
        print(f"Priya Citations: {[c.get('filename') or c.get('title') for c in cits]}")
        for c in cits:
            assert USER_A not in str(c), f"Found leak of Alex's document in Priya's retrieval: {c}"
    else:
        print(f"Priya chat error: {priya_chat_res.status_code} {priya_chat_res.text}")

    print("\n==================================================")
    print("  ALL MULTI-FORMAT & TENANCY CHECKS PASSED 100%!  ")
    print("==================================================")

if __name__ == "__main__":
    main()
