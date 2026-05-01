from groq import Groq
import os
import json
from logger import log

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_text(content:str) -> str:
    log.info("stage.extract_text.started")
    return content.strip()

def classify_document(text:str) -> str:
    log.info("stage.classify_document.started")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{
            "role": "user",
            "content": (
                "Classify this documento into exactly one of these categories: " "invoice, contract, report, email, other."
                "Repl with only the category word, nothing else. \n\n"
                f"{text[:500]}"
            )
        }],
        max_tokens=10
    )
    result = response.choices[0].message.content.strip().lower()
    log.info("stage.classify_document.completed", result=result)
    return result

def summarise_document(text:str) -> str:
    log.info("stage.summarise_document.started")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{
            "role": "user",
            "content": (
                "Summarise this document in exactly 2-3 sentences."
                "Be concise and factual.\n\n"
                f"{text[:2000]}"
            )
        }],
        max_tokens=200
    )
    result = response.choices[0].message.content.strip()
    log.info("stage.summarise_document.completed")
    return result

def extract_entities(text:str) -> str:
    log.info("stage.extract_entities.started")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{
            "role": "user",
            "content": (
                "Extract key entities from this text. "
                "Return a JSON array of objects, each with 'type' and 'value' keys."
                "Types can be: person, organisation, date, amount, location. "
                "Return only valid JSON, no other text. \n\n"
                f"{text[:2000]}"
            )
        }]
    )
    result = response.choices[0].message.content.strip()
    
    try:
        json.loads(result)
    except json.JSONDecodeError:
        result = "[]"
    log.info("stage.extract_entities.completed")
    return result


def generate_insights(text:str) -> str:
    log.info("stage.generate_insights.started")
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{
            "role": "user",
            "content": (
                "List 3 key insights or action items from this document. "
                "Format as a JSON array of strings. "
                "Return only valid JSON, no other text. \n\n"
                f"{text[:2000]}"
            )
        }],
        max_tokens=300
    )
    
    result = response.choices[0].message.content.strip()

    try:
        json.loads(result)
    except json.JSONDecodeError:
        result = '["Could not extract insights"]'
    log.info("stage.generate_insights.completed")
    return result
