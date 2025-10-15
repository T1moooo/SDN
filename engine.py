# Policy engine module
import yaml
import json
from deployer import send_config_commands

def _translate_policy_to_commands(policy):
    """
    Translates a single policy definition from YAML into a sequence of NX-API CLI commands.
    This is the core logic of the policy engine.
    """
    commands = []
    policy_name = policy['name']
    match_ip = policy['match']['source_ip']
    priority = policy['action']['set_priority']
    interface = policy['target_interface']

    acl_name = f"ACL_{policy_name}"
    class_map_name = f"CM_{policy_name}"
    policy_map_name = f"PM_{policy_name}"

    # 1. Create/Update Access Control List (ACL)
    commands.append(f"ip access-list {acl_name}")
    commands.append(f"10 permit ip {match_ip} any")

    # 2. Create/Update Class Map to use the ACL
    commands.append(f"class-map type qos {class_map_name}")
    commands.append(f"match access-group name {acl_name}")

    # 3. Create/Update Policy Map to set priority
    commands.append(f"policy-map type qos {policy_map_name}")
    commands.append(f"class {class_map_name}")
    commands.append(f"set dscp {priority}")

    # 4. Apply Policy Map to the target interface
    commands.append(f"interface {interface}")
    commands.append(f"service-policy type qos input {policy_map_name}")

    return commands

def apply_policy_from_yaml(yaml_file_path):
    """
    Reads a YAML policy file, translates it, and sends it to the switch.
    """
    try:
        with open(yaml_file_path, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return False, f"Policy file not found: {yaml_file_path}"
    except yaml.YAMLError as e:
        return False, f"Error parsing YAML file: {e}"

    all_commands = []
    for policy in data.get('policies', []):
        commands = _translate_policy_to_commands(policy)
        all_commands.extend(commands)

    if not all_commands:
        return False, "No valid policies found in the file."

    success, results = send_config_commands(all_commands)
    
    if success:
        return True, "Policy applied successfully."
    else:
        # Attempt to format the error message
        error_details = ""
        for i, result in enumerate(results):
            if result and 'error' in result:
                 # NX-API often puts error details in result -> body -> msg
                error_body = result.get('result', {}).get('body', {})
                error_msg = error_body.get('msg', 'Unknown error')
                error_details += f"Command '{all_commands[i]}' failed: {error_msg}. "
        
        return False, f"Failed to apply policy. Details: {error_details or results}"

if __name__ == '__main__':
    # Example usage:
    # Create a dummy policy.yaml file first
    dummy_policy = {
        "policies": [
            {
                "name": "ensure-course-selection-priority",
                "match": {"source_ip": "10.1.1.10/32"},
                "action": {"set_priority": "af41"},
                "target_interface": "Ethernet1/1"
            }
        ]
    }
    with open("policy.yaml", "w") as f:
        yaml.dump(dummy_policy, f)

    print("Applying policy from policy.yaml...")
    success, message = apply_policy_from_yaml('policy.yaml')
    print(f"Status: {'Success' if success else 'Failure'}")
    print(f"Message: {message}")
