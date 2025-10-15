# Deployment module for sending commands to the switch
import requests
import json
import config

def send_config_commands(commands):
    """
    Sends a list of configuration commands to the switch via NX-API.
    The commands are sent in a single transactional request.
    
    Args:
        commands (list): A list of CLI commands to execute.

    Returns:
        tuple: (bool, list) where bool is True on success and list contains
               the JSON-RPC response for each command.
    """
    payload = []
    for i, cmd in enumerate(commands, 1):
        payload.append({
            "jsonrpc": "2.0",
            "method": "cli_conf", # Use 'cli_conf' for configuration mode
            "params": {
                "cmd": cmd,
                "version": 1
            },
            "id": i
        })

    print(f"Sending {len(commands)} commands to {config.NXAPI_URL}...")
    
    try:
        # It's highly recommended to use proper certificate management in production
        response = requests.post(
            config.NXAPI_URL,
            auth=(config.SWITCH_USERNAME, config.SWITCH_PASSWORD),
            headers=config.NXAPI_HEADERS,
            data=json.dumps(payload),
            verify=False  # In a lab, we disable SSL verification.
        )
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error sending commands to switch: {e}")
        return False, [{"error": str(e)}]

    results = response.json()
    
    # Check for errors in the response from the switch
    # The response is a list if multiple commands were sent
    if isinstance(results, list):
        for res in results:
            if 'error' in res:
                print(f"An error occurred in command execution: {res['error']}")
                return False, results
    # Handle single command response
    elif 'error' in results:
        print(f"An error occurred in command execution: {results['error']}")
        return False, [results]

    print("Commands executed successfully.")
    return True, results

if __name__ == '__main__':
    # Example usage: create a test vlan
    print("--- Running standalone test for deployer ---")
    test_commands = [
        "vlan 123",
        "name TEST_VLAN_FROM_SCRIPT"
    ]
    success, result_data = send_config_commands(test_commands)
    print("\n--- Results ---")
    print(f"Success: {success}")
    print("Response JSON:")
    print(json.dumps(result_data, indent=2))

    # Example of cleanup
    print("\n--- Cleaning up ---")
    cleanup_commands = ["no vlan 123"]
    send_config_commands(cleanup_commands)
