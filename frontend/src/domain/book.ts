import type { Language, StoryV2 } from "../api/contracts";
import type { Character } from '../personalization/character';
export type CreationMethod = "AI_GENERATED" | "TEMPLATE_BASED" | "MANUAL";
export type Art =
  | "whale"
  | "moon"
  | "alphabet"
  | "hero"
  | "hero-striped"
  | "family"
  | "garden";
export type PageColor = "cream" | "mint" | "pink" | "lavender" | "sky";
export type PageLayout = "split" | "full" | "text";
export interface BookPage {
  pageId: string;
  pageNumber: number;
  targetId?: string | null;
  sentenceUnits: string[];
  illustration: Art | null;
  layout: PageLayout;
  background: PageColor;
  character?: Character;
  imageFrame?: {x:number;y:number;scale:number};
}
/** Frontend canonical v1 view model, NOT an existing persistence/manual HTTP DTO. */
export interface Book {
  schemaVersion: "1";
  id: string;
  method: CreationMethod;
  title: string;
  language: Language;
  childName?: string;
  character?: Character;
  dedication?: string;
  editedFrom?: {id:string;method:CreationMethod};
  createdAt: string;
  updatedAt: string;
  status: "draft" | "ready" | "failed";
  cover: Art;
  coverColor: string;
  pages: BookPage[];
  demo: boolean;
  template?: { id: string; version: string; values: Record<string, string> };
  generation?: {
    schemaVersion: "2";
    profileId: string;
    profileVersion: string;
  };
}
export const newId = () => crypto.randomUUID();
export function blankPage(): BookPage {
  return {
    pageId: newId(),
    pageNumber: 1,
    sentenceUnits: [""],
    illustration: "garden",
    layout: "split",
    background: "cream",
  };
}
export function createBlankBook(language: Language): Book {
  const now = new Date().toISOString();
  return {
    schemaVersion: "1",
    id: newId(),
    method: "MANUAL",
    title: "",
    language,
    childName: "",
    createdAt: now,
    updatedAt: now,
    status: "draft",
    cover: "garden",
    coverColor: "#b7cfc1",
    pages: [blankPage()],
    demo: true,
  };
}
export function reindex(pages: BookPage[]): BookPage[] {
  return pages.map((page, i) => ({ ...page, pageNumber: i + 1 }));
}
export function movePage(book: Book, from: number, to: number): Book {
  if (
    to < 0 ||
    to >= book.pages.length ||
    from < 0 ||
    from >= book.pages.length
  )
    return book;
  const pages = [...book.pages];
  const [page] = pages.splice(from, 1);
  pages.splice(to, 0, page);
  return { ...book, pages: reindex(pages), status: "draft" };
}
export function canFinalize(book: Book): boolean {
  return (
    !!book.title.trim() &&
    book.title.length <= 120 &&
    book.pages.length > 0 &&
    book.pages.length <= 32 &&
    book.pages.every(
      (page) =>
        page.sentenceUnits.some((text) => text.trim()) &&
        page.sentenceUnits.join("\n").length <= 12000,
    )
  );
}
export function bookFromStory(
  story: StoryV2,
  childName: string,
  demo = true,
): Book {
  const now = new Date().toISOString();
  return {
    schemaVersion: "1",
    id: newId(),
    method: "AI_GENERATED",
    title: story.title,
    language: story.language,
    childName,
    createdAt: now,
    updatedAt: now,
    status: "ready",
    cover: "garden",
    coverColor: "#b7cfc1",
    demo,
    pages: story.pages.map((page) => ({
      pageId: page.page_id,
      pageNumber: page.page_number,
      targetId: page.target_id,
      sentenceUnits: [...page.sentence_units],
      illustration: null,
      layout: "text",
      background: "cream",
    })),
    generation: {
      schemaVersion: "2",
      profileId: story.profile_id,
      profileVersion: story.profile_version,
    },
  };
}
