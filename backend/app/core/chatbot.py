"""The Agriva assistant: the agriculture-only system prompt plus the LLM call.

Shared by the /api/chatbot endpoint and the agents. The agents used to reach it
with an HTTP request to their own server, which added a hop, a separate
90-second timeout, and held two worker threads for every call. They now call
`ask_agriva` in-process.
"""

from typing import Optional, Tuple

from app.core.llm_client import chat_completion

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi (Devanagari)",
    "pa": "Punjabi (Gurmukhi)",
    "mr": "Marathi (Devanagari)",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "gu": "Gujarati",
    "bn": "Bengali",
    "ml": "Malayalam",
    "or": "Odia",
}


def agriva_system_prompt(language: str) -> str:
    language_name = LANGUAGE_NAMES.get(language, "English")
    return f"""
You are Agriva, an AI assistant specialized ONLY in agriculture.
The user's selected language is {language_name} (code: {language}).
Write the entire answer in that language. This includes the summary, headings,
category labels, table headings, bullet labels, and closing text. Do not switch
to English in the middle of the answer. Keep unavoidable crop names, product
names, and standard abbreviations only when they are proper names or have no
clear translation.

Your domain includes:
- Crop diseases
- Plant health
- Fertilizers
- Irrigation
- Weather for farming
- Soil analysis
- Livestock
- Government agricultural schemes
- Mandi prices
- Precision agriculture

If a user asks anything outside agriculture, farming, crops, livestock,
horticulture, or rural farming practices, do not answer the question.

Instead reply politely:

"I'm Agriva, an agriculture assistant. I can only help with farming-related
questions such as crop diseases, fertilizers, irrigation, weather, soil health,
and government schemes."

Never provide programming code, mathematics, general knowledge, essays,
jokes, recipes, or other unrelated content.
"""


def ask_agriva(query: str, system_prompt: Optional[str] = None,
               language: str = "en") -> Tuple[str, str]:
    """Answer as Agriva. Returns (answer, "provider:model"), or ("", "") on failure.

    A caller's system prompt goes ahead of the agriculture-only guardrail, the
    way /api/chatbot has always combined them.
    """
    default_system_prompt = agriva_system_prompt(language)
    messages = [
        {
            "role": "system",
            "content": f"{system_prompt}\n\n{default_system_prompt}" if system_prompt else default_system_prompt,
        },
        {"role": "user", "content": query},
    ]
    answer, model = chat_completion(messages, temperature=0.2, top_p=0.8, max_tokens=1000)
    print(f"[Chatbot] User Query: {query}\n[Chatbot] Response: {answer}")
    return answer, model
