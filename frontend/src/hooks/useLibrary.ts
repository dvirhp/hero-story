import { useState } from "react";
import { catalog, sampleBook } from "../data/catalog";
import { createBlankBook } from "../domain/book";
import type { Book } from "../domain/book";
import { readTab, isBooks, useRecovery } from "../state/tabRecovery";
function fixtures(): Book[] {
  const first = sampleBook(catalog[0], "en");
  first.id = "demo-whale";
  first.createdAt = "2026-11-03T10:00:00Z";
  const second = sampleBook(catalog[1], "he");
  second.id = "demo-moon";
  second.createdAt = "2026-11-04T10:00:00Z";
  const draft = createBlankBook("en");
  draft.id = "demo-draft";
  draft.title = "The day the clouds came down";
  draft.createdAt = "2026-11-05T08:00:00Z";
  draft.pages[0].sentenceUnits = [
    "One morning, a cloud knocked softly at the window.",
  ];
  draft.cover = "whale";
  draft.pages[0].illustration = "whale";
  return [draft, second, first];
}
/** Deliberately in-memory: no localStorage, cookies, ownership or persistence APIs. */
export function useLibrary(remember = false) {
  const [books, setBooks] = useState<Book[]>(
    () => readTab("books", isBooks) ?? fixtures(),
  );
  const storageFailed = useRecovery("books", books, remember);
  const save = (book: Book) =>
    setBooks((current) => [
      structuredClone(book),
      ...current.filter((item) => item.id !== book.id),
    ]);
  const remove = (id: string) =>
    setBooks((current) => current.filter((item) => item.id !== id));
  return { books, save, remove, storageFailed };
}
