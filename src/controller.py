from src.dataobjects import ViewCallbacks
from src.model.model import Model
from src.tools.bookmarklet import get_bookmarklet_template
from src.view.view import View


class Controller:
    def __init__(self, config: dict[str, any]) -> None:
        bookmarklet_template = get_bookmarklet_template()

        config_databases = config.pop("redis")
        self.model = Model(config_databases)
        self.view = View(bookmarklet_template)

        view_callbacks = ViewCallbacks(
            self.model.dummy_function
        )

        self.view.set_callbacks(view_callbacks)
        self.view.setup_routes()
