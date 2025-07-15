import meilisearch
import time
from app.core.config import settings

meili_client = meilisearch.Client(
    settings.MEILI_SEARCH_URL, settings.MEILI_SEARCH_API_KEY
)


class MeiliSearchService:
    """
    A service class for managing Meilisearch operations.
    """

    def __init__(
        self,
        meili_client: meilisearch.Client = meili_client,
        index_name: str = "ktechhub",
    ):
        """
        Initialize the service with a Meilisearch client and an index name.
        :param meili_client: The Meilisearch client instance.
        :param index_name: The name of the index to operate on.
        """
        self.client = meili_client
        self.index = meili_client.index(index_name)

    def list_data(self, limit=50, offset=0):
        """
        List documents from the index with pagination.
        """
        return self.index.get_documents({"limit": limit, "offset": offset})

    def get_one(self, document_id):
        """
        Retrieve a single document by ID.
        """
        return self.index.get_document(document_id)

    def create_one(self, document):
        """
        Create a single document.
        """
        return self.index.add_documents([document])

    def create_many(self, documents):
        """
        Create multiple documents at once.
        """
        return self.index.add_documents(documents)

    def update_one(self, document_id, updates):
        """
        Update a single document.
        """
        updates["id"] = document_id  # Ensure ID is present in the update
        return self.index.update_documents([updates])

    def update_many(self, documents):
        """
        Update multiple documents at once.
        """
        return self.index.update_documents(documents)

    def delete_one(self, document_id):
        """
        Delete a single document by ID.
        """
        return self.index.delete_document(document_id)

    def delete_many(self, document_ids):
        """
        Delete multiple documents at once.
        """
        return self.index.delete_documents(document_ids)

    def delete_all(self):
        """
        Delete all documents from the index.
        """
        return self.index.delete_all_documents()

    def search(self, query, filters=None, limit=10, offset=0, sort=None):
        """
        Perform a search query with optional filters.
        """
        search_params = {"limit": limit, "offset": offset}
        if filters:
            search_params["filter"] = filters
        if sort:
            search_params["sort"] = sort
        return self.index.search(query, search_params)
