from flask import Flask, request, jsonify
import subprocess
import threading
import os
import uuid
import csv
from urllib.parse import urlparse

app = Flask(__name__)
UPLOAD_FOLDER = "/tmp/toad_inputs"
OUTPUT_FOLDER = "/tmp/toad_outputs"
RESULTS = {}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def parse_repo_url(repo_url):
    path = urlparse(repo_url).path.strip("/")
    parts = path.split("/")
    if len(parts) != 2:
        raise ValueError("Invalid GitHub URL")
    return parts[0], parts[1]

def run_toad_task(task_id, input_csv_path):
    try:
        subprocess.run(
            ["python3.8", "pattern_detection.py"],
            input=f"{input_csv_path}\n{OUTPUT_FOLDER}\ntask_{task_id}\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        RESULTS[task_id] = {
            "status": "completed",
            "output_file": os.path.join(OUTPUT_FOLDER, f"task_{task_id}.csv")
        }
    except subprocess.CalledProcessError as e:
        RESULTS[task_id] = {
            "status": "error",
            "error": e.stderr
        }

@app.route('/run_toad', methods=['POST'])
def run_toad():
    repo_url = request.json.get("repo_url")
    date = request.json.get("date")

    if not repo_url or not date:
        return jsonify({"error": "repo_url and date are required"}), 400

    try:
        owner, repo = parse_repo_url(repo_url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    task_id = str(uuid.uuid4())
    input_csv_path = os.path.join(UPLOAD_FOLDER, f"input_{task_id}.csv")
    with open(input_csv_path, "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([owner, repo, date])

    RESULTS[task_id] = {"status": "running"}

    thread = threading.Thread(target=run_toad_task, args=(task_id, input_csv_path))
    thread.start()

    return jsonify({"task_id": task_id})

@app.route('/get_result/<task_id>', methods=['GET'])
def get_result(task_id):
    result = RESULTS.get(task_id)
    if not result:
        return jsonify({"error": "Task ID not found"}), 404
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
