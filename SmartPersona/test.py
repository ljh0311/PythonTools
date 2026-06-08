from ollama_func import Ollama_func

ollama_func = Ollama_func()


class VersatileAgent:
    """
    VersatileAgent can perform a variety of language tasks such as summarizing,
    elaborating, explaining, and general information synthesis.
    Uses the provided ollama_func's send_prompt method to accomplish tasks.
    """

    def __init__(self, ollama_func):
        self.ollama_func = ollama_func

    def perform_task(self, text, task: str):
        """
        Performs the specified task on the provided text.

        task: a string describing the instruction/task for the AI (e.g. "summarize", "elaborate", "explain in detail", etc.)
        """
        prompt = (
            f"As a versatile assistant, please {task} the following information:\n\n"
            f"{text}"
        )
        return self.ollama_func.send_prompt(prompt)

    def summarize(self, text):
        # Specialized method for bullet point summary
        return self.perform_task(text, "summarize in 3-5 concise bullet points")

    def elaborate(self, text):
        # Specialized method for an in-depth summary
        return self.perform_task(
            text,
            "provide a thorough and detailed explanation, elaborating on key points and insights",
        )


class AgentB:
    """
    AgentB handles tasks related to generating detailed and elaborated summaries of provided information.

    This agent takes a block of text and returns an in-depth summary, elaborating on key points,
    insights, and implications. The summary is more comprehensive and explanatory compared to a simple bullet summary.
    """

    def __init__(self, ollama_func):
        self.ollama_func = ollama_func

    def elaborate(self, text):
        prompt = (
            "Provide a thorough and detailed summary of the following information. "
            "Go beyond a simple summary: explain the main points clearly, add context or background information where relevant, "
            "highlight any implications or actionable insights, and elaborate on any subtleties or important nuances. "
            "Your response should read like a comprehensive explanatory write-up, not just bullet points.\n\n"
            f"{text}"
        )
        return self.ollama_func.send_prompt(prompt)


# Create instances of the agents
agent_a = VersatileAgent(ollama_func)
agent_b = AgentB(ollama_func)


user_prompt = input("Enter your prompt: ")
response = ollama_func.send_prompt(user_prompt)

# Step 1 : Think what does the user want to do?
think_prompt = (
    "Break down the user's request into the 5Ws and 1H: Who, What, Where, When, Why, and How. "
    "For the following prompt, list each category with your best assessment based on the text.\n"
    "Respond with a JSON object with the following format: "
    '{"Who": "...", "What": "...", "Where": "...", "When": "...", "Why": "...", "How": "..."}.\n'
    f"Prompt: {user_prompt}"
)
thinking = ollama_func.send_prompt(think_prompt)

import time
import random

# Step 2: Suggest the best action based on reasoning, with improved mimicry of a human collaborator
def pretty_print_thinking(thinking):
    print("\n🤔 Here's my breakdown of your prompt:")
    time.sleep(random.uniform(0.4, 1))
    print(thinking)
    print()

suggest_prompt = (
    "You've analyzed the user's prompt using the 5Ws and 1H. "
    "Given this reflection, what would you (as a helpful assistant) do next for the user? "
    "Choose just the action name: 'perform_task' (for a direct answer) or 'elaborate' (for detailed, contextual writing).\n\n"
    f"Analysis: {thinking}\n"
    "Reply ONLY with one of those choices, and nothing more."
)
pretty_print_thinking(thinking)

time.sleep(random.uniform(0.3, 0.8))
print("Hmm...deciding what to do next...\n")
time.sleep(random.uniform(0.7, 1.1))

suggest_action = ollama_func.send_prompt(suggest_prompt)
action = str(suggest_action).strip().lower()
print(f"🤖 My suggestion: {action}\n")

# For now, always use VersatileAgent, but act with more conversational style
agent = agent_a

time.sleep(random.uniform(0.5, 1.2))
print("Alright, let me work on that!\n")
time.sleep(random.uniform(0.6, 1.3))

if action == "perform_task":
    print("→ Using perform_task for a direct response.\n")
    perform_action = agent.perform_task(user_prompt, action)
elif action == "elaborate":
    print("→ Crafting a more detailed and explanatory answer (elaborate).\n")
    perform_action = agent.elaborate(user_prompt)
else:
    print("→ (Defaulting to summary mode, just in case...)\n")
    perform_action = agent.perform_task(user_prompt, "provide a helpful response")

time.sleep(random.uniform(0.8, 1.3))
print("="*32)
print("Agent Response:\n")
print(perform_action)
print("="*32)
