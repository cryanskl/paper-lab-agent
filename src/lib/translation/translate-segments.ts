// Translation pipeline wrapper.
//
// Phase 3 keeps the fake translation as the default per the harness
// rules. The wrapper exposes a single function that turns a list of
// parsed segments into a translated list by calling the provided
// `translate` function for each english field. The default caller is
// the fake model adapter's `translate(english) => english` passthrough.
//
// Real (Phase 4) providers will swap the `translate` function. This
// module is intentionally pure — no I/O, no DB, no model import — so
// the unit tests can drive it without the rest of the app.

import type { PaperSegment } from "@/types/domain";

export type SegmentTranslator = (english: string) => string;

export interface TranslateSegmentsOptions {
  /** If true, the input is left untouched and `chinese` is left as
   *  the segment's own value (placeholder mode). Useful when the
   *  caller has not approved any translation provider. */
  leaveAsIs?: boolean;
}

export function translateSegments(
  segments: readonly PaperSegment[],
  translate: SegmentTranslator,
  options: TranslateSegmentsOptions = {},
): PaperSegment[] {
  if (options.leaveAsIs) {
    return segments.map((s) => ({ ...s }));
  }
  return segments.map((s) => {
    if (typeof s.english !== "string" || s.english === "") {
      return { ...s, chinese: s.chinese ?? "" };
    }
    let translated: string;
    try {
      translated = translate(s.english);
    } catch (err) {
      // A misbehaving translator must not corrupt the rest of the
      // pipeline; fall back to the existing chinese value.
      const message = err instanceof Error ? err.message : String(err);
      return { ...s, chinese: `${s.chinese}`.length > 0 ? s.chinese : `__translate_error:${message}` };
    }
    return { ...s, chinese: translated };
  });
}

export function fakeTranslationPlaceholder(english: string): string {
  // Explicit, honest placeholder. We do NOT pretend to translate.
  // Reader surfaces this as "(中文待翻译)" so users are not misled.
  if (english.trim() === "") return "";
  return "";
}
