from app.core.exceptions import ResourceNotFound


class ListeningReferenceNotFound(ResourceNotFound):
    pass


class ListeningEventConflict(Exception):
    pass


class InvalidListeningEvent(Exception):
    pass
