import os

from celery import Celery
import subprocess
import uuid
from pathlib import Path
import sys
import csv
import json
from app.utils import calculate_start_date
import xml.etree.ElementTree as ET
import shutil
import stat

# === Configurazione di Celery con Redis come broker e backend ===
app = Celery("tasks",
             broker="redis://redis:6379/0",
             backend="redis://redis:6379/0") 

# === Mapping pattern name abbreviato ➜ nome completo ===
PATTERN_DESCRIPTIONS = {
    "IC": "Informal Community (IC)",
    "CoP": "Community of Practice (CoP)",
    "FN": "Formal Network (FN)",
    "SN": "Social Network (SN)",
    "IN": "Informal Network (IN)",
    "NoP": "Network of Practice (NoP)",
    "FG": "Formal Group (FG)",
    "PT": "Project Team (PT)",
}

# === Mapping pattern ➜ descrizione testuale completa ===
PATTERN_DETAILS = {
    "IC": "Usually sets of people part of an organization, with a common interest, often closely dependent on their practice. Informal interactions, usually across unbound distances.",
    "CoP": "Groups of people sharing a concern, a set of problems, or a passion about a topic, who deepen their knowledge and expertise in this area by interacting frequently in the same geolocation.",
    "FN": "Members are rigorously selected and prescribed by management (often in the form of FG), directed according to corporate strategy and mission.",
    "SN": "SNs can be seen as a supertype for all OSSs. To identify an SN, it is sufficient to split the structure of organizational patterns into macrostructure and microstructure.",
    "IN": "Looser networks of ties between individuals that happen to come in contact in the same context. Their driving force is the strength of the ties between members.",
    "NoP": "A networked system of communication and collaboration connecting CoPs. Anyone can join. They span geographical and time distances alike.",
    "FG": "People grouped by corporations to act on (or by means of) them. Each group has an organizational goal, called mission. Compared to FN, no reliance on networking technologies, local in nature.",
    "PT": "People with complementary skills who work together to achieve a common purpose for which they are accountable. Enforced by their organization and follow specific strategies or organizational guidelines.",
}

# === Errori noti che TOAD può restituire e loro messaggio personalizzato ===
TOAD_KNOWN_ERRORS = {
    "There must be at least 100 commits": "Invalid Repository: There must be at least 100 commits!",
    "There must be at least 2 members": "Invalid Repository: Not enough members (min. 2)!",
    "There must be at least 1 milestone": "Invalid Repository: No milestones found (min. 1)!",
    "Geographical information is not enough": "Invalid Repository: Insufficient geographical data!",
    "Invalid repository": "Invalid Repository: General validation failed!"
}


# === Utility ===

# Crea la cartella csv/job_id con i file input.csv e toad_stdin.txt
def prepare_job_directory(job_id: str, author: str, repository: str, end_date: str) -> Path:
    job_dir = Path("csv") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # input.csv contiene i parametri per TOAD
    input_csv = job_dir / "input.csv"
    with open(input_csv, "w") as f:
        f.write(f"{author},{repository},{end_date}\n")

    # Simula input da tastiera per TOAD
    stdin_file = job_dir / "toad_stdin.txt"
    with open(stdin_file, "w") as f:
        f.write(f"{input_csv}\n{job_dir}\noutput\n")

    return job_dir

# Cerca nei log di stdout/stderr un errore noto di TOAD
def detect_toad_failure(output: str) -> str | None:
    for raw, friendly in TOAD_KNOWN_ERRORS.items():
        if raw.lower() in output.lower():
            return friendly
    return None

# Handler per rimuovere file protetti da sola lettura (necessario su Windows)
def force_remove_readonly(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    try:
        func(path)
    except Exception:
        pass

# Cancella cartelle generate dall’analisi
def clean_up(job_id: str, author: str, repository: str):
    paths_to_remove = [
        Path("csv") / job_id,
        Path("data") / author / repository,
        Path("graphs") / author / repository,
        Path("repositories") / f"{author}.{repository}"
    ]
    for path in paths_to_remove:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, onerror=force_remove_readonly)
            else:
                path.unlink(missing_ok=True)

# Legge output.csv per ottenere i pattern rilevati
def read_patterns(output_csv: Path) -> list:
    if not output_csv.exists():
        return []
    try:
        with open(output_csv, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                return []
            raw = rows[0]
            return [{
                "name": PATTERN_DESCRIPTIONS[k],
                "description": PATTERN_DETAILS.get(k, ""),
                "detected": raw[k].lower() == "true"
            } for k in PATTERN_DESCRIPTIONS if k in raw]
    except Exception:
        return []

# Legge metrics.json prodotto da TOAD
def read_metrics(metrics_path: Path) -> dict:
    if not metrics_path.exists():
        return {"error": "metrics.json non trovato"}
    try:
        with open(metrics_path, "r") as f:
            raw_metrics = json.load(f)

        # Mappa delle descrizioni per ogni metrica
        descriptions = {
            "dispersion": {
                "geo_distance_variance": "Variance in the geographic locations of contributors, indicating global distribution.",
                "avg_geo_distance": "Average geographic distance between contributors, in kilometers.",
                "cultural_distance_variance": "Variance in cultural values among contributors based on national culture metrics."
            },
            "engagement": {
                "m_comment_per_pr": "Mean number of comments per pull request.",
                "mm_comment_dist": "Median monthly number of comments per member.",
                "m_watchers": "Mean number of watchers, indicating general interest in the repository.",
                "m_stargazers": "Mean number of stargazers, showing popularity or appreciation.",
                "m_active": "Number of active members (committed in last 30 days).",
                "mm_commit_dist": "Median number of commits per member per month.",
                "mm_filecollab_dist": "Median number of collaborators per file per month."
            },
            "formality": {
                "m_membership_type": "Average member role score (e.g., contributor = 1, collaborator = 2).",
                "milestones": "Total number of milestones set in the project.",
                "lifetime": "Project age in days from first to last commit."
            },
            "longevity": {
                "longevity": "Average number of days active contributors have been part of the project."
            },
            "structure": {
                "repo_connections": "Indicates if contributors work together on the same repositories.",
                "follow_connections": "Indicates if contributors follow each other on GitHub.",
                "pr_connections": "Indicates if contributors interact through pull request comments."
            }
        }

        def wrap_metrics(section: str, metrics_dict: dict) -> dict:
            wrapped = {}
            for k, v in metrics_dict.items():
                wrapped[k] = {
                    "value": v,
                    "description": descriptions.get(section, {}).get(k, "")
                }
            return wrapped

        return {
            "dispersion": wrap_metrics("dispersion", raw_metrics.get("dispersion", {})),
            "engagement": wrap_metrics("engagement", raw_metrics.get("engagement", {})),
            "formality": wrap_metrics("formality", raw_metrics.get("formality", {})),
            "longevity": wrap_metrics("longevity", {"longevity": raw_metrics.get("longevity")}),
            "structure": wrap_metrics("structure", raw_metrics.get("structure", {}))
        }

    except Exception as e:
        return {"error": f"Errore lettura metrics.json: {str(e)}"}

# Legge e unisce tutti i file GEXF di TOAD in una singola struttura
def read_all_graphs(author: str, repository: str) -> dict:
    graph_dir = Path("graphs") / author / repository
    if not graph_dir.exists():
        return {"error": "Cartella graph non trovata"}

    all_nodes = set()
    all_edges = []
    ns = {'g': 'http://www.gexf.net/1.2draft'}

    for gexf_file in sorted(graph_dir.glob(f"{author}-{repository}_graph*.gexf")):
        try:
            tree = ET.parse(gexf_file)
            root = tree.getroot()

            # Estrai nodi
            nodes = [node.attrib['id'] for node in root.findall(".//g:node", ns)]
            all_nodes.update(nodes)

            # Estrai archi
            edges = [{
                "source": e.attrib['source'],
                "target": e.attrib['target'],
                "weight": float(e.attrib.get('weight', 1))
            } for e in root.findall(".//g:edge", ns)]
            all_edges.extend(edges)

        except Exception as e:
            return {"error": f"Errore durante la lettura di {gexf_file.name}: {str(e)}"}

    return {
        "nodes": list(all_nodes),
        "edges": all_edges
    }

# === TASK Celery ===
@app.task(bind=True, name="app.tasks.run_analysis")
def run_analysis(self, author: str, repository: str, end_date: str):
    job_id = str(uuid.uuid4())
    start_date = calculate_start_date(end_date)

    # Aggiorna stato intermedio per monitoraggio via API
    self.update_state(state="STARTED", meta={
        "job_id": job_id,
        "author": author,
        "repository": repository,
        "start_date": start_date,
        "end_date": end_date
    })

    job_dir = prepare_job_directory(job_id, author, repository, end_date)
    stdin_path = job_dir / "toad_stdin.txt"

    script_path = os.path.join(os.path.dirname(__file__), "..", "pattern_detection.py")
    script_path = os.path.abspath(script_path)

    try:
        # Avvia TOAD come subprocess simulando input da tastiera
        result = subprocess.run(
            [sys.executable, script_path],
            stdin=open(stdin_path),
            capture_output=True,
            text=True,
            timeout=1200  # timeout di sicurezza: 20 minuti
        )

        combined_output = result.stdout + "\n" + result.stderr
        detected_error = detect_toad_failure(combined_output)
        print(combined_output)

        # Analisi fallita
        if detected_error:
            clean_up(job_id, author, repository)
            return {
                "job_id": job_id,
                "status": "FAILED",
                "author": author,
                "repository": repository,
                "start_date": start_date,
                "end_date": end_date,
                "error": detected_error,
            }

        # Analisi completata: leggi tutti i risultati
        output_csv = job_dir / "output.csv"
        metrics_path = Path("data") / author / repository / "metrics.json"

        results = {
            "patterns": read_patterns(output_csv),
            "metrics": read_metrics(metrics_path),
            "graph": read_all_graphs(author, repository)
        }

        if not results["patterns"] or "error" in results["metrics"] or not results["metrics"] or "error" in results["graph"] or not results["graph"]:
            clean_up(job_id, author, repository)
            return {
                "job_id": job_id,
                "status": "FAILED",
                "author": author,
                "repository": repository,
                "start_date": start_date,
                "end_date": end_date,
                "error": "An Error Occurred during the analysis... Please try again later!"
            }

        final_result = {
            "job_id": job_id,
            "status": "SUCCESS",
            "author": author,
            "repository": repository,
            "start_date": start_date,
            "end_date": end_date,
            "results": results
        }

        # Salva una copia dei risultati su disco
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        with open(logs_dir / f"{job_id}.json", "w") as f:
            json.dump(final_result, f, indent=2)

        clean_up(job_id, author, repository)
        return final_result

    except subprocess.TimeoutExpired:
        clean_up(job_id, author, repository)
        return {
            "job_id": job_id,
            "status": "FAILED",
            "author": author,
            "repository": repository,
            "start_date": start_date,
            "end_date": end_date,
            "error": "TOAD execution timeout!"
        }