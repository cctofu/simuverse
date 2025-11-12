import os
import sys
import json
import re
import hashlib
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
        persona_summary = persona.get("summary", "")

        # Build context string
        context_parts = []
        for key, value in key_values.items():
            if isinstance(value, str):
                context_parts.append(f"{key}: {value}")
            elif isinstance(value, (list, dict)):
                context_parts.append(f"{key}: {value}")
        context = "\n".join(context_parts)
        if persona_summary:
            context = persona_summary + "\n" + context

        # Create system prompt telling the model to roleplay as this persona
        system_prompt = f"""
You simulate a real consumer and must output strictly valid text that matches the schema.
Do not invent brands, prices, or statistics unless they appear in <FACTS>. 
Keep the writing concrete, first person, and 2–3 sentences.
<PROFILE>
{context}
</PROFILE>
Text: Write 2-3 sentences in first person that reflect the decision and mention exactly one everyday constraint that fits the profile 
(money, time, space, location, family). No brand/statistic unless in <FACTS>. Be specific; avoid hedging.
"""
        self.conversation_history = [{"role": "system", "content": system_prompt}]

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #
    def _compute_jitter(self, question: str) -> int:
        seed = int(hashlib.sha256(f"{self.pid}|{question}".encode()).hexdigest(), 16)
        return (seed % 5) - 2

    def _is_likelihood_question(self, question: str) -> bool:
        pattern = re.compile(
            r"\b(likely|likelihood|probab|chance|odds|1-10|1 to 10|would you|will you|consider)\b",
            re.I,
        )
        return bool(pattern.search(question))

    # ------------------------------------------------------------------ #
    # Core chat methods
    # ------------------------------------------------------------------ #
    def ask(self, question: str) -> str:
        self.conversation_history.append({"role": "user", "content": question})
        response = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=self.conversation_history
        )
        assistant_message = response.choices[0].message.content.strip()
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def ask_decision(self, question: str, facts: dict = None) -> str:
        facts = facts or {}
        jitter = self._compute_jitter(question)
        facts_json = json.dumps(facts, ensure_ascii=False)

        system = (
            "You simulate a real consumer and must output strictly valid JSON that matches the schema. "
            "Do not invent brands, prices, or statistics unless they appear in <FACTS>. "
            "Keep the writing concrete, first person, and 2–3 sentences."
        )

        user = f"""
<PROFILE> {self.persona.get('summary', '')} </PROFILE>
<QUESTION> {question} </QUESTION>
<FACTS> {facts_json} </FACTS>
Decision steps (follow exactly):
1) Likelihood → score:
   - 1 = very unlikely, 10 = very likely.
2) Feature adjustments:
   +2 if sender is a favorite category/brand explicitly in <FACTS>.
   +2 if 'deal_threshold_pct' in <FACTS> is met by the offer in the question.
   +1 if budget is tight but persona hunts promos.
   -2 if inbox volume ≥100/day, unsubscribe spree, or privacy-paranoid.
   -1 if time pressure is high or promo fatigue high.
3) Add deterministic jitter J = {jitter}.
4) Clamp S to 1..10.
5) Text: Write 2–3 sentences in first person mentioning exactly one everyday constraint
   (money, time, space, location, family). Choose one micro-scenario that fits:
   [Inbox-zero purge] [Deal-hunter watching % threshold] [Brand loyalist]
   [Privacy-first] [Time-crunched skimmer].
Output (strict JSON only):
{{"text": "...", "score": S (integer 1..10), "assumption": ""}}
"""

        response = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content.strip()

    def ask_auto(self, question: str, facts: dict = None) -> str:
        """Auto-detect whether to return plain text or JSON score."""
        if self._is_likelihood_question(question):
            return self.ask_decision(question, facts)
        else:
            return self.ask(question)

    # ------------------------------------------------------------------ #
    # History management
    # ------------------------------------------------------------------ #
    def get_history(self) -> List[dict]:
        return self.conversation_history[1:]

    def clear_history(self):
        self.conversation_history = self.conversation_history[:1]


# ---------------------------------------------------------------------- #
# Helper function for one-off calls
# ---------------------------------------------------------------------- #
def ask_persona(pid: str, question: str, facts: dict = None) -> str:
    chat = PersonaChat(pid)
    return chat.ask_auto(question, facts)


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
