try:
    from app.schemas_legacy import ArtistOutputSchema, DirectorOutputSchema, ReaderOutputSchema

    __all__ = ["ArtistOutputSchema", "DirectorOutputSchema", "ReaderOutputSchema"]
except ImportError:  # pragma: no cover
    __all__ = []
