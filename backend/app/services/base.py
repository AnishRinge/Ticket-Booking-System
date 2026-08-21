from typing import Generic, TypeVar
from sqlalchemy.orm import Session
from app.repositories.base import BaseRepository

RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)

class BaseService(Generic[RepositoryType]):
    def __init__(self, repository: RepositoryType):
        self.repository = repository

    # Standard service methods can be added here
