# Main application file (Flask web server)
from flask import Flask, jsonify, request, render_template
from apscheduler.schedulers.background import BackgroundScheduler
from engine import apply_policy_from_yaml
from collector import collect_all_data, data_cache
import config

app = Flask(__name__)

@app.route('/dashboard')
def dashboard():
    """
    Serves the main monitoring dashboard.
    """
    return render_template('index.html')

@app.route('/api/system-health')
def api_system_health():
    """
    API endpoint to get the latest system health data.
    """
    health_data = data_cache.get("system_health")
    if health_data:
        return jsonify(health_data)
    return jsonify({"error": "No health data available yet."}), 503

@app.route('/api/interfaces')
def api_interfaces():
    """
    API endpoint to get the latest interface status data.
    """
    interface_data = data_cache.get("interfaces")
    if interface_data:
        return jsonify(interface_data)
    return jsonify({"error": "No interface data available yet."}), 503

@app.route('/api/apply-policy', methods=['POST'])
def api_apply_policy():
    """
    API endpoint to trigger applying a policy from a YAML file.
    Expects a JSON payload with 'policy_file' key.
    e.g., {"policy_file": "policy.yaml"}
    """
    data = request.get_json()
    if not data or 'policy_file' not in data:
        return jsonify({"status": "error", "message": "Missing 'policy_file' in request"}), 400

    policy_file = data['policy_file']
    success, message = apply_policy_from_yaml(policy_file)

    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 500

def start_scheduler():
    """
    Initializes and starts the background scheduler for data collection.
    """
    scheduler = BackgroundScheduler()
    # Run the collection job every 30 seconds
    scheduler.add_job(collect_all_data, 'interval', seconds=30, id='data_collector_job')
    scheduler.start()
    print("Background scheduler started. Data will be collected every 30 seconds.")

if __name__ == '__main__':
    # Run the collection once at startup
    collect_all_data()
    # Start the background collection scheduler
    start_scheduler()
    # Start the Flask web server
    app.run(host='0.0.0.0', port=config.FLASK_PORT, debug=config.DEBUG)
