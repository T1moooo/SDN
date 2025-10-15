"""
This script is the primary deliverable for Week 1's core task.
It demonstrates how to programmatically configure QoS on a Nexus 9000v switch
using Python and the NX-API REST interface.

This script performs the following actions:
1. Defines all necessary QoS components: ACL, Class Map, Policy Map.
2. Applies the policy to a specific interface.
3. Provides a cleanup function to remove the configuration.

**Prerequisites:**
- A running Nexus 9000v switch with NX-API enabled (`feature nxapi`).
- Network connectivity from the script's host to the switch's management IP.
- `requests` and `python-dotenv` libraries installed (`pip install -r requirements.txt`).
- A `.env` file created from `.env.example` with correct switch credentials.
"""
import json
from deployer import send_config_commands

# --- Configuration Variables ---
# These variables define the QoS policy we want to create.
# In a real application, these would come from a YAML file or a UI.
TARGET_INTERFACE = "Ethernet1/1"
POLICY_NAME = "COURSE_SELECTION_APP"
SOURCE_IP = "10.1.1.10/32"  # IP of the critical application server
PRIORITY_DSCP = "af41"      # DSCP value for high priority traffic

# --- Derived Names ---
# We derive the names of the configuration objects from the policy name
# to ensure they are unique and easy to identify.
ACL_NAME = f"ACL_{POLICY_NAME}"
CLASS_MAP_NAME = f"CM_{POLICY_NAME}"
POLICY_MAP_NAME = f"PM_{POLICY_NAME}"


def apply_qos_policy():
    """
    Builds and sends the commands to apply the full QoS policy.
    """
    print("--- Applying QoS Policy ---")
    
    # The commands are ordered to respect dependencies (e.g., ACL must exist before class-map uses it).
    commands = [
        # 1. Configure an Access Control List (ACL) to identify the traffic.
        f"ip access-list {ACL_NAME}",
        f"10 permit ip {SOURCE_IP} any",
        
        # 2. Configure a Class Map to group the traffic based on the ACL.
        f"class-map type qos {CLASS_MAP_NAME}",
        f"match access-group name {ACL_NAME}",
        
        # 3. Configure a Policy Map to define the action (set DSCP value).
        f"policy-map type qos {POLICY_MAP_NAME}",
        f"class {CLASS_MAP_NAME}",
        f"set dscp {PRIORITY_DSCP}",
        
        # 4. Apply the Policy Map to the target interface.
        f"interface {TARGET_INTERFACE}",
        f"service-policy type qos input {POLICY_MAP_NAME}"
    ]
    
    success, results = send_config_commands(commands)
    
    print("\n--- Policy Application Results ---")
    print(f"Success: {success}")
    print("Full Response:")
    print(json.dumps(results, indent=2))
    return success

def remove_qos_policy():
    """
    Builds and sends the commands to remove the QoS policy and its components.
    This is crucial for testing and cleanup.
    """
    print("\n--- Removing QoS Policy ---")
    
    # Cleanup should be done in the reverse order of creation to handle dependencies.
    commands = [
        # 1. Remove the policy from the interface.
        f"interface {TARGET_INTERFACE}",
        f"no service-policy type qos input {POLICY_MAP_NAME}",
        
        # 2. Remove the Policy Map.
        f"no policy-map type qos {POLICY_MAP_NAME}",
        
        # 3. Remove the Class Map.
        f"no class-map type qos {CLASS_MAP_NAME}",
        
        # 4. Remove the ACL.
        f"no ip access-list {ACL_NAME}"
    ]
    
    success, results = send_config_commands(commands)
    
    print("\n--- Policy Removal Results ---")
    print(f"Success: {success}")
    print("Full Response:")
    print(json.dumps(results, indent=2))
    return success

if __name__ == "__main__":
    print("Starting QoS configuration script...")
    
    # Apply the policy
    if apply_qos_policy():
        print("\nQoS policy applied successfully.")
        # Wait for user input before cleaning up, so you can verify on the switch.
        input("Press Enter to proceed with cleanup...")
    else:
        print("\nFailed to apply QoS policy. Check errors above.")
        # Even on failure, try to clean up any partial configuration.
        input("Press Enter to attempt cleanup anyway...")

    # Remove the policy
    if remove_qos_policy():
        print("\nQoS policy removed successfully.")
    else:
        print("\nFailed to remove QoS policy. Manual cleanup on the switch may be required.")
