from openai import OpenAI
from pydantic import BaseModel, Field

import instructor


class StockInfo(BaseModel):
    company: str = Field(..., description="The company name")
    ticker: str = Field(..., description="The stock ticker")


def main() -> None:
    company = "Apple Inc."
    #company = "Google"

    client = instructor.from_openai(
        OpenAI(
            base_url="http://localhost:8800/v1",
            api_key="ollama"
        ),
        mode=instructor.Mode.JSON
    )

    response = client.chat.completions.create(
        # model="llama2",
        model="mistral",
        messages=[
            {"role": "user", "content": f"Return company name and ticker symbol for {company}"}
        ],
        response_model=StockInfo,
    )

    response_json = response.model_dump(mode="json")

    print(response_json)


if __name__ == "__main__":
    main()
