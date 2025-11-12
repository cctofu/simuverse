import os
import sys
from typing import List
from openai import OpenAI

# Import configuration and utilities
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY, DATABASE_PATH, CHAT_MODEL
from utils import load_personas


class PersonaChat:
    def __init__(self, pid: str):
        # Load all personas from database
        personas = load_personas(DATABASE_PATH)

        # Find the persona with matching ID
        persona = None
        for p in personas:
            if p.get("id") == pid:
                persona = p
                break

        if persona is None:
            raise ValueError(f"Persona with ID '{pid}' not found in database")

        self.pid = pid
        self.persona = persona
        self.client = OpenAI(api_key=OPENAI_API_KEY)

        # Extract key_values as context
        key_values = persona.get("key_values", {})

        # Build context string from key_values
        context_parts = []
        for key, value in key_values.items():
            if isinstance(value, str):
                context_parts.append(f"{key}: {value}")
            elif isinstance(value, (list, dict)):
                context_parts.append(f"{key}: {value}")

        context = "\n".join(context_parts)

        # Create system prompt telling the model to roleplay as this persona
        system_prompt = (
            "You are roleplaying as a specific person with the following characteristics and attributes. "
            "Answer the user's questions from this person's perspective, staying in character and using "
            "their values, beliefs, lifestyle, and personality traits to inform your responses. "
            "Be authentic and consistent with the persona described below.\n\n"
            f"Your persona:\n{context}"
        )

        # Initialize conversation history with system prompt
        self.conversation_history = [
            {"role": "system", "content": system_prompt}
        ]

    def ask(self, question: str) -> str:
        """
        Ask the persona a question and get a response. Maintains conversation context.

        Args:
            question: The question to ask the persona

        Returns:
            The persona's response to the question
        """
        # Add user question to conversation history
        self.conversation_history.append({"role": "user", "content": question})

        # Get response from the model
        response = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=self.conversation_history
        )

        assistant_message = response.choices[0].message.content.strip()

        # Add assistant response to conversation history
        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        return assistant_message

    def get_history(self) -> List[dict]:
        """
        Get the full conversation history.

        Returns:
            List of message dictionaries with role and content
        """
        # Return everything except the system prompt
        return self.conversation_history[1:]

    def clear_history(self):
        """
        Clear the conversation history while keeping the system prompt.
        """
        # Keep only the system prompt
        self.conversation_history = self.conversation_history[:1]


def ask_persona(pid: str, question: str) -> str:
    """
    Single-turn function: Ask a persona a question without maintaining conversation history.
    For multi-turn conversations, use the PersonaChat class instead.

    Args:
        pid: The persona ID to query
        question: The question to ask the persona

    Returns:
        The persona's response to the question

    Raises:
        ValueError: If the persona ID is not found in the database
    """
    chat = PersonaChat(pid)
    return chat.ask(question)


# --------------------------------------------------
# LOCAL TEST
# --------------------------------------------------
if __name__ == "__main__":
    test_pid = "user_000009"  # Replace with an actual persona ID from your database

    print("=" * 60)
    print("Example 1: Single-turn conversation (no context)")
    print("=" * 60)
    try:
        answer = ask_persona(test_pid, "What do you think about buying luxury items?")
        print(f"\nPersona {test_pid}'s Answer:\n{answer}\n")
    except ValueError as e:
        print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Example 2: Multi-turn conversation (with context)")
    print("=" * 60)
    try:
        # Initialize a conversation session
        chat = PersonaChat(test_pid)

        # First question
        print("\nYou: What do you think about buying luxury items?")
        response1 = chat.ask("What do you think about buying luxury items?")
        print(f"Persona: {response1}")

        # Follow-up question (model has context from previous exchange)
        print("\nYou: Why do you feel that way?")
        response2 = chat.ask("Why do you feel that way?")
        print(f"Persona: {response2}")

        # Another follow-up
        print("\nYou: Can you give me a specific example?")
        response3 = chat.ask("Can you give me a specific example?")
        print(f"Persona: {response3}")

        # Show conversation history
        print("\n" + "-" * 60)
        print("Full conversation history:")
        print("-" * 60)
        for i, msg in enumerate(chat.get_history(), 1):
            role = msg["role"].capitalize()
            content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            print(f"{i}. {role}: {content}")

    except ValueError as e:
        print(f"Error: {e}")
