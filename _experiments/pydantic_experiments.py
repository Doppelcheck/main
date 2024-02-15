from pydantic import BaseModel, Field


class CustomBaseModel(BaseModel):

    def __init__(self, path: tuple[str, ...] | None = None, **data: any) -> None:
        super().__init__(**data)
        self._path = tuple() or path

    def __setattr__(self, key: str, value: any) -> None:
        super().__setattr__(key, value)  # Set the attribute using the superclass method
        if not key.startswith("_"):
            self.set_callback(key, value)

    def __getattribute__(self, key: str) -> any:
        value = object.__getattribute__(self, key)
        if not key.startswith("_"):
            get_callback = object.__getattribute__(self, "get_callback")
            get_callback(key, value)
        return value

    def set_callback(self, key: str, value: any) -> None:
        # Define your callback logic here
        print(f"Attribute {key} set to {value}")

    def get_callback(self, key: str, value: any) -> None:
        # Define your callback logic here
        print(f"Attribute {key} has value {value}")


class A(CustomBaseModel):
    a: int
    b: int
    c: int = 1
    d: int = 2


class B(A):
    a: int
    b: int = 3
    c: int = 4


class C(CustomBaseModel):
    a: A
    b: B


class D(C):
    a: A
    b: B = Field(default_factory=lambda: B(a=1))


if __name__ == "__main__":
    a = A(a=1, b=2)
    b = B(a=1)
    c = C(a=a, b=b)
    d = D(a=a)

    print(a)
    """
    print(b)
    print(c)
    print(d)

    c.a = A(a=2, b=3)
    print(d.b)
    """