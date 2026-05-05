"""
Interface to Llama-3.1-Tulu-3.1-8B LLM for various tasks using transformers.
"""

from typing import AsyncGenerator
import asyncio
from loguru import logger
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread


async def prompt_transformers(prompt: str, model_name: str = "allenai/Llama-3.1-Tulu-3.1-8B", system_prompt: str | None = None) -> AsyncGenerator[str, None]:
    """
    Send a prompt to the LLM and stream the response.

    Args:
        prompt: The prompt to send
        model_name: Name of the model on Hugging Face
        system_prompt: Optional system prompt

    Yields:
        Generated text chunks
    """
    # Load model and tokenizer
    if not hasattr(prompt_transformers, "model") or not hasattr(prompt_transformers, "tokenizer"):
        logger.info(f"Loading model and tokenizer for {model_name}...")
        prompt_transformers.tokenizer = AutoTokenizer.from_pretrained(model_name)

        # Set pad token to eos token if not set
        if prompt_transformers.tokenizer.pad_token is None:
            prompt_transformers.tokenizer.pad_token = prompt_transformers.tokenizer.eos_token

        prompt_transformers.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            low_cpu_mem_usage=True
        )
        logger.info(f"Model and tokenizer loaded successfully.")

    # Prepare messages
    messages = []
    if system_prompt is not None:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    # Convert messages to the format expected by the model
    input_text = prompt_transformers.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    # Tokenize the input
    inputs = prompt_transformers.tokenizer(input_text, return_tensors="pt", padding=True)
    input_ids = inputs["input_ids"].to("cuda" if torch.cuda.is_available() else "cpu")
    attention_mask = inputs["attention_mask"].to("cuda" if torch.cuda.is_available() else "cpu")

    # Create a streamer
    streamer = TextIteratorStreamer(prompt_transformers.tokenizer, timeout=10, skip_prompt=True, skip_special_tokens=True)

    # Generate in a separate thread
    generation_kwargs = dict(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=1024,
        temperature=0.7,
        top_p=0.9,
        pad_token_id=prompt_transformers.tokenizer.pad_token_id,
        streamer=streamer,
    )

    thread = Thread(target=prompt_transformers.model.generate, kwargs=generation_kwargs)
    thread.start()

    # Yield from the streamer
    for text in streamer:
        yield text
        await asyncio.sleep(0.01)


async def compare_text_segments(original_chunk: str, source_chunk: str, model_name: str = "allenai/Llama-3.1-Tulu-3.1-8B") -> str:
    """
    Compare two text segments using LLM.

    Args:
        original_chunk: Original chunk content
        source_chunk: Source chunk content
        model_name: Name of the model on Hugging Face

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
        f"\n"
    )

    system_prompt = "You are an expert at spotting conflicting statements."

    response_str = ""
    async for response in prompt_transformers(prompt, model_name, system_prompt=system_prompt):
        response_str += response

    return response_str


async def generate_summary(content: str, model_name: str = "allenai/Llama-3.1-Tulu-3.1-8B", context: dict[str, any] | None = None) -> str:
    """
    Generate a summary of content using LLM.

    Args:
        content: Content to summarize
        model_name: Name of the model on Hugging Face
        context: Additional context

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
        f"\n"
    )

    system_prompt = "You are an expert at summarizing texts, focusing on key information and facts."

    response_str = ""
    async for response in prompt_transformers(prompt, model_name, system_prompt=system_prompt):
        response_str += response

    return response_str


async def get_search_query(content: str, context: dict[str, any], model_name: str = "allenai/Llama-3.1-Tulu-3.1-8B") -> str:
    """
    Generate a search query for verification using LLM.

    Args:
        content: Content to verify
        context: Additional context
        model_name: Name of the model on Hugging Face

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
    async for response in prompt_transformers(prompt, model_name, system_prompt=system_prompt):
        response_str += response

    return response_str


def check_model_availability(model_name: str = "allenai/Llama-3.1-Tulu-3.1-8B") -> bool:
    """
    Check if the model is available on Hugging Face.

    Args:
        model_name: Name of the model on Hugging Face

    Returns:
        True if the model is available, False otherwise
    """
    logger.info(f"Checking availability of model '{model_name}'...")

    try:
        # We don't want to fully load the model here, just check if we can access its configuration
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(model_name)
        logger.info(f"Config for model '{model_name}' is available.")

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        logger.info(f"Tokenizer for model '{model_name}' is available.")

        return True
    except Exception as e:
        logger.error(f"Could not access model '{model_name}': {e}")
        return False


async def test_all_functions():
    """Test all functions in this module"""
    # Configuration
    model_name = "allenai/Llama-3.1-Tulu-3.1-8B"

    # 1. Test check_model_availability
    logger.info("Testing check_model_availability function...")
    model_available = check_model_availability(model_name)
    if not model_available:
        logger.error("Model is not available. Stopping tests.")
        return

    # 2. Test prompt_transformers
    logger.info("Testing prompt_transformers function...")
    test_prompt = "What is the capital of France?"
    test_system_prompt = "You are a helpful assistant."

    logger.info(f"Prompt: {test_prompt}")
    response = ""
    async for chunk in prompt_transformers(test_prompt, model_name, test_system_prompt):
        response += chunk
    logger.info(f"Response: {response}")

    # 3. Test compare_text_segments
    logger.info("Testing compare_text_segments function...")
    original_text = "Paris is the capital of France. It has a population of 2.1 million."
    source_text = "Paris is the capital of France. It has a population of 2.2 million."

    logger.info(f"Original: {original_text}")
    logger.info(f"Source: {source_text}")
    comparison = await compare_text_segments(original_text, source_text, model_name)
    logger.info(f"Comparison result: {comparison}")

    # 4. Test generate_summary
    logger.info("Testing generate_summary function...")
    test_content = """Paris, the capital city of France, is renowned for its iconic Eiffel Tower 
    and world-class museums like the Louvre. With a rich history dating back over 2,000 years, 
    it remains one of the most visited tourist destinations globally."""

    test_context = {"title": "Paris Tourism Guide", "date": "2023-05-15"}

    logger.info(f"Content to summarize: {test_content}")
    summary = await generate_summary(test_content, model_name, test_context)
    logger.info(f"Summary: {summary}")

    # 5. Test get_search_query
    logger.info("Testing get_search_query function...")
    test_query_content = "The COVID-19 pandemic was declared by the WHO on March 11, 2020."
    test_query_context = {"topic": "Global Health", "source": "News Article"}

    logger.info(f"Content for query: {test_query_content}")
    query = await get_search_query(test_query_content, test_query_context, model_name)
    logger.info(f"Generated search query: {query}")

    logger.info("All tests completed.")


def main():
    """Main function to run tests"""
    assert torch.cuda.is_available()

    try:
        asyncio.run(test_all_functions())
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user.")
    except Exception as e:
        logger.error(f"Error during tests: {e}")


if __name__ == "__main__":
    main()