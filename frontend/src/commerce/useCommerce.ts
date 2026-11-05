import { useState } from "react";
import type { Book } from "../domain/book";
import { addLine } from "./model";
import type { CartLine, DemoOrder, Format } from "./model";
import { readTab, useRecovery, isBook } from "../state/tabRecovery";
import { configurationKey, demoOffer } from "./model";
export function isCartLines(value: unknown): value is CartLine[] {
  return (
    Array.isArray(value) &&
    value.length <= 40 &&
    value.every(
      (line) =>
        line &&
        typeof line === "object" &&
        typeof line.id === "string" &&
        isBook(line.book) &&
        demoOffer.formats.some((option) => option.id === line.format) &&
        Number.isInteger(line.quantity) &&
        line.quantity > 0 &&
        line.quantity <= 10 &&
        line.offerId === demoOffer.id &&
        line.configuration === configurationKey(line.book, line.format),
    )
  );
}
export function useCommerce(remember = false) {
  const [lines, setLines] = useState<CartLine[]>(
    () => readTab("bag", isCartLines) ?? [],
  );
  const [orders, setOrders] = useState<DemoOrder[]>([]);
  const storageFailed = useRecovery("bag", lines, remember);
  const add = (book: Book, format: Format, quantity: number) => {
    const next = addLine(lines, book, format, quantity);
    setLines(next);
  };
  const update = (id: string, quantity: number) => {
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 10) return;
    setLines((current) =>
      current.map((line) => (line.id === id ? { ...line, quantity } : line)),
    );
  };
  const remove = (id: string) =>
    setLines((current) => current.filter((line) => line.id !== id));
  const complete = (order: DemoOrder) => {
    setOrders((current) =>
      current.some((item) => item.id === order.id)
        ? current
        : [order, ...current],
    );
    setLines([]);
  };
  return {
    lines,
    orders,
    add,
    update,
    remove,
    complete,
    storageFailed,
    count: lines.reduce((sum, line) => sum + line.quantity, 0),
  };
}
