import { useEffect, useState } from "react";
import type { Book } from "../domain/book";
const prefix = "storyforge.tab.v1.";
export function remembers() {
  try {
    return sessionStorage.getItem(`${prefix}consent`) === "yes";
  } catch {
    return false;
  }
}
export function readTab<T>(
  key: string,
  valid: (value: unknown) => value is T,
): T | null {
  try {
    if (!remembers()) return null;
    const raw = sessionStorage.getItem(prefix + key);
    if (!raw || raw.length > 1000000) return null;
    const value: unknown = JSON.parse(raw);
    return valid(value) ? value : null;
  } catch {
    return null;
  }
}
export function writeTab(key: string, value: unknown): boolean {
  try {
    if (!remembers()) return true;
    const text = JSON.stringify(value);
    if (text.length > 1000000) return false;
    sessionStorage.setItem(prefix + key, text);
    return true;
  } catch {
    return false;
  }
}
export function clearTab() {
  try {
    for (const key of Object.keys(sessionStorage))
      if (key.startsWith(prefix)) sessionStorage.removeItem(key);
  } catch {
    /* Storage may be disabled; in-memory use remains available. */
  }
}
export function useRemember() {
  const [remember, setRemember] = useState(remembers);
  const [failed, setFailed] = useState(false);
  const update = (value: boolean) => {
    setFailed(false);
    if (!value) clearTab();
    else
      try {
        sessionStorage.setItem(`${prefix}consent`, "yes");
      } catch {
        setFailed(true);
        return;
      }
    setRemember(value);
  };
  return { remember, setRemember: update, failed };
}
export function useRecovery<T>(key: string, value: T, enabled: boolean) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    setFailed(enabled && !writeTab(key, value));
  }, [key, value, enabled]);
  return failed;
}
const record = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === "object" && !Array.isArray(value);
const text = (value: unknown, max: number) =>
  typeof value === "string" && value.length <= max;
const arts = [
  "whale",
  "moon",
  "alphabet",
  "hero",
  "hero-striped",
  "family",
  "garden",
];
function validCharacter(value: unknown): boolean {
  if (value === undefined) return true;
  if (!record(value)) return false;
  return (
    [
      ["presentation", ["neutral", "boy", "girl"]],
      ["skin", ["light", "warm", "deep"]],
      ["hair", ["chestnut", "black", "gold"]],
      ["hairstyle", ["shortHair", "curls", "longHair"]],
      ["eye", ["brownEyes", "blueEyes", "greenEyes"]],
      ["outfit", ["explorer", "sailor"]],
      ["accessory", ["none", "starPin", "hat"]],
    ].every(([key, options]) =>
      (options as string[]).includes(value[key as string] as string),
    ) &&
    typeof value.glasses === "boolean" &&
    typeof value.freckles === "boolean"
  );
}
export function isBook(value: unknown): value is Book {
  if (
    !record(value) ||
    value.schemaVersion !== "1" ||
    !text(value.id, 100) ||
    !text(value.title, 120) ||
    (value.childName !== undefined && !text(value.childName, 40)) ||
    (value.dedication !== undefined && !text(value.dedication, 500)) ||
    (value.template !== undefined &&
      (!record(value.template) ||
        !text(value.template.id, 100) ||
        !text(value.template.version, 100) ||
        !record(value.template.values) ||
        !Object.values(value.template.values).every((item) =>
          text(item, 1500),
        ))) ||
    (value.editedFrom !== undefined &&
      (!record(value.editedFrom) ||
        !text(value.editedFrom.id, 100) ||
        !["AI_GENERATED", "TEMPLATE_BASED", "MANUAL"].includes(
          String(value.editedFrom.method),
        ))) ||
    !["en", "he"].includes(String(value.language)) ||
    !["AI_GENERATED", "TEMPLATE_BASED", "MANUAL"].includes(
      String(value.method),
    ) ||
    !["draft", "ready", "failed"].includes(String(value.status)) ||
    !arts.includes(String(value.cover)) ||
    typeof value.coverColor !== "string" ||
    !/^#[0-9a-f]{6}$/i.test(value.coverColor) ||
    !Array.isArray(value.pages) ||
    value.pages.length < 1 ||
    value.pages.length > 32 ||
    !validCharacter(value.character) ||
    typeof value.demo !== "boolean" ||
    !Number.isFinite(Date.parse(String(value.createdAt))) ||
    !Number.isFinite(Date.parse(String(value.updatedAt)))
  )
    return false;
  return (
    new Set(value.pages.map((page) => (record(page) ? page.pageId : null)))
      .size === value.pages.length &&
    value.pages.every(
      (page, i) =>
        record(page) &&
        text(page.pageId, 150) &&
        (page.targetId === undefined ||
          page.targetId === null ||
          text(page.targetId, 150)) &&
        page.pageNumber === i + 1 &&
        ["split", "full", "text"].includes(String(page.layout)) &&
        ["cream", "mint", "pink", "lavender", "sky"].includes(
          String(page.background),
        ) &&
        (page.illustration === null ||
          arts.includes(String(page.illustration))) &&
        Array.isArray(page.sentenceUnits) &&
        page.sentenceUnits.length <= 200 &&
        page.sentenceUnits.every((unit) => text(unit, 12000)) &&
        validCharacter(page.character) &&
        (!page.imageFrame ||
          (record(page.imageFrame) &&
            ["x", "y", "scale"].every(
              (key) =>
                typeof page.imageFrame === "object" &&
                page.imageFrame !== null &&
                Number.isFinite(
                  (page.imageFrame as Record<string, unknown>)[key],
                ) &&
                Number((page.imageFrame as Record<string, unknown>)[key]) >=
                  0 &&
                Number((page.imageFrame as Record<string, unknown>)[key]) <=
                  100,
            ))),
    )
  );
}
export function isBooks(value: unknown): value is Book[] {
  return Array.isArray(value) && value.length <= 40 && value.every(isBook);
}
