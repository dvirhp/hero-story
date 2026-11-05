import type { Language, StoryType } from "../api/contracts";
import type { Art, Book } from "../domain/book";
import { newId } from "../domain/book";
import type { ProductCopy } from "../i18n/product";
import { characterFromValues,characterOptions,defaultCharacter,fullCharacterSchema } from '../personalization/character';
import type { CharacterSchema } from '../personalization/character';
export type Localized = Record<Language, string>;
export type Category =
  | "adventure"
  | "bedtime"
  | "educational"
  | "superhero"
  | "family";
export type AgeGroup = "babies" | "toddlers" | "preschool" | "older";
type FieldBase = {
  id: string;
  label: keyof ProductCopy;
  required: boolean;
  default: string;
};
export type TemplateField = FieldBase &
  (
    | { type: "text" | "textarea"; maxLength: number }
    | { type: "select"; options: { value: string; label: keyof ProductCopy }[] }
  );
export interface BookTemplate {
  id: string;
  version: "demo-1";
  title: Localized;
  personalTitle: Localized;
  description: Localized;
  art: Art;
  category: Category;
  ages: AgeGroup[];
  languages: Language[];
  color: string;
  storyType: StoryType;
  fields: TemplateField[];
  character?: CharacterSchema;
  pages: Record<Language, string[]>;
}
const name: TemplateField = {
  id: "name",
  label: "childName",
  type: "text",
  required: true,
  default: "",
  maxLength: 40,
};
const dedication: TemplateField = {
  id: "dedication",
  label: "dedication",
  type: "textarea",
  required: false,
  default: "",
  maxLength: 240,
};
const color: TemplateField = {
  id: "color",
  label: "coverColor",
  type: "select",
  required: true,
  default: "#b7cfc1",
  options: [
    { value: "#b7cfc1", label: "teal" },
    { value: "#e9a08c", label: "coral" },
    { value: "#c9c0e0", label: "lavender" },
    { value: "#f3d294", label: "yellow" },
  ],
};
const companion: TemplateField = {
  id: "companion",
  label: "companion",
  type: "select",
  required: true,
  default: "fox",
  options: [
    { value: "fox", label: "fox" },
    { value: "rabbit", label: "rabbit" },
  ],
};
export const catalog: BookTemplate[] = [
  {
    id: "sky-whale",
    version: "demo-1",
    title: { en: "The Sky-Whale Express", he: "רכבת לווייתני השמיים" },
    personalTitle: {
      en: "{{name}} & the Sky-Whale Express",
      he: "{{name}} ולווייתן השמיים",
    },
    description: {
      en: "All aboard a very unusual adventure. A gentle whale, a pocketful of clouds, and a little explorer with somewhere wonderful to go.",
      he: "עולים להרפתקה מיוחדת. לווייתן עדין, כיס מלא עננים ומסע למקום נפלא.",
    },
    art: "whale",
    category: "adventure",
    ages: ["preschool", "older"],
    languages: ["en", "he"],
    color: "#e9a08c",
    storyType: "adventure",
    fields: [name, companion, dedication, color],
    pages: {
      en: [
        "A cloud drifted down to the window. “Your ride is here, {{name}},” whispered the wind.",
        "A great blue whale floated outside. A little {{companion}} was already waiting on its back.",
        "Together, they sailed past islands of cloud. Below them, the rivers looked like silver ribbons.",
        "“What is at the edge of the sky?” asked {{name}}. The whale answered with a gentle, rumbling song.",
        "At the edge was a garden of stars, just waking up. Every star hummed a different note.",
        "The whale carried everyone home before bedtime. A little starlight stayed in the window, waiting for another adventure.",
      ],
      he: [
        "ענן קטן ירד אל החלון. ״ההסעה שלך כאן, {{name}}״, לחשה הרוח.",
        "לווייתן כחול ריחף בחוץ. על גבו כבר חיכה {{companion}} קטן.",
        "יחד שטו כולם בין איים של עננים. למטה נראו הנהרות כמו סרטי כסף.",
        "״מה יש בקצה השמיים?״ נשמעה שאלה. הלווייתן ענה בשיר עמוק ועדין.",
        "בקצה השמיים הייתה גינת כוכבים מתעוררת. לכל כוכב היה צליל משלו.",
        "לפני השינה חזרו כולם הביתה. בחלון נשאר קצת אור כוכבים, מחכה להרפתקה הבאה.",
      ],
    },
  },
  {
    id: "moon-fox",
    version: "demo-1",
    title: { en: "Goodnight, Little Fox", he: "לילה טוב, שועל קטן" },
    personalTitle: { en: "Goodnight, {{name}}", he: "לילה טוב, {{name}}" },
    description: {
      en: "Follow a sleepy fox through the last little sounds of the day. A soft, unhurried story for a shared goodnight.",
      he: "מקשיבים עם שועל מנומנם לצלילים האחרונים של היום. סיפור עדין לרגע של לילה טוב.",
    },
    art: "moon",
    category: "bedtime",
    ages: ["babies", "toddlers", "preschool"],
    languages: ["en", "he"],
    color: "#414271",
    storyType: "bedtime",
    fields: [name, dedication, color],
    pages: {
      en: [
        "The day folded up its golden light. “Goodnight, {{name}},” said the little fox.",
        "Goodnight to the leaves, whispering up in the tree. Goodnight to the birds, as quiet as can be.",
        "A cloud pulled a blanket over one bright star. The moon kept a little light on, not very far.",
        "The fox curled into a warm, soft ring. The garden had finished its evening song.",
        "One gentle breath. One quiet sigh. A hundred tiny stars in the blueberry sky.",
        "Goodnight, {{name}}. The world will be here when morning comes.",
      ],
      he: [
        "היום קיפל את אורו הזהוב. ״לילה טוב, {{name}}״, אמר השועל הקטן.",
        "לילה טוב לעלים שלוחשים על העץ. לילה טוב לציפורים שנחות בקן.",
        "ענן כיסה כוכב אחד בשמיכה. הירח השאיר אור קטן, לא רחוק.",
        "השועל התכרבל בעיגול חמים ורך. הגינה סיימה את שיר הערב שלה.",
        "נשימה עדינה אחת. אנחה שקטה אחת. מאה כוכבים קטנים בשמיים כחולים.",
        "לילה טוב, {{name}}. העולם יחכה כאן גם בבוקר.",
      ],
    },
  },
  {
    id: "alphabet-garden",
    version: "demo-1",
    title: { en: "The Letter Garden", he: "גינת האותיות" },
    personalTitle: {
      en: "{{name}}’s Letter Garden",
      he: "גינת האותיות של {{name}}",
    },
    description: {
      en: "Letters are growing in the garden! An original little sample about noticing shapes, sounds and new possibilities.",
      he: "אותיות צומחות בגינה! דוגמה מקורית על צורות, צלילים ואפשרויות חדשות.",
    },
    art: "alphabet",
    category: "educational",
    ages: ["toddlers", "preschool"],
    languages: ["en", "he"],
    color: "#a9d3c3",
    storyType: "educational",
    fields: [name, color],
    pages: {
      en: [
        "“Welcome, {{name}},” chirped a tiny bird. “Something unusual is growing today!”",
        "An A stood beside an apple tree. Its branches stretched up like a little green tent.",
        "A B bounced by a bed of blue flowers. A bee hummed hello from the blossoms.",
        "A C curled round like the moon. The bird made a nest in its quiet curve.",
        "{{name}} found letters in every corner. Some stood tall. Some curled. Some reached out to hold hands.",
        "The garden gate closed with a gentle click. Tomorrow there would be more shapes to discover.",
      ],
      he: [
        "״ברוכים הבאים, {{name}}״, צייצה ציפור קטנה. ״משהו מיוחד צומח כאן היום!״",
        "ליד עץ קטן עמדה האות א. על הענפים חיכו אגסים.",
        "האות ב נחה ליד בית קטן. בדלת חיכה ברווז שאמר שלום.",
        "האות ג התכופפה ליד גינה. גלגל קטן התגלגל בשביל.",
        "בכל פינה חיכתה צורה חדשה. חלקן גבוהות, חלקן מתעגלות וחלקן מושיטות יד.",
        "שער הגינה נסגר בנקישה עדינה. מחר יחכו עוד צורות לגלות.",
      ],
    },
  },
  {
    id: "small-hero",
    version: "demo-1",
    title: { en: "A Very Small Superhero", he: "גיבור־על קטן מאוד" },
    personalTitle: {
      en: "{{name}}’s Everyday Superpower",
      he: "כוח הקסם של {{name}}",
    },
    description: {
      en: "Some heroes fly. Others notice when a friend needs a hand. A bright story about the little things that matter.",
      he: "יש גיבורים שעפים, ויש כאלה שרואים כשמישהו צריך עזרה. סיפור בהיר על הדברים הקטנים שחשובים.",
    },
    art: "hero",
    category: "superhero",
    ages: ["preschool", "older"],
    languages: ["en", "he"],
    color: "#91c7d7",
    storyType: "adventure",
    fields: [
      name,
      {
        id: "outfit",
        label: "appearance",
        type: "select",
        required: true,
        default: "raincoat",
        options: [
          { value: "raincoat", label: "raincoat" },
          { value: "striped", label: "striped" },
        ],
      },
      dedication,
    ],
    pages: {
      en: [
        "A yellow cape waited by the door. Today was a good day to be {{name}}.",
        "Outside, the city was already busy. A little bird had lost the way back to its tree.",
        "{{name}} stopped to listen. Sometimes a superhero’s best power is making a little room for someone else.",
        "Together, they followed the song of another bird. It came from a tree at the end of the street.",
        "The little bird fluttered home. The whole tree seemed to sing thank you.",
        "There was no medal at the end of the day. Just a warm feeling, and a cape ready for tomorrow.",
      ],
      he: [
        "גלימה צהובה חיכתה ליד הדלת. יום חדש התחיל בשביל {{name}}.",
        "בחוץ העיר כבר הייתה עסוקה. ציפור קטנה איבדה את הדרך לעץ שלה.",
        "לרגע היה שקט של הקשבה. לפעמים הכוח הכי טוב הוא לפנות קצת מקום למישהו אחר.",
        "יחד עקבו כולם אחרי שיר של ציפור. הוא הגיע מעץ בקצה הרחוב.",
        "הציפור הקטנה רפרפה הביתה. כל העץ כאילו שר תודה.",
        "בסוף היום לא הייתה מדליה. רק הרגשה חמימה וגלימה שמחכה למחר.",
      ],
    },
  },
  {
    id: "bear-hug",
    version: "demo-1",
    title: { en: "A Hug as Big as Home", he: "חיבוק גדול כמו בית" },
    personalTitle: { en: "A Hug for {{name}}", he: "חיבוק בשביל {{name}}" },
    description: {
      en: "How big can a hug be? Follow two gentle bears on a little journey through all the things that feel like home.",
      he: "כמה גדול יכול להיות חיבוק? שני דובים עדינים מגלים את הדברים הקטנים שמרגישים כמו בית.",
    },
    art: "family",
    category: "family",
    ages: ["babies", "toddlers", "preschool"],
    languages: ["en", "he"],
    color: "#f3d29d",
    storyType: "general",
    fields: [name, dedication],
    pages: {
      en: [
        "“How big is a hug?” wondered {{name}}. A little bear opened both arms wide.",
        "“As big as a tree?” The tree rustled all its leaves, as if to say, a little bigger.",
        "“As big as a house?” Warm light glowed behind a window. A kettle sang a little song.",
        "“As big as the sky?” A cloud drifted softly over the two bears.",
        "The little bear settled into a familiar cuddle. No measuring was needed at all.",
        "A hug was exactly big enough to feel like home. And there was always room for {{name}}.",
      ],
      he: [
        "״כמה גדול חיבוק?״ הייתה השאלה של {{name}}. דוב קטן פתח את שתי זרועותיו.",
        "״גדול כמו עץ?״ העץ רשרש בכל עליו, כאילו אמר: קצת יותר.",
        "״גדול כמו בית?״ אור חם זהר בחלון. קומקום שר שיר קטן.",
        "״גדול כמו שמיים?״ ענן חלף ברכות מעל שני הדובים.",
        "הדוב הקטן התכרבל בחיבוק מוכר. לא היה צריך למדוד בכלל.",
        "החיבוק היה בדיוק בגודל שמרגיש כמו בית. ותמיד היה בו מקום גם בשביל {{name}}.",
      ],
    },
  },
  {
    id: "moon-garden",
    version: "demo-1",
    title: { en: "The Moonlight Garden", he: "גינת אור הירח" },
    personalTitle: {
      en: "{{name}}’s Moonlight Garden",
      he: "גינת הירח של {{name}}",
    },
    description: {
      en: "A door in a familiar garden opens onto something new. A gentle night-time discovery, with a curious companion.",
      he: "דלת בגינה מוכרת נפתחת אל משהו חדש. גילוי לילי ועדין, עם חבר סקרן.",
    },
    art: "garden",
    category: "adventure",
    ages: ["toddlers", "preschool", "older"],
    languages: ["en", "he"],
    color: "#b7cfc1",
    storyType: "general",
    fields: [name, companion, dedication],
    pages: {
      en: [
        "In the quiet garden, {{name}} found a door no bigger than a leaf.",
        "A little {{companion}} sat beside it. The door opened with the softest creak.",
        "Behind it was a garden made of moonlight. Every flower held a tiny silver drop.",
        "{{name}} followed the winding path, listening to the rustle of leaves.",
        "At the end was a small, golden seed. A little gift to take home.",
        "Now a new leaf grows beside the window. It shines just a little when the moon comes out.",
      ],
      he: [
        "בגינה השקטה חיכתה דלת קטנה, לא גדולה מעלה. על הפתק היה כתוב: בשביל {{name}}.",
        "לידה ישב {{companion}} קטן. הדלת נפתחה בחריקה הכי עדינה.",
        "מאחוריה הייתה גינה של אור ירח. בכל פרח נחה טיפה כסופה קטנה.",
        "השביל התפתל בין העלים המרשרשים. בכל צעד חיכה צליל חדש.",
        "בקצה השביל נח זרע זהוב קטן. מתנה שאפשר לקחת הביתה.",
        "עכשיו צומח עלה חדש ליד החלון. כשהירח יוצא, הוא זוהר קצת.",
      ],
    },
  },
];
for(const template of catalog){
 if(['sky-whale','small-hero'].includes(template.id))template.character=fullCharacterSchema;
 if(template.id==='alphabet-garden')template.character={version:'1',fields:['presentation','skin','hair','hairstyle','eye','glasses','freckles']};
 if(template.id==='moon-fox')template.character={version:'1',fields:['skin','hair','hairstyle','glasses']};
}
export const categories: Category[] = [
  "adventure",
  "bedtime",
  "educational",
  "superhero",
  "family",
];
export const ages: AgeGroup[] = ["babies", "toddlers", "preschool", "older"];
export const ageLabels: Record<AgeGroup, keyof ProductCopy> = {
  babies: "newbornAge",
  toddlers: "toddlerAge",
  preschool: "preschoolAge",
  older: "olderAge",
};
export function templateDefaults(
  template: BookTemplate,
): Record<string, string> {
  return {...Object.fromEntries(
    template.fields.map((field) => [field.id, field.default]),
  ),...Object.fromEntries((template.character?.fields??[]).map(key=>[`character_${key}`,String(defaultCharacter[key])]))};
}
export function templateErrors(
  template: BookTemplate,
  values: Record<string, string>,
): Record<string, "required" | "tooLong"> {
  const errors: Record<string, "required" | "tooLong"> = {};
  const allowed=new Set([...template.fields.map(field=>field.id),...(template.character?.fields??[]).map(key=>`character_${key}`)]);
  for(const key of Object.keys(values))if(!allowed.has(key))errors[key]='required';
  for(const key of template.character?.fields??[]){const value=values[`character_${key}`];if(value!==undefined&&!(key==='glasses'||key==='freckles'?['true','false'].includes(value):characterOptions[key]?.some(option=>option.value===value)))errors[`character_${key}`]='required';}
  for (const field of template.fields) {
    const value = values[field.id] ?? "";
    if (
      (field.required && !value.trim()) ||
      (field.type === "select" &&
        !field.options.some((option) => option.value === value))
    )
      errors[field.id] = "required";
    else if (
      (field.type !== "select" && Array.from(value).length > field.maxLength) ||
      /[\u0000-\u0008\u202a-\u202e\u2066-\u2069]/u.test(value)
    )
      errors[field.id] = "tooLong";
  }
  return errors;
}
export function personalizeTemplate(
  template: BookTemplate,
  values: Record<string, string>,
  language: Language,
  id: string = newId(),
): Book {
  const name = values.name || (language === "he" ? "נועם" : "Alex");
  const companion =
    values.companion === "rabbit"
      ? language === "he"
        ? "ארנב"
        : "rabbit"
      : language === "he"
        ? "שועל"
        : "fox";
  // A single pass preserves literal user text containing template-like markers.
  const replace = (text: string) =>
    text.replace(/\{\{(name|companion)\}\}/g, (_match, key: string) =>
      key === "name" ? name : companion,
    );
  const now = new Date().toISOString();
  const character=template.character?characterFromValues(values,template.character):undefined;
  const art: Art =
    template.id === "small-hero" && values.outfit === "striped"
      ? "hero-striped"
      : template.art;
  const dedication = values.dedication?.trim() ? values.dedication : "";
  const text = [...template.pages[language]];
  if (dedication) text.unshift(dedication);
  if (template.id === "small-hero")
    text[dedication ? 1 : 0] =
      language === "he"
        ? `ליד הדלת חיכו ${values.outfit === "striped" ? "חולצה מפוספסת" : "מעיל גשם צהוב"} וגלימה. יום חדש התחיל בשביל {{name}}.`
        : `A ${values.outfit === "striped" ? "striped sweater" : "sunshine raincoat"} and a cape waited by the door. Today was a good day to be {{name}}.`;
  return {
    schemaVersion: "1",
    id,
    method: "TEMPLATE_BASED",
    title: replace(template.personalTitle[language]),
    language,
    childName: name,
    character,
    createdAt: now,
    updatedAt: now,
    status: "ready",
    cover: art,
    coverColor: values.color || template.color,
    demo: true,
    template: {
      id: template.id,
      version: template.version,
      values: { ...values },
    },
    pages: text.map((line, i) => ({
      pageId: `${id}-page-${i + 1}`,
      pageNumber: i + 1,
      // Dedication is literal adult-authored text, never template code.
      sentenceUnits: [dedication && i === 0 ? line : replace(line)],
      illustration: art,
      character,
      layout: "split",
      background: "cream",
    })),
  };
}
export function sampleBook(template: BookTemplate, language: Language): Book {
  return personalizeTemplate(
    template,
    {
      ...templateDefaults(template),
      name: language === "he" ? "נועם" : "Alex",
    },
    language,
    `sample-${template.id}-${language}`,
  );
}
