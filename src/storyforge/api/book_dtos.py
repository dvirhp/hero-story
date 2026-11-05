"""Future Book adapter schemas only. No routes mounted before secure ownership exists."""

from storyforge.domain.base import Label
from storyforge.domain.books import BookDetail, ManualBookCreate
from storyforge.domain.documents import DocumentContract

# Reuse canonical models rather than maintain divergent wire/domain copies.
BookDetailResponse = BookDetail
ManualBookCreateRequest = ManualBookCreate


class BookTitleUpdate(DocumentContract):
    title: Label
