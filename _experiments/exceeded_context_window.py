import json
import tiktoken
import asyncio
import openai


async def main() -> None:
    with open("../.nicegui/storage-general.json", mode="r") as f:
        config_json = f.read()

    config = json.loads(config_json)
    api_key = config["system"]["config"]["llm_interfaces"]["OpenAI API (free during beta)"]["api_key"]

    prompt = "What is the capital of the United States?" * 10_000
    client = openai.AsyncOpenAI(api_key=api_key)
    messages = [{"role": "user", "content": prompt}]

    token = tiktoken.encoding_for_model("gpt-3.5-turbo")

    token.encode("\n".join(f"{each_message['role']}: {each_message['content']}" for each_message in messages))

    arguments = {"model": "gpt-3.5-turbo"}

    try:
        response = await client.chat.completions.create(messages=messages, **arguments)
        print(response.model_dump(mode="json"))

    except openai.BadRequestError as e:
        if e.code == 'context_length_exceeded':
            print("Context length exceeded")

    except Exception as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
