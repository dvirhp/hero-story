import { describe, expect, it } from "vitest";
import { ageInMonths, initialDraft, prepareRequest } from "../src/domain/brief";
const valid = { ...initialDraft, name: "Noam", theme: "Moon garden" };
describe("v2 brief normalization", () => {
  it.each([
    ["0", "months", 0],
    ["36", "months", 36],
    ["3", "years", 36],
    ["1.5", "years", 18],
    ["0.25", "years", 3],
    ["1000", "years", 12000],
  ] as const)("normalizes %s %s to %s months", (age, unit, expected) =>
    expect(ageInMonths(age, unit)).toBe(expected),
  );
  it.each([
    "",
    "-1",
    "1.1",
    "0.00000000001",
    "Infinity",
    "NaN",
    "1e3",
    "9007199254740992",
  ])("rejects unsupported month input %s", (age) =>
    expect(ageInMonths(age, "months")).toBeNull(),
  );
  it("requires exact months from years", () =>
    expect(ageInMonths("1.1", "years")).toBeNull());
  it("keeps user pages independent of age", () => {
    for (const age of ["0", "3", "12", "36", "72", "1200"])
      expect(
        prepareRequest({ ...valid, age, ageUnit: "months", pages: "27" })
          .request?.page_count,
      ).toBe(27);
  });
  it.each(["0", "33", "2.5", ""])(
    "rejects out-of-policy page count %s without clamping",
    (pages) =>
      expect(prepareRequest({ ...valid, pages }).errors.pages).toBe(
        "invalidPages",
      ),
  );
  it("preserves supplied name and sends no unsupported years field", () => {
    const request = prepareRequest({
      ...valid,
      name: " נועם ",
      language: "he",
    }).request!;
    expect(request.display_name).toBe(" נועם ");
    expect(request.age_months).toBe(36);
    expect(request).not.toHaveProperty("age");
    expect(request).not.toHaveProperty("narrative_pronouns");
  });
  it("requires one ordered target per page", () => {
    expect(
      prepareRequest({
        ...valid,
        education: true,
        pages: "3",
        targets: "Moon\nSun",
      }).errors.targets,
    ).toBeTruthy();
    const request = prepareRequest({
      ...valid,
      education: true,
      pages: "3",
      targets: "Moon\nStars\nSun",
    }).request!;
    expect(request.structure?.targets.map((target) => target.label)).toEqual([
      "Moon",
      "Stars",
      "Sun",
    ]);
  });
  it("requires unique letter targets for alphabet stories", () => {
    expect(
      prepareRequest({ ...valid, type: "alphabet" }).errors.targets,
    ).toBeTruthy();
    expect(
      prepareRequest({
        ...valid,
        type: "alphabet",
        pages: "2",
        targets: "A\nA",
      }).errors.targets,
    ).toBeTruthy();
    expect(
      prepareRequest({
        ...valid,
        type: "alphabet",
        pages: "2",
        targets: "א\nב",
      }).request?.structure?.targets.every(
        (target) => target.kind === "letter",
      ),
    ).toBe(true);
  });
  it("rejects bidi controls while accepting ordinary Hebrew and emoji", () => {
    expect(prepareRequest({ ...valid, name: "נועם 🌙" }).request).toBeDefined();
    expect(
      prepareRequest({ ...valid, name: "Noam\u202e" }).errors.name,
    ).toBeTruthy();
  });
});
