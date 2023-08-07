from typing import Optional
import strawberry


@strawberry.input()
class ComboboxInput:
    id: Optional[int] = None
    name: str
