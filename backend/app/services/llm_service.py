import json
import re
from typing import Any, Dict, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings

_llm_model = None

def get_llm_model(streaming: bool = False):
    """Initialize the LLM model based on provider settings."""
    global _llm_model
    # Do not cache streaming models as streaming might be dynamic
    if _llm_model is not None and not streaming:
        return _llm_model

    if settings.LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL_NAME,
            temperature=0.2,
            streaming=streaming
        )
    else:
        from langchain_groq import ChatGroq
        model = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL_NAME,
            temperature=0.2,
            streaming=streaming
        )
        
    if not streaming:
        _llm_model = model
    return model


class LLMService:
    @classmethod
    async def summarize_text(cls, text_content: str) -> Dict[str, Any]:
        """Summarize text content (Abstract, Key Points, Simple explanation) in JSON format."""
        llm = get_llm_model()
        
        system_prompt = (
            "You are an expert research analyst. Your task is to analyze the research paper text provided "
            "and generate a structured summary. You must return your response as a valid JSON object. "
            "The JSON must have the following keys:\n"
            "1. 'summary': A detailed 3-4 sentence overview of the paper's core contributions, methods, and findings.\n"
            "2. 'abstract': A brief 1-2 sentence description of the research goal/problem.\n"
            "3. 'key_points': A JSON list of 4-6 strings, each representing a crucial takeaway, metric, or finding.\n"
            "4. 'explain_simple': A simple, jargon-free 2-sentence explanation of the paper's core concept, "
            "written as if explaining to a 10-year-old child.\n\n"
            "Format the response ONLY as a raw JSON string. Do not include markdown code fences (like ```json), "
            "no leading or trailing text, just the raw JSON object."
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Here is the text to summarize:\n\n{text_content}")
        ]
        
        try:
            # We run in a thread pool since LangChain calls are blocking by default in some setups
            import asyncio
            response = await asyncio.to_thread(llm.invoke, messages)
            
            # Parse the response text as JSON
            cleaned_content = response.content.strip()
            # Clean up markdown code fences if LLM included them despite instructions
            if cleaned_content.startswith("```"):
                cleaned_content = re.sub(r"^```(?:json)?\n", "", cleaned_content)
                cleaned_content = re.sub(r"\n```$", "", cleaned_content)
            
            summary_data = json.loads(cleaned_content)
            
            # Validate structure
            required_keys = ["summary", "abstract", "key_points", "explain_simple"]
            for key in required_keys:
                if key not in summary_data:
                    if key == "key_points":
                        summary_data[key] = []
                    else:
                        summary_data[key] = "Not available."
            return summary_data
            
        except Exception as e:
            # Fallback if AI generation or parsing fails
            return {
                "summary": "Failed to generate AI summary. The document was indexed successfully.",
                "abstract": "Failed to generate abstract.",
                "key_points": [f"Error occurred during summary generation: {str(e)}"],
                "explain_simple": "Failed to generate simple explanation."
            }
