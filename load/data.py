"""
A Loader class to import data into weaviate.
"""
import uuid
from typing import Optional
import weaviate.tools


def generate_uuid(
        key: str
    ) -> str:
    """
    Generate an universally unique identifier (uuid).

    Parameters
    ----------
    key : str
        The key used to generate the uuid.

    Returns
    -------
    str
        Universally unique identifier (uuid) as string.
    """

    return str(uuid.uuid3(uuid.NAMESPACE_DNS, key))


class Loader:
    """
    A Loader class that uploads Newespaper Articles, Publications, Categories and Authors.
    It makes use of the weaviate.tools.Batcher to upload data in batches.
    """

    def __init__(self, batcher:weaviate.tools.Batcher):
        self.batcher = batcher
        self.loaded_articles = []

    def load_category(self,
            data: dict
        ) -> None:
        """
        Load catogory into weaviate.

        Parameters
        ----------
        data : dict
            Category as a dictionary.
        """

        self.batcher.add_data_object(
            data_object=data["schema"],
            class_name=data["class"],
            uuid=data["id"]
        )

    def load_publication(self,
            data: dict
        ) -> None:
        """
        Load Publication into weaviate.

        Parameters
        ----------
        data : dict
            Publication as a dictionary.
        """

        self.batcher.add_data_object(
            data_object=data["schema"],
            class_name=data["class"],
            uuid=data["id"]
        )

    def load_authors_article(self,
            data: dict
        ) -> None:
        """
        Load Authors and Article into weaviate.

        Parameters
        ----------
        data : dict
            Article as a dictionary.
        """

        article_id = generate_uuid(data['title'])

        ##### ADD AUTHORS #####
        author_ids = []
        for author in data['authors']:
            author_id = self.add_author(author, article_id, data['publicationId'])
            if author_id is not None:
                author_ids.append(author_id)
            else:
                # TODO Why to use the publication ID if the author ID is not generated???
                author_ids.append(data['publicationId'])

        ##### ADD ARTICLES #####
        if article_id not in self.loaded_articles:
            self.loaded_articles.append(article_id)
            word_count = len(' '.join(data['paragraphs']).split(' '))
            article_object = {
                'title': data['title'],
                'summary': process_input('Summary', data['summary']),
                'wordCount': word_count,
                'url': data['url'],
            }
            # Set publication date
            if data['pubDate'] is not None and data['pubDate'] != '':
                article_object['publicationDate'] = data['pubDate']
            # Add article to weaviate
            self.batcher.add_data_object(article_object, "Article", article_id)
            # Add reference to weaviate
            self.batcher.add_reference(
                from_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                from_thing_class_name="Article",
                from_thing_uuid=article_id,
                from_property_name="inPublication",
                to_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                to_thing_uuid=data['publicationId'],
            )
            self.batcher.add_reference(
                from_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                from_thing_class_name="Publication",
                from_thing_uuid=data['publicationId'],
                from_property_name="hasArticles",
                to_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                to_thing_uuid=article_id
            )
            self.add_ref_article_authors(author_ids, article_id)

    def add_ref_article_authors(self,
            author_ids: list,
            article_id: str
        ) -> None:
        """
        Add Reference of the Article to the Authors into Batcher
        to be loaded into weaviate.

        Parameters
        ----------
        author_ids : list
            A list of authors uuids to that worte the Article.
        article_id : str
            UUID of the Article.
        """

        for author_id in author_ids:
            self.batcher.add_reference(
                from_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                from_thing_class_name="Article",
                from_thing_uuid=article_id,
                from_property_name="hasAuthors",
                to_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                to_thing_uuid=author_id,
            )

    def add_author(self,
            author: str,
            article_id: str,
            publication_id: str
        ) -> Optional[str]:
        """
        Add Author into Batcher to be loaded into weaviate.

        Parameters
        ----------
        author : str
            Name of the Author.
        article_id : str
            UUID of the Article.
        publication_id : str
            UUID of the Publication.

        Returns
        -------
        Optional[str]
            The processed Author name.
            Only names that consists of two words, otherwise returns None.
        """

        author = process_input('Author', author)
        if len(author.split(' ')) == 2:
            author_uuid = generate_uuid(author)
            self.batcher.add_data_object(
                data_object={'name': author},
                class_name='Author',
                uuid=author_uuid,
            )
            self.batcher.add_reference(
                from_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                from_thing_class_name="Author",
                from_thing_uuid=author_uuid,
                from_property_name="writesFor",
                to_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                to_thing_uuid=publication_id
            )
            self.batcher.add_reference(
                from_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                from_thing_class_name="Author",
                from_thing_uuid=author_uuid,
                from_property_name="wroteArticles",
                to_semantic_type=weaviate.SEMANTIC_TYPE_THINGS,
                to_thing_uuid=article_id
            )
            return author_uuid
        return None


def process_input(
        class_name: str,
        value: str,
    ) -> str:
    """
    Clean up the data.

    Parameters
    ----------
    class_name: str
        Which class the object(see value) to clean belongs to.
    value: str
        The object to clean.

    Returns
    -------
    str
        Cleaned object.
    """

    if class_name == 'Author':
        value = value.replace(' Wsj.Com', '')
        value = value.replace('.', ' ')
    elif class_name == 'Summary':
        value = value.replace('\n', ' ')
    return value
