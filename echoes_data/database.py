from sqlalchemy import Engine

from echoes_data.utils import Dialect


class EchoesDB:
    def __init__(self, engine: Engine, dialect: Dialect) -> None:
        self.engine = engine
        self.dialect = dialect
