"""
A simplified script to test the basic NX-API connection to a Nexus switch.
It performs a simple, read-only 'show version' command to isolate
connection issues from command execution issues.
"""
import requests
import json
import config

def test_simple_connection():
    """
    Connects to the switch and executes 'show version'.
    """
    print(f"--- Attempting to connect to {config.SWITCH_IP} ---")
    
    # This payload uses the 'cli' method for a read-only command.
    payload = {
        "jsonrpc": "2.0",
        "method": "cli",
        "params": {
            "cmd": "show version",
            "version": 1
        },
        "id": 1
    }

    try:
        response = requests.post(
            config.NXAPI_URL,
            auth=(config.SWITCH_USERNAME, config.SWITCH_PASSWORD),
            headers=config.NXAPI_HEADERS,
            data=json.dumps(payload),
            verify=False,  # Disable SSL verification for lab environments
            timeout=10     # Add a timeout to prevent hanging
        )
        response.raise_for_status()  # Raise an exception for HTTP errors

        result = response.json()

        if 'error' in result:
            print("\n--- Connection Test Failed (API Error) ---")
            print("The switch responded with an error:")
            print(json.dumps(result['error'], indent=2))
            return False
        
        print("\n--- Connection Test Successful ---")
        print("Successfully received data from the switch:")
        # Extracting and printing only the relevant 'body' part of the response
        print(json.dumps(result.get('result', {}).get('body', {}), indent=2))
        return True

    except requests.exceptions.SSLError as e:
        print("\n--- Connection Test Failed (SSL Error) ---")
        print("An SSL/TLS error occurred. This is likely a configuration issue on the Nexus switch.")
        print(f"Error details: {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print("\n--- Connection Test Failed (Connection Error) ---")
        print("Could not connect to the switch. Check IP address, port, and network connectivity (firewalls, etc.).")
        print(f"Error details: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n--- Connection Test Failed (General Request Error) ---")
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    test_simple_connection()
