"""
Interface to Ollama LLM for various tasks.
"""

from typing import AsyncGenerator, AsyncIterator
import ollama
from loguru import logger
from ollama import ChatResponse
import asyncio


async def prompt_ollama(prompt: str, host: str, model: str, system_prompt: str | None = None) -> AsyncGenerator[str, None]:
    ollama.pull(model)

    client = ollama.AsyncClient(host=host)

    messages = list()
    if system_prompt is not None:
        messages = [{'role': 'system', 'content': system_prompt}]

    messages.append({'role': 'user', 'content': prompt})

    stream: AsyncIterator[ChatResponse] = await client.chat(
        model=model,
        messages=messages,
        stream=True
    )

    async for response in stream:
        message = response["message"]
        content = message["content"]
        yield content


async def compare_text_segments(original_chunk: str, source_chunk: str, model: str, ollama_host: str) -> float:
    """
    Compare two text segments using LLM.

    Args:
        original_chunk: Original chunk content
        source_chunk: Source chunk content
        model: Name of the LLM model
        ollama_host: URL of the Ollama API

    Returns:
        Concise description of similarities and differences
    """
    prompt = (
        f"```text\n"
        f"{original_chunk}\n"
        f"```\n"
        f"\n"
        f"```source\n"
        f"{source_chunk}\n"
        f"```\n"
        f"\n"
        f"Compare the above text against the source and concisely list clear contradictions. Consider only statements "
        f"about the same things, objects, or subjects. Ignore all other statements. Respond in the language of the "
        f"text with one single sentence only: no disclaimer, introduction, or conclusion.\n"
        "\n"
    )

    system_prompt = "You are an expert at spotting conflicting statements."

    response_str = ""
    async for response in prompt_ollama(prompt, ollama_host, model, system_prompt=system_prompt):
        response_str += response

    return response_str


async def generate_summary(content: str, model: str, ollama_host: str, context: dict[str, any] | None = None) -> str:
    """
    Generate a summary of content using LLM.

    Args:
        content: Content to summarize
        context: Additional context
        model: Name of the LLM model
        ollama_host: URL of the Ollama API

    Returns:
        Generated summary
    """
    if context is None:
        context_snippet = ""
        context_instruction = ""

    else:
        context_text = "\n".join(f"{k}: {v}" for k, v in context.items() if k != "url")
        context_snippet = (
            f"```\n"
            f"{context_text}\n"
            f"```\n"
            f"\n"
        )
        context_instruction = " Consider the provided context in your summary but summarize only the text."

    language = "the text's language"

    prompt = (
        f"{context_snippet}"
        f"```text\n"
        f"{content}\n"
        f"```\n"
        f"\n"
        f"Extract the main claim from the text above. If time, location, and people are available, make sure to "
        f"mention them by converting any and all relative references to their absolute, explicitly, and specific "
        f"counterparts.{context_instruction} Respond in {language} with one single sentence only: no disclaimer, "
        f"introduction, or conclusion.\n"
        "\n"
    )

    system_prompt = "You are an expert at summarizing texts, focusing on key information and facts."

    response_str = ""
    async for response in prompt_ollama(prompt, ollama_host, model, system_prompt=system_prompt):
        response_str += response

    return response_str


async def get_search_query(content: str, context: dict[str, any], model: str, ollama_host: str) -> str:
    """
    Generate a search query for verification using LLM.

    Args:
        content: Content to verify
        context: Additional context
        model: Name of the LLM model
        ollama_host: URL of the Ollama API

    Returns:
        Generated search query
    """
    if context is None:
        context_snippet = ""
        context_instruction = ""

    else:
        context_text = "\n".join(f"{k}: {v}" for k, v in context.items())
        context_snippet = (
            f"```\n"
            f"{context_text}\n"
            f"```\n"
            f"\n"
        )
        context_instruction = "Consider the provided context in your query but verify only the text."

    language = "the text's language"

    prompt = (
        f"{context_snippet}"
        f"```text\n"
        f"{content}\n"
        f"```\n"
        f"\n"
        f"For the provided text, generate a web search engine query that would return the most relevant results on the "
        f"topic. The query should be concise and in {language}.{context_instruction} Be very specific to make sure to "
        f"get only results that are immediately relevant to the text above. Respond with the query only: no "
        f"disclaimer, introduction, or conclusion.\n"
        f"\n"
    )

    system_prompt = "You are an expert at generating web search engine queries to verify information."

    response_str = ""
    async for response in prompt_ollama(prompt, ollama_host, model, system_prompt=system_prompt):
        response_str += response

    return response_str


def check_ollama(model: str, ollama_host: str) -> bool:
    """
    Check if Ollama is running and has the required model.

    Args:
        model: Name of the LLM model to check/pull
        ollama_host: URL of the Ollama API

    Returns:
        True if Ollama is running and the model is available, False otherwise
    """
    logger.info(f"Checking Ollama service and model '{model}'...")

    try:
        client = ollama.Client(host=ollama_host)

    except Exception as e:
        logger.error(f"Could not connect to Ollama API: {e}")
        logger.error("Please make sure Ollama is running: https://ollama.ai/download")
        return False

    try:
        # Use the documented method for listing models
        models = client.list()
        model_names = [m['model'].split(':')[0] for m in models["models"]]

        if model not in model_names:
            logger.info(f"Model '{model}' not found. Pulling...")
            try:
                client.pull(model)
                logger.info(f"Model '{model}' successfully pulled.")
            except Exception as e:
                logger.error(f"Failed to pull model '{model}': {e}")
                return False
        else:
            logger.info(f"Model '{model}' is already available.")

    except Exception as e:
        logger.error(f"Could not list models from Ollama API: {e}")
        return False

    return True


async def test_all_functions():
    """Test all functions in this module"""
    # Configuration
    model = "tulu3"  # oder ein anderes verfügbares Modell
    ollama_host = "http://localhost:11434"
    
    # 1. Test check_ollama
    logger.info("Testing check_ollama function...")
    ollama_available = check_ollama(model, ollama_host)
    if not ollama_available:
        logger.error("Ollama is not available. Stopping tests.")
        return
    
    # 2. Test prompt_ollama
    logger.info("Testing prompt_ollama function...")
    test_prompt = "What is the capital of France?"
    test_system_prompt = "You are a helpful assistant."
    
    logger.info(f"Prompt: {test_prompt}")
    response = ""
    async for chunk in prompt_ollama(test_prompt, ollama_host, model, test_system_prompt):
        response += chunk
    logger.info(f"Response: {response}")
    
    # 3. Test compare_text_segments
    logger.info("Testing compare_text_segments function...")
    original_text = "Paris is the capital of France. It has a population of 2.1 million."
    source_text = "Paris is the capital of France. It has a population of 2.2 million."
    
    logger.info(f"Original: {original_text}")
    logger.info(f"Source: {source_text}")
    comparison = await compare_text_segments(original_text, source_text, model, ollama_host)
    logger.info(f"Comparison result: {comparison}")
    
    # 4. Test generate_summary
    logger.info("Testing generate_summary function...")
    test_content = """Paris, the capital city of France, is renowned for its iconic Eiffel Tower 
    and world-class museums like the Louvre. With a rich history dating back over 2,000 years, 
    it remains one of the most visited tourist destinations globally."""
    
    test_context = {"title": "Paris Tourism Guide", "date": "2023-05-15"}
    
    logger.info(f"Content to summarize: {test_content}")
    summary = await generate_summary(test_content, model, ollama_host, test_context)
    logger.info(f"Summary: {summary}")
    
    # 5. Test get_search_query
    logger.info("Testing get_search_query function...")
    test_query_content = "The COVID-19 pandemic was declared by the WHO on March 11, 2020."
    test_query_context = {"topic": "Global Health", "source": "News Article"}
    
    logger.info(f"Content for query: {test_query_content}")
    query = await get_search_query(test_query_content, test_query_context, model, ollama_host)
    logger.info(f"Generated search query: {query}")
    
    logger.info("All tests completed.")

def main():
    """Main function to run tests"""
    try:
        asyncio.run(test_all_functions())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user.")
    except Exception as e:
        logger.error(f"Error during tests: {e}")

if __name__ == "__main__":
    main()
