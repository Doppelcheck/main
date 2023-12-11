from src.dataobjects import ViewCallbacks
from src.model.model import Model
from src.view.view import View


class Controller:
    def __init__(self, config: dict[str, any]) -> None:
        config_databases = config.pop("redis")
        self.model = Model(config_databases)
        self.view = View()

        view_callbacks = ViewCallbacks(
            self.model.dummy_function
        )

        self.view.set_callbacks(view_callbacks)
        self.view.setup_routes()
