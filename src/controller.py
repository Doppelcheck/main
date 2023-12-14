import lingua

from src.dataobjects import ViewCallbacks
from src.model.model import Model
from src.tools.bookmarklet import get_bookmarklet_template
from src.view.view import View


class Controller:
    def __init__(self, config: dict[str, any]) -> None:
        bookmarklet_template = get_bookmarklet_template()
        detector = lingua.LanguageDetectorBuilder.from_all_languages()
        self.detector_built = detector.build()

        config_databases = config.pop("redis")
        self.model = Model(config_databases)
        self.view = View(bookmarklet_template)

        self.agent_config = config.pop("agent_interface")
        view_callbacks = ViewCallbacks(
            self.model.dummy_function,
            self.get_agent_config,
            self.detect_language
        )

        self.view.set_callbacks(view_callbacks)
        self.view.setup_routes()

    def get_agent_config(self) -> dict[str, any]:
        return dict(self.agent_config)

    def detect_language(self, text: str) -> str:
        language = self.detector_built.detect_language_of(text)
        if language is None:
            return "en"

        return language.iso_code_639_1.name.lower()
