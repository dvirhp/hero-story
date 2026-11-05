import type { StoryRequestV2, StoryService, StoryV2 } from "./contracts";
/** Local editorial samples. No quality approval, developmental assessment or real generation implied. */
export function makeSample(request: StoryRequestV2): StoryV2 {
  const name = request.display_name;
  const en = [
    [
      `${name} found a small golden seed beside the window.`,
      "Outside, the evening sky was turning the color of blueberries.",
    ],
    [
      "The seed gave a tiny rustle, like a leaf saying hello.",
      `${name} placed it in a little pot and opened the window to the breeze.`,
    ],
    [
      "A silver shoot curled up toward the stars.",
      `${name} watched a single leaf unfold, wide enough to catch a drop of moonlight.`,
    ],
    [
      "The moonlight rested on the leaf like a pearl.",
      `${name} listened as the garden grew quiet, one small sound at a time.`,
    ],
    [
      "A sleepy bird tucked its head beneath its wing.",
      `${name} left the golden seed a little water and whispered a wish for morning.`,
    ],
    [
      "By the window, the little leaf shone softly in the dark.",
      `${name} settled down to sleep. There would be something new to discover tomorrow.`,
    ],
  ];
  const he = [
    [
      `ליד החלון חיכה זרע זהוב קטן. השם ${name} היה כתוב על הפתק שלצידו.`,
      "בחוץ התחילו השמיים להיצבע בכחול עמוק.",
    ],
    [
      "הזרע רשרש בעדינות, כמו עלה שאומר שלום.",
      "עציץ קטן חיכה ליד החלון הפתוח, ומשב רוח נעים נכנס הביתה.",
    ],
    [
      "נבט כסוף הסתלסל לאט לעבר הכוכבים.",
      "עלה אחד נפתח, רחב מספיק כדי לתפוס טיפה של אור ירח.",
    ],
    [
      "אור הירח נח על העלה כמו פנינה קטנה.",
      "הגינה נעשתה שקטה, צליל קטן אחד בכל פעם.",
    ],
    [
      "ציפור מנומנמת הסתירה את ראשה מתחת לכנף.",
      "ליד העציץ חיכו מעט מים ומשאלה קטנה לבוקר.",
    ],
    [
      "ליד החלון, העלה הקטן האיר ברכות בחושך.",
      `לילה טוב, ${name}. מחר יחכה כאן משהו חדש לגלות.`,
    ],
  ];
  return {
    schema_version: "2",
    title:
      request.requested_title ??
      (request.language === "he"
        ? "הזרע ששמר אור ירח"
        : "The seed that held the moonlight"),
    language: request.language,
    direction: request.language === "he" ? "rtl" : "ltr",
    profile_id: "demo",
    profile_version: "editorial-sample-v1",
    page_count: request.page_count,
    pages: Array.from({ length: request.page_count }, (_, i) => ({
      page_id: `sample-${i + 1}`,
      page_number: i + 1,
      target_id: request.structure?.targets[i]?.target_id ?? null,
      sentence_units: (request.language === "he" ? he : en)[i % 6]!,
    })),
  };
}
export function createMockStoryService(delay = 1800): StoryService {
  return {
    generate(request, signal) {
      return new Promise((resolve, reject) => {
        if (signal.aborted) {
          reject(new DOMException("Cancelled", "AbortError"));
          return;
        }
        const abort = () => {
          clearTimeout(timer);
          reject(new DOMException("Cancelled", "AbortError"));
        };
        const timer = setTimeout(() => {
          signal.removeEventListener("abort", abort);
          resolve(makeSample(request));
        }, delay);
        signal.addEventListener("abort", abort, { once: true });
      });
    },
  };
}
