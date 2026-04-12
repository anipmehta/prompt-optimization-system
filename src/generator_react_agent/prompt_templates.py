"""Static prompt template and example retrieval tools."""


def retrieve_templates(query: str) -> str:
    """Retrieve relevant prompt templates based on task characteristics."""
    return (
        "Common prompt templates for this type of task:\n"
        "- Direct instruction: 'You are a [role]. [Task]. [Format].'\n"
        "- Chain-of-thought: 'Think step by step about [task].'\n"
        "- Few-shot: 'Here are examples: [examples]. Now do [task].'\n"
        "- Role-play: 'Act as an expert [domain] professional. [Task].'"
    )


def search_examples(task_type: str) -> str:
    """Find relevant input-output examples for a given task type."""
    return (
        "No specific examples found for this task type. "
        "Consider including 2-3 concrete input/output pairs "
        "that demonstrate the expected behavior."
    )
