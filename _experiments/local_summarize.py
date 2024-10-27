from typing_extensions import Any
from pydantic import BaseModel, ConfigDict
from enum import Enum
import rich
import asyncio

from ollama_instructor.ollama_instructor_client import OllamaInstructorAsyncClient

class Gender(Enum):
    MALE = 'male'
    FEMALE = 'female'

class Person(BaseModel):
    '''
    This model defines a person.
    '''
    name: str
    age: int
    gender: Gender
    likes: list[str] = []
    friends: list[str] = []

    model_config = ConfigDict(
        extra='forbid'
    )

async def process_request(client: OllamaInstructorAsyncClient, messages: list[dict[str, Any]]) -> str:
    response = await client.chat_completion(
        model='qwen2.5',
        pydantic_model=Person,
        messages=messages,
    )
    return response['message']['content']

async def main() -> None:
    client = OllamaInstructorAsyncClient()
    await client.async_init()  # Important: must call this before using the client

    requests = [
        process_request(client, [
            {
                'role': 'user',
                'content': 'Jason is 25 years old. Jason loves to play soccer with his friends Nick and Gabriel. His favorite food is pizza.'
            }
        ]),
        process_request(client, [
            {
                'role': 'user',
                'content': 'Alice is 30 years old. Alice enjoys reading books and hiking in her free time. Her favorite season is fall.'
            }
        ]),
        process_request(client, [
            {
                'role': 'user',
                'content': 'Bob is 28 years old. Bob works as a software developer and loves coding and gaming on weekends.'
            }
        ])
    ]

    responses = await asyncio.gather(*requests)
    for response in responses:
        rich.print(response)

if __name__ == "__main__":
    asyncio.run(main())