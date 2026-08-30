import requests
import json
import os

def test_gfw_api():
    print("--- Global Fishing Watch (GFW) API Connection Test ---")
    
    # The official GFW API endpoint for vessel search
    gfw_url = "https://gateway.api.globalfishingwatch.org/v3/vessels/search"
    
    # We will try a basic query just to see if the server responds
    params = {
        "query": "ship",
        "limit": 1
    }
    
    # Check if the user has set an API key
    api_key = os.environ.get("GFW_API_KEY", "")
    
    headers = {
        "Authorization": f"Bearer {api_key}" if api_key else ""
    }
    
    print(f"[*] Pinging GFW API at: {gfw_url}")
    if not api_key:
        print("[!] No 'GFW_API_KEY' found in environment variables. Expecting 401 Unauthorized.")
    
    try:
        response = requests.get(gfw_url, params=params, headers=headers)
        
        print(f"[*] Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[+] SUCCESS: API connection is perfect and authenticated!")
            print(json.dumps(response.json(), indent=2))
        elif response.status_code == 401:
            print("[-] FAILED: 401 Unauthorized. The API is working, but it rejected our request because we don't have a valid API Key.")
        else:
            print(f"[-] FAILED: The API returned an unexpected status code: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"[-] FATAL ERROR: Could not reach the GFW servers. {e}")

if __name__ == "__main__":
    test_gfw_api()
