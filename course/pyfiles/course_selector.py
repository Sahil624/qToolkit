from typing import List, Dict, Set, Tuple, Callable
from collections import defaultdict, deque

def calculate_course_value(course: Dict, preference: str) -> int:
    """Assigns a 'value' to a course based on user preference."""

    kolb_phase = course.get('kolb_phase', 'N/A')

    if preference == 'balanced':
        return 1  # Original logic: just count the course

    if preference == 'experiential':
        if kolb_phase in ['CE', 'AE']:
            return 10  # High value for games/sims
        else:
            return 1   # Low value for theory/quizzes

    if preference == 'conceptual':
        if kolb_phase == 'AC':
            return 10  # High value for theory
        else:
            return 1   # Low value for others

    if preference == 'reflective':
        if kolb_phase == 'RO':
            return 10  # High value for quizzes
        else:
            return 1   # Low value for others

    return 1

def maximize_courses(courses: List[Dict], total_time: int, user_selection: List[str], known_topics: Set[str], activity_preference: str,
                     log_function: Callable[[str], None] = print) -> Tuple[List[str], int]:
    
    # Build adjacency list representation of the prerequisite graph
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    course_dict = {}
    for course in courses:
        course_id = course['lo_id']
        course_dict[course_id] = course
        log_function(f"Course {course_id}, Estimated Time {course['estimated_time_mins']}, ...")
        for prereq in course['prerequisites']:
            graph[prereq].append(course_id)
            in_degree[course_id] += 1

    # Topological sort
    queue = deque([course_id for course_id in course_dict if in_degree[course_id] == 0])
    topological_order = []
    while queue:
        course_id = queue.popleft()
        topological_order.append(course_id)
        for neighbor in graph[course_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    log_function(f"Total time required (without filtering) {sum(map(lambda x: course_dict.get(x)['estimated_time_mins'], topological_order))}")
    log_function(f"Topological order {topological_order}")
    log_function(f"Known topics {known_topics}")

    # Get all prerequisites for user-selected courses
    def get_all_prerequisites(course_id):
        prereqs = set()
        queue = deque([course_id])
        while queue:
            current = queue.popleft()
            for prereq in course_dict[current]['prerequisites']:
                if prereq not in prereqs:
                    prereqs.add(prereq)
                    queue.append(prereq)
        return prereqs

    all_relevant_courses = set(user_selection)
    for course_id in user_selection:
        all_relevant_courses.update(get_all_prerequisites(course_id))

    # Filter and sort courses based on topological order and relevance
    valid_selection = [course_id for course_id in topological_order if course_id in all_relevant_courses]

    # Dynamic programming
    dp = [[0] * (total_time + 1) for _ in range(len(valid_selection) + 1)]
    for i in range(1, len(valid_selection) + 1):
        course_id = valid_selection[i-1]
        course = course_dict[course_id]
        course_time = course['estimated_time_mins']
        # TODO: Verify this logic. Not sure about this once.
        # Basically if there is a course which is not reachable by any edge (i.e. not a pre-req for any)
        # Include it or not.
        # For now, I am only generating graph with relevant modules. But in future can generate course for all modules on startup.
        # course_value =  1  # Prioritize user-selected courses
        course_value = calculate_course_value(course, activity_preference)
        for t in range(total_time + 1):
            is_known_topic = course_id in known_topics
            # We can select a topic if
            # 1) It is not an already known topic.
            # 2) There is time to adjust it.
            # 3) It's pre reqs are processed.
            if not is_known_topic and (course_time <= t and all(prereq in set(valid_selection[:i-1]) for prereq in course['prerequisites'])):
                dp[i][t] = max(dp[i-1][t], dp[i-1][t-course_time] + course_value)
            else:
                dp[i][t] = dp[i-1][t]

    # Backtrack to find selected courses
    selected_courses = []
    t = total_time
    for i in range(len(valid_selection), 0, -1):
        # If these values are different, it means that including the i-th course improved 
        # the solution for time t, so we include this course in our selection.
        if dp[i][t] != dp[i-1][t]:
            course_id = valid_selection[i-1]
            selected_courses.append(course_id)
            t -= course_dict[course_id]['estimated_time_mins']
            log_function(f"Added course {course_id}. Remaining time: {t}")
        else:
            log_function(f"Skipped course {valid_selection[i-1]}. Not optimal for remaining time: {t}")

    selected_courses.reverse()  # Reverse to get courses in order of selection

    return selected_courses, len(selected_courses)
