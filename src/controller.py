from src.dataobjects import ViewCallbacks
from src.model.model import Model
from src.tools.bookmarklet import compile_bookmarklet
from src.view.view import View


class Controller:
    def __init__(self, config: dict[str, any]) -> None:
        bookmarklet_target = compile_bookmarklet()

        config_databases = config.pop("redis")
        self.model = Model(config_databases)
        self.view = View(bookmarklet_target)

        view_callbacks = ViewCallbacks(
            self.model.dummy_function
        )

        self.view.set_callbacks(view_callbacks)
        self.view.setup_routes()
