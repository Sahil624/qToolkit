from IPython.core.magic import register_cell_magic
from IPython import get_ipython
from .v_db.vector_db_manager import get_db_manager_instance

def mark_course_if_completed(lo_id: str):
    v_db = get_db_manager_instance()

    lesson_number = v_db.get_parent_lesson_of_lo(lo_id)
    if lesson_number is None:
        print(f"Learning Objective ID '{lo_id}' not found in database.")
        return
    is_lesson_completed = v_db.is_lesson_completed(lesson_number)

    v_db.update_course_status(lo_id, lesson_number, is_lesson_completed)

def course_completed(line, cell):
    """
    Your custom cell magic implementation.
    
    Args:
        line (str): The text on the same line as %%my_magic (for arguments).
        cell (str): The entire string content of the cell body.
    """
    
    course_id = line.strip()
    mark_course_if_completed(course_id)
    print(f"Course '{course_id}' marked as completed.")