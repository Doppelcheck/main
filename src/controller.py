import lingua
import nltk

from src.agents.extraction import AgentExtraction
from src.dataobjects import ViewCallbacks
from src.model.model import Model
from src.tools.bookmarklet import get_bookmarklet_template
from src.view.view import View


class Controller:
    def __init__(self, config: dict[str, any]) -> None:
        bookmarklet_template = get_bookmarklet_template()

        config_agents = config.pop("agents")

        config_extraction_agent = config_agents.pop("extraction")
        agent_interface = config.pop("agent_interface")
        self.extractor_agent = AgentExtraction(config_extraction_agent, agent_interface)
        # todo: add comparison_agent and retrieval_agent
        self.comparison_agent = None
        self.retrieval_agent = None

        config_databases = config.pop("redis")
        self.model = Model(config_databases)
        self.view = View(bookmarklet_template)

        view_callbacks = ViewCallbacks(
            self.model.dummy_function,
            self.get_extractor_agent,
        )

        self.view.set_callbacks(view_callbacks)
        self.view.setup_routes()

    def get_extractor_agent(self) -> AgentExtraction:
        return self.extractor_agent
