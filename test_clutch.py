import os
import sys

# Ensure src is in path so we can import our main FastAPI app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from fastapi.testclient import TestClient
    from main import app
    import asyncio
except ImportError as e:
    print(f"Failed to import dependencies: {e}. Are you running in the venv?")
    sys.exit(1)

client = TestClient(app)

print("\n=== TEST 1: Safe, Normal Command ===")
res1 = client.post("/v1/execute", json={"command": "echo 'Hello, World! I am a safe AI agent.'"})
print(f"Status Code: {res1.status_code}")
print(f"Response: {res1.json()}")

print("\n=== TEST 2: The Context Clutch (Massive Output) ===")
# We ask python to print 5000 characters to intentionally trigger the truncator (limit is 2000)
massive_cmd = "python3 -c \"print('A' * 5000)\""
res2 = client.post("/v1/execute", json={"command": massive_cmd})
print(f"Status Code: {res2.status_code}")
data2 = res2.json()
print(f"Was Truncated?: {data2.get('truncated')}")
if data2.get("truncated"):
    output_preview = data2.get("output", "")
    print(f"Length of returned output: {len(output_preview)} chars (Clutch Successfully Engaged!)")
    # Show the middle section of the output where the injection happens
    mid = len(output_preview) // 2
    preview = output_preview[mid-100:mid+100]
    print(f"Clutch Injection Snippet:\n{preview}")

print("\n=== TEST 3: Semantic Security Guardrail ===")
res3 = client.post("/v1/execute", json={"command": "rm -rf /var/www/html"})
print(f"Status Code: {res3.status_code}")
if res3.status_code == 403:
    print(f"Security Block: {res3.json()}")

print("\n=== TEST 4: HIPAA / PII Redaction Template Engine ===")
test_text = "History: Patient admitted 12/05/2023. MRN: PAT-847291. Email: test@clinic.com. Phone: 555-019-2830. IP: 192.168.1.5"
res4 = client.post("/v1/execute", json={"command": f"echo '{test_text}'"})
print(f"Status Code: {res4.status_code}")
data4 = res4.json()
print(f"Original Text: {test_text}")
print(f"Redacted Output: {data4.get('output', '').strip()}")

print("\nAll MVP tests completed.")
