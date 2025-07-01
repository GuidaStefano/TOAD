import shutil
from pathlib import Path
from app.tasks import read_all_graphs


def create_gexf_file(path: Path, nodes: list[str], edges: list[tuple[str, str, float | None]]):
    """
    Helper per creare un file GEXF di test.
    """
    from xml.etree.ElementTree import Element, SubElement, ElementTree

    root = Element("gexf", xmlns="http://www.gexf.net/1.2draft")
    graph = SubElement(root, "graph")

    nodes_elem = SubElement(graph, "nodes")
    for nid in nodes:
        SubElement(nodes_elem, "node", id=nid)

    edges_elem = SubElement(graph, "edges")
    for i, (source, target, weight) in enumerate(edges):
        attribs = {"id": str(i), "source": source, "target": target}
        if weight is not None:
            attribs["weight"] = str(weight)
        SubElement(edges_elem, "edge", **attribs)

    tree = ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def test_read_all_graphs_directory_not_found():
    """
    Verifica che venga restituito un errore se la cartella dei grafi non esiste.
    """
    result = read_all_graphs("nonexistent_author", "nonexistent_repo")
    assert result["error"] == "Cartella graph non trovata"


def test_read_all_graphs_valid_single_file():
    """
    Verifica il parsing corretto di un singolo file GEXF nella directory reale 'graphs/'.
    """
    author = "john"
    repo = "sample"
    graph_dir = Path("graphs") / author / repo
    graph_dir.mkdir(parents=True, exist_ok=True)

    gexf_path = graph_dir / f"{author}-{repo}_graph0.gexf"
    create_gexf_file(gexf_path, ["n1", "n2"], [("n1", "n2", 2.5)])

    result = read_all_graphs(author, repo)
    assert set(result["nodes"]) == {"n1", "n2"}
    assert result["edges"][0]["source"] == "n1"
    assert result["edges"][0]["target"] == "n2"
    assert result["edges"][0]["weight"] == 2.5

    shutil.rmtree(Path("graphs") / author)


def test_read_all_graphs_file_with_missing_weight():
    """
    Verifica che venga usato il peso di default = 1.0 se assente nel GEXF.
    """
    author = "john"
    repo = "noweight"
    graph_dir = Path("graphs") / author / repo
    graph_dir.mkdir(parents=True, exist_ok=True)

    gexf_path = graph_dir / f"{author}-{repo}_graph0.gexf"
    create_gexf_file(gexf_path, ["a", "b"], [("a", "b", None)])

    result = read_all_graphs(author, repo)
    assert result["edges"][0]["weight"] == 1.0

    shutil.rmtree(Path("graphs") / author)


def test_read_all_graphs_multiple_files():
    """
    Verifica che nodi ed archi vengano aggregati correttamente da più file.
    """
    author = "alice"
    repo = "multi"
    graph_dir = Path("graphs") / author / repo
    graph_dir.mkdir(parents=True, exist_ok=True)

    create_gexf_file(graph_dir / f"{author}-{repo}_graph0.gexf", ["x"], [("x", "x", 1)])
    create_gexf_file(graph_dir / f"{author}-{repo}_graph1.gexf", ["y"], [("y", "y", 2)])

    result = read_all_graphs(author, repo)
    assert set(result["nodes"]) == {"x", "y"}
    assert len(result["edges"]) == 2

    shutil.rmtree(Path("graphs") / author)


def test_read_all_graphs_parsing_error():
    """
    Verifica che un errore di parsing restituisca un messaggio di errore.
    """
    author = "fail"
    repo = "badxml"
    graph_dir = Path("graphs") / author / repo
    graph_dir.mkdir(parents=True, exist_ok=True)

    bad_file = graph_dir / f"{author}-{repo}_graph0.gexf"
    bad_file.write_text("<gexf><broken></gexf>")  # XML non valido

    result = read_all_graphs(author, repo)
    assert "error" in result
    assert f"Errore durante la lettura di {bad_file.name}" in result["error"]

    shutil.rmtree(Path("graphs") / author)


