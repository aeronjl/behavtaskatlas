/**
 * Story metadata, lifted out of the index page so the home can show a
 * cycling "story of the week" without duplicating the list, and so the
 * `/og/stories/<slug>.svg` endpoint can build per-story preview cards
 * from the same source.
 */

export interface Story {
  slug: string;
  href: string;
  title: string;
  lead: string;
  surface: string;
  tags: string[];
  /** Family ids whose activity should bias this story to the top of
   * the rotation. When a recently-added record's family appears here,
   * the story moves into the "recently active" featured slot. */
  familyIds: string[];
  speciesCount?: number;
  readMinutes: number;
  publishedAt: string; // YYYY-MM-DD
}

export const stories: Story[] = [
  {
    slug: "visual-contrast",
    href: "/stories/visual-contrast",
    title: "Visual contrast family map",
    lead:
      "The atlas's deepest family becomes a visual coverage map: notable papers, protocols, source-data depth, findings, slices, and model-selection ambiguity in one scan.",
    surface: "Timeline + coverage matrix + curve scan + small multiples",
    tags: ["visual contrast", "coverage", "family depth"],
    familyIds: ["family.visual-2afc-contrast"],
    speciesCount: 2,
    readMinutes: 8,
    publishedAt: "2026-04-30",
  },
  {
    slug: "rdm",
    href: "/stories/rdm",
    title: "Cross-species random-dot motion",
    lead:
      "Classic macaque RDM, human reaction-time RDM, and macaque confidence-wagering RDM live on one canonical signed-coherence axis. DDM fits give a single drift parameter to read off across species — and the spread is bigger than you'd expect.",
    surface: "Psychometric + chronometric + DDM cross-species fits",
    tags: ["random-dot motion", "DDM", "cross-species"],
    familyIds: ["family.random-dot-motion"],
    speciesCount: 2,
    readMinutes: 6,
    publishedAt: "2026-04-22",
  },
  {
    slug: "prior-shifts",
    href: "/stories/prior-shifts",
    title: "Prior conditioning shifts the psychometric, not the slope",
    lead:
      "IBL biases mouse choice via three-block left-prior schedules; Walsh 2024 biases human choice with trial-by-trial valid/neutral/invalid cues. Both predict μ moves and σ stays put. The atlas measures both directly.",
    surface: "Psychometric μ vs σ across mouse blocks and human cues",
    tags: ["prior conditioning", "psychometric", "cross-species"],
    familyIds: ["family.visual-2afc-contrast", "family.random-dot-motion"],
    speciesCount: 2,
    readMinutes: 7,
    publishedAt: "2026-04-18",
  },
];

export function storyBySlug(slug: string): Story | undefined {
  return stories.find((story) => story.slug === slug);
}

/**
 * Pick a story of the week deterministically: same week = same story.
 * The index walks forward as the calendar advances so a returning
 * visitor sees a new featured story without us having to maintain an
 * editorial calendar.
 */
export function storyOfTheWeek(now: Date = new Date()): Story {
  const startOfYear = Date.UTC(now.getUTCFullYear(), 0, 1);
  const ms = now.getTime() - startOfYear;
  const week = Math.floor(ms / (7 * 24 * 60 * 60 * 1000));
  const index = ((week % stories.length) + stories.length) % stories.length;
  return stories[index];
}

export interface FeaturedStory {
  story: Story;
  /** When the family was last extended, if the pick came from recent
   * activity (otherwise null and the story is the calendar default). */
  triggeredByFamily: { id: string; lastAdded: string } | null;
}

/**
 * Pick the story to feature on the homepage, biased toward whichever
 * task family has been most recently extended in the atlas. Falls back
 * to the calendar-week rotation when no recent activity matches a
 * story's `familyIds`.
 *
 * The `familyLastAdded` map is sourced from `derived/recent.json` —
 * its keys are family ids and values are ISO dates of the most recent
 * record (finding, paper, slice) that joined that family.
 */
export function featuredStory(
  familyLastAdded: Record<string, string>,
  now: Date = new Date(),
): FeaturedStory {
  const orderedFamilies = Object.entries(familyLastAdded)
    .filter(([, date]) => Boolean(date))
    .sort(([, a], [, b]) => b.localeCompare(a));

  for (const [familyId, lastAdded] of orderedFamilies) {
    const match = stories.find((s) => s.familyIds.includes(familyId));
    if (match) {
      return { story: match, triggeredByFamily: { id: familyId, lastAdded } };
    }
  }

  return { story: storyOfTheWeek(now), triggeredByFamily: null };
}
