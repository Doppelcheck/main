from _deprecated.src.agents.comparison import AgentComparison
from _deprecated.src.agents.extraction import AgentExtraction
from _deprecated.src.agents.retrieval import AgentRetrieval
from _deprecated.src.dataobjects import ViewCallbacks
from _deprecated.src.model.model import Model
from _deprecated.src.tools.bookmarklet import get_bookmarklet_template
from _deprecated.src.view.view import View


class Controller:
    def __init__(self, config: dict[str, any]) -> None:
        bookmarklet_template = get_bookmarklet_template()

        config_agents = config.pop("agents")

        agent_interface = config.pop("agent_interface")
        config_extraction_agent = config_agents.pop("extraction")
        self.extractor_agent = AgentExtraction(config_extraction_agent, agent_interface)

        config_retrieval_agent = config_agents.pop("retrieval")
        config_google = config.pop("google")
        self.retrieval_agent = AgentRetrieval(config_retrieval_agent, config_google, agent_interface)

        config_comparison_agent = config_agents.pop("comparison")
        self.comparison_agent = AgentComparison(config_comparison_agent, agent_interface)

        config_databases = config.pop("redis")
        self.model = Model(config_databases)
        self.view = View(bookmarklet_template)

        view_callbacks = ViewCallbacks(
            self.model.dummy_function,
            lambda: self.extractor_agent,
            lambda: self.retrieval_agent,
            lambda: self.comparison_agent,
        )

        self.view.set_callbacks(view_callbacks)
        self.view.setup_routes()
