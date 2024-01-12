import asyncio
import dataclasses
import json
from pprint import pprint
from typing import Generator

from src.agents.comparison import AgentComparison, Match
from src.agents.retrieval import AgentRetrieval


async def press_opinions(
        claim: str,
        agent_comparison: AgentComparison, agent_retrieval: AgentRetrieval) -> Generator[Match, None, None]:
    documents = agent_retrieval.retrieve_documents(claim)
    async for each_document in documents:
        each_match = await agent_comparison.compare(claim, each_document)
        yield each_match


async def main() -> None:
    # todo: bash `playwright install`
    with open("../../config/config.json", mode="r", encoding="utf-8") as f:
        config = json.load(f)

    google_config = config["google"]
    openai_config = config["agent_interface"]

    agents_config = config["agents"]
    extraction_config = agents_config["extraction"]
    retrieval_config = agents_config["retrieval"]
    comparison_config = agents_config["comparison"]

    agent_retrieval = AgentRetrieval(retrieval_config, google_config, openai_config)
    agent_comparison = AgentComparison(comparison_config, openai_config)

    claim = "Israel wird vor dem Internationalen Gerichtshof wegen des Verdachts auf Völkermord im Gazastreifen angeklagt."
    claim = "Südafrika hat den Internationalen Gerichtshof aufgefordert, Israels Vorgehen gegen die Hamas als Völkermord einzustufen. "

    i = 0
    async for each_match in press_opinions(claim, agent_comparison, agent_retrieval):
        pprint(each_match)
        with open(f"{i:02d}.json", mode="w", encoding="utf-8") as f:
            each_dict = dataclasses.asdict(each_match)
            json.dump(each_dict, f, indent=2)
        i += 1


if __name__ == "__main__":
    asyncio.run(main())
