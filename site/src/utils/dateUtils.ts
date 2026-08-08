import holidaysData from "../data/holidays-2026.json";

const MONTHS_RU = [
  "ЯНВАРЯ",
  "ФЕВРАЛЯ",
  "МАРТА",
  "АПРЕЛЯ",
  "МАЯ",
  "ИЮНЯ",
  "ИЮЛЯ",
  "АВГУСТА",
  "СЕНТЯБРЯ",
  "ОКТЯБРЯ",
  "НОЯБРЯ",
  "ДЕКАБРЯ",
];

const MONTHS_NOMINATIVE_RU = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];

const DAYS_OF_WEEK_RU = [
  "ВОСКРЕСЕНЬЕ",
  "ПОНЕДЕЛЬНИК",
  "ВТОРНИК",
  "СРЕДА",
  "ЧЕТВЕРГ",
  "ПЯТНИЦА",
  "СУББОТА",
];

export function parseDateString(dateStr: string): Date {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDateString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function getWeekNumber(d: Date): number {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

export function isRedDate(dateStr: string): boolean {
  const dt = parseDateString(dateStr);
  const dayOfWeek = dt.getDay(); // 0 is Sunday, 6 is Saturday
  const year = String(dt.getFullYear());

  const yearData = (holidaysData as Record<string, { holidays: string[]; workdays: string[] }>)[year];
  if (yearData) {
    if (yearData.workdays.includes(dateStr)) return false;
    if (yearData.holidays.includes(dateStr)) return true;
  }

  return dayOfWeek === 0 || dayOfWeek === 6;
}

export function getFormattedHeaderDate(dateStr: string) {
  const dt = parseDateString(dateStr);
  const dayNum = dt.getDate();
  const monthName = MONTHS_RU[dt.getMonth()];
  const year = dt.getFullYear();
  const dayOfWeekName = DAYS_OF_WEEK_RU[dt.getDay()];
  const weekNum = getWeekNumber(dt);
  const red = isRedDate(dateStr);

  return {
    dayNum,
    monthName,
    year,
    dayOfWeekName,
    weekNum,
    isRed: red,
  };
}

export function getMonthNameNominative(monthIndex: number): string {
  return MONTHS_NOMINATIVE_RU[monthIndex] || "";
}

export function getMskTodayDateString(): string {
  // Return current date in MSK timezone
  const now = new Date();
  const mskTime = new Date(now.toLocaleString("en-US", { timeZone: "Europe/Moscow" }));
  return formatDateString(mskTime);
}
