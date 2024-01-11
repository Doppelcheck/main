import asyncio
import dataclasses
import json
from pprint import pprint

from src.agents.comparison import AgentComparison
from src.agents.retrieval import AgentRetrieval


async def main() -> None:
    # todo: bash `playwright install`
    claim_a = "Israel wird vor dem Internationalen Gerichtshof wegen des Verdachts auf Völkermord im Gazastreifen angeklagt."
    claim_b = "Südafrika hat den Internationalen Gerichtshof aufgefordert, Israels Vorgehen gegen die Hamas als Völkermord einzustufen. "

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

    documents = agent_retrieval.retrieve_documents(claim_b)
    i = 0
    async for each_document in documents:
        pprint(each_document)
        each_match = await agent_comparison.compare(claim_b, each_document)
        with open(f"{i:02d}.json", mode="w", encoding="utf-8") as f:
            each_dict = dataclasses.asdict(each_match)
            json.dump(each_dict, f, indent=2)
        i += 1


if __name__ == "__main__":
    asyncio.run(main())
