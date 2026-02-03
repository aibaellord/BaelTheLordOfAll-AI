#!/usr/bin/env python3
"""BAEL Singularity API Test Script."""

import json
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000"

def test_endpoint(method: str, path: str, data: dict = None):
    """Test an API endpoint."""
    url = f"{BASE_URL}{path}"
    print(f"\n{'='*60}")
    print(f"{method} {path}")
    print('='*60)

    try:
        if method == "GET":
            req = urllib.request.Request(url)
        else:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode() if data else None,
                headers={"Content-Type": "application/json"}
            )
            req.method = method

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            print(f"Status: {response.status}")
            print(f"Response: {json.dumps(result, indent=2)[:2000]}")
            return result

    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(f"Body: {e.read().decode()[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    return None

def main():
    print("\n" + "🔥" * 30)
    print(" BAEL SINGULARITY API TEST SUITE")
    print("🔥" * 30)

    # Test root
    test_endpoint("GET", "/")

    # Test health
    test_endpoint("GET", "/health")

    # Test Singularity status
    test_endpoint("GET", "/api/singularity/status")

    # Test capabilities
    result = test_endpoint("GET", "/api/singularity/capabilities")
    if result and result.get("success"):
        caps = result.get("data", {})
        total = sum(len(v) for v in caps.values())
        print(f"\n📊 Total Capabilities: {total} across {len(caps)} domains")

    # Test think
    test_endpoint("POST", "/api/singularity/think", {
        "query": "What is consciousness?",
        "depth": "deep"
    })

    # Test reason
    test_endpoint("POST", "/api/singularity/reason", {
        "query": "If all humans need water to survive, and Alice is human, what can we conclude about Alice?"
    })

    # Test introspect
    test_endpoint("GET", "/api/singularity/introspect")

    print("\n" + "✅" * 30)
    print(" ALL TESTS COMPLETE!")
    print("✅" * 30 + "\n")

if __name__ == "__main__":
    main()
