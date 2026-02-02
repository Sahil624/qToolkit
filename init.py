import os

import argparse

from edu_agents.v_db.vector_db_manager import VectorDBManager
from edu_agents.v_db.index_notebooks import index_course_content, build_knowledge_graph

def re_index_notebooks(re_index_enabled):
    v_db_manager = VectorDBManager(path="data/vector_db")

    if re_index_enabled:
        v_db_manager.clear_all()

    index_course_content("./content", v_db_manager)

    v_db_manager.save()


    build_knowledge_graph(v_db_manager)

def run_search_test():
    v_db_manager = VectorDBManager(path="data/vector_db")
    query = "What is a quantum bit?"
    results = v_db_manager.search_with_filter(query, 1)
    for i, text in enumerate(results):
        print(f"Result {i+1} (\n{text}\n{'-'*40}")

if __name__ == "__main__":
    args = argparse.ArgumentParser(description="Initialize toolkit")
    args.add_argument("--reindex", action="store_true", help="Re-index the notebooks", default=os.getenv("REINDEX_NOTEBOOKS", "0") == "1")
    args.add_argument("--search_test", action="store_true", help="Run a search test after indexing", default=os.getenv("RUN_SEARCH_TEST", "0") == "1")
    args.add_argument('--restore', action='store_true', help='Restore notebooks from backups', default=os.getenv("RESTORE", "0") == "1")
    args.add_argument('--clean', action='store_true', help='Clean up backup files', default=os.getenv("CLEAN_BACKUPS", "0") == "1")
    parsed_args = args.parse_args()

    re_index_enabled = parsed_args.reindex
    new_setup = not os.path.exists("data/vector_db")

    if re_index_enabled or new_setup:
        print("Re-indexing notebooks...")
        if re_index_enabled and not new_setup:
            print("Warning: Re-indexing will overwrite existing vector database.")
        re_index_notebooks(re_index_enabled)
        print("Re-indexing complete.")

    if parsed_args.search_test:
        print("Running search test...")
        run_search_test()
        print("Search test complete.")