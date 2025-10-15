# Data collection module
import requests
import json
from datetime import datetime
import config

# In-memory cache for collected data
# In a real production app, you might use Redis or a database.
data_cache = {
    "system_health": None,
    "interfaces": None
}

def get_system_resources():
    """
    Collects system resource information (CPU, memory) from the switch.
    """
    payload = [
        {
            "jsonrpc": "2.0",
            "method": "cli",
            "params": {
                "cmd": "show system resources",
                "version": 1
            },
            "id": 1
        }
    ]
    try:
        response = requests.post(
            config.NXAPI_URL,
            auth=(config.SWITCH_USERNAME, config.SWITCH_PASSWORD),
            headers=config.NXAPI_HEADERS,
            data=json.dumps(payload),
            verify=False  # Disable SSL verification for self-signed certs
        )
        response.raise_for_status()
        data = response.json()['result']['body']
        return {
            "timestamp": datetime.now().isoformat(),
            "cpu_state": data.get('cpu_state'),
            "memory_usage": {
                "total": data.get('memory_usage_total'),
                "used": data.get('memory_usage_used'),
                "free": data.get('memory_usage_free'),
            }
        }
    except requests.exceptions.RequestException as e:
        print(f"Error collecting system resources: {e}")
        return None

def get_interface_status():
    """
    Collects interface brief information.
    """
    payload = [
        {
            "jsonrpc": "2.0",
            "method": "cli",
            "params": {
                "cmd": "show interface brief",
                "version": 1
            },
            "id": 1
        }
    ]
    try:
        response = requests.post(
            config.NXAPI_URL,
            auth=(config.SWITCH_USERNAME, config.SWITCH_PASSWORD),
            headers=config.NXAPI_HEADERS,
            data=json.dumps(payload),
            verify=False
        )
        response.raise_for_status()
        # The actual data is in result -> body -> TABLE_interface -> ROW_interface
        raw_interfaces = response.json()['result']['body']['TABLE_interface']['ROW_interface']
        
        # Filter and format the data
        interfaces = [
            {
                "interface": i.get("interface"),
                "state": i.get("state"),
                "vlan": i.get("vlan"),
                "duplex": i.get("duplex"),
                "speed": i.get("speed"),
                "type": i.get("type"),
            }
            for i in raw_interfaces
        ]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "interfaces": interfaces
        }

    except requests.exceptions.RequestException as e:
        print(f"Error collecting interface status: {e}")
        return None
    except KeyError:
        # This can happen if the switch response format is unexpected
        print("Error parsing interface data from switch response.")
        return None

def collect_all_data():
    """
    Runs all collector functions and updates the in-memory cache.
    This function is intended to be called periodically by the scheduler.
    """
    print(f"[{datetime.now()}] Running data collection cycle...")
    health_data = get_system_resources()
    if health_data:
        data_cache["system_health"] = health_data
    
    interface_data = get_interface_status()
    if interface_data:
        data_cache["interfaces"] = interface_data
    print("Data collection cycle finished.")

if __name__ == '__main__':
    # Example usage
    resources = get_system_resources()
    if resources:
        print(json.dumps(resources, indent=2))

    interfaces = get_interface_status()
    if interfaces:
        print("\n--- Interfaces ---")
        print(json.dumps(interfaces, indent=2))
