class Model:
    def __init__(self, redis_config: dict[str, any]) -> None:
        db_config = redis_config.pop("database_01")

    def dummy_function(self, arg: str) -> None:
        pass