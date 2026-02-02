import json

from IPython.core.interactiveshell import InteractiveShell

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
import tornado

from .v_db.peer_agent import PeerAgent
from .course_completed import mark_course_if_completed
from .v_db.vector_db_manager import get_db_manager_instance
from .prompt import get_peer_prompt, get_tutor_prompt, format_chat_history

class AskAgentHandler(APIHandler):
    """
    The handler that listens for API calls from the React front-end.
    """
    
    def __init__(self, application, request, **kwargs):
        resp = super().__init__(application, request, **kwargs)
        self.peer_agent = PeerAgent(
            db_path='data/vector_db'
        )
        self.db_manager = get_db_manager_instance()
        return resp

    @tornado.web.authenticated
    def post(self):
        """
        Handles POST requests to /q-toolkit/ask
        """
        try:
            # 1. Get the incoming request body (the student's question)
            data = self.get_json_body()
            query = data.get("query")
            agent_type = data.get("agent_type", "peer") # e.g., 'peer' or 'tutor'
            completed_lo_ids = data.get("student_completed_lo_ids", None)
            current_lo_id = data.get("current_lo_id", None)
            history = data.get("history", [])

            if not completed_lo_ids:
                completed_lo_ids = self.db_manager.get_completed_lo_ids()

            if current_lo_id and current_lo_id not in completed_lo_ids:
                completed_lo_ids.append(current_lo_id)

            if agent_type not in ['peer', 'tutor']:
                raise ValueError(f"Unknown agent_type: {agent_type}")

            if not query:
                raise ValueError("No query provided")

            print(f"Received query for {agent_type}: {query}")
            
            if agent_type == 'peer':
                result = self.peer_agent.answer_question(
                    query, 
                    get_peer_prompt(), 
                    completed_lo_ids=completed_lo_ids, 
                    chat_history=history
                )
                answer = result["answer"]
                escalate = result.get("escalate", False)
            else:
                # Tutor: skip grading, use all content
                result = self.peer_agent.answer_question(
                    query, 
                    get_tutor_prompt(query, history), 
                    completed_lo_ids=None,  # Tutor has access to all content
                    chat_history=history,
                    skip_grading=True
                )
                answer = result["answer"]
                escalate = False  # Tutor never escalates

            # 3. Send the response back to the front-end
            self.finish(json.dumps({
                "data": answer,
                "escalate": escalate
            }))

        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({"error": str(e)}))

class CourseTrackerHandler(APIHandler):
    """
    Handler to track course progress.
    """
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db_manager = get_db_manager_instance()

    @tornado.web.authenticated
    def post(self):
        try:
            data = self.get_json_body()
            lo_id = data.get("lo_id")
            mark_course_if_completed(lo_id)

            self.finish(json.dumps({"status": "success"}))
        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({"error": str(e)}))

    @tornado.web.authenticated
    def get(self):
        try:
            data = self.get_json_body()
            if data:
                lo_id = data.get("lo_id")
                lesson_number = data.get("lesson_number")
            else:
                lo_id = None
                lesson_number = None

            return_data = {
                'lesson_info': None,
                'lo_info': None,
                'max_course_progress': None,
                'tracking_data': None
            }
            
            if lesson_number is not None:
                completed = self.db_manager.is_lesson_completed(lesson_number)
                return_data['lesson_info'] = {
                    'lesson_number': lesson_number,
                    'completed': completed
                }
            if lo_id:
                completed = self.db_manager.is_lo_completed(lo_id)
                return_data['lo_info'] = {
                    'lo_id': lo_id,
                    'completed': completed
                }
            max_progress = self.db_manager.get_max_lesson_completed()
            return_data['max_course_progress'] = max_progress
            tracking_data = self.db_manager.get_full_tracking_data()
            return_data['tracking_data'] = tracking_data
            return_data['manifest'] = self.db_manager.get_course_manifest_copy()

            self.finish(json.dumps(return_data))

        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({"error": str(e)}))

class VectorDatabaseHandler(APIHandler):
    """
    Handler to manage vector database operations.
    """
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.db_manager = get_db_manager_instance()

    @tornado.web.authenticated
    def post(self):
        try:
            data = self.get_json_body()
            operation = data.get("operation")

            if operation == "clear":
                self.db_manager.clear_all()
                self.finish(json.dumps({"status": "vector database cleared"}))
            elif operation == "reindex":
                from .v_db.index_notebooks import index_course_content
                from .v_db.graph_rag import GraphRAG
                import os
                
                # Reindex FAISS
                index_course_content("./content", self.db_manager)
                self.db_manager.save()
                
                # Build GraphRAG from indexed content
                print("Building GraphRAG knowledge graph...")
                graph_path = os.path.join(self.db_manager.db_path, "knowledge_graph.pkl")
                graph_rag = GraphRAG(graph_path=graph_path)
                corpus = [
                    {"content": meta["content"], "source": str(key)} 
                    for key, meta in self.db_manager.metadata.items()
                ]
                graph_rag.build_from_corpus(corpus)
                
                self.finish(json.dumps({"status": "vector database and knowledge graph re-indexed"}))
            else:
                raise ValueError(f"Unknown operation: {operation}")

        except Exception as e:
            self.set_status(500)
            self.finish(json.dumps({"error": str(e)}))

    @tornado.web.authenticated
    def get(self):
        query = self.get_argument("query", None)
        lo_id_str = self.get_argument("lo_ids", None)

        if lo_id_str:
            completed_lo_ids = lo_id_str.split(",")
        else:
            completed_lo_ids = None

        if query:
            context_chunks = self.db_manager.filter_with_lo_ids(
                query=query, lo_ids=completed_lo_ids, num_results=2
            )
            context_str = "\n\n".join(context_chunks)

            self.set_status(200)
            self.finish(context_str)
        else:
            try:
                self.finish(json.dumps({
                    'metadata': self.db_manager.metadata
                }))
            except Exception as e:
                self.set_status(500)
                self.finish(json.dumps({"error": str(e)}))

def setup_handlers(web_app):
    host_pattern = ".*$"

    base_url = web_app.settings["base_url"]
    # The URL your front-end will call: /q-toolkit/ask
    ask_route_pattern = url_path_join(base_url, "q-toolkit", "ask")
    # The URL for course tracking: /q-toolkit/track_course
    course_tracker_pattern = url_path_join(base_url, "q-toolkit", "track_course")
    # The URL for vector DB operations: /q-toolkit/vector_db
    vector_db_pattern = url_path_join(base_url, "q-toolkit", "vector_db")

    handlers = [
        (ask_route_pattern, AskAgentHandler),
        (course_tracker_pattern, CourseTrackerHandler),
        (vector_db_pattern, VectorDatabaseHandler),
    ]
    web_app.add_handlers(host_pattern, handlers)
