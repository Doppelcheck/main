from openai import OpenAI
from pydantic import BaseModel, Field

import instructor


class Symbol(BaseModel):
    pass


class GoogleSymbol(Symbol):
    company: str = "Google"
    ticker: str = "GOOGL"


class AppleSymbol(Symbol):
    company: str = "Apple Inc."
    ticker: str = "AAPL"


class TeslaSymbol(Symbol):
    company: str = "Tesla Inc."
    ticker: str = "TSLA"


class MicrosoftSymbol(Symbol):
    company: str = "Microsoft Corporation"
    ticker: str = "MSFT"


class AmazonSymbol(Symbol):
    company: str = "Amazon.com Inc."
    ticker: str = "AMZN"


class FacebookSymbol(Symbol):
    company: str = "Meta Platforms Inc."
    ticker: str = "META"


class StockInfo(BaseModel):
    symbol: GoogleSymbol | AppleSymbol | TeslaSymbol | MicrosoftSymbol | AmazonSymbol | FacebookSymbol = Field(..., description="The company symbol")


def main() -> None:
    #company = "Apple Inc."
    company = "Google"

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
