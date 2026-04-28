export type ComparisonSpec = {
  id: string;
  question: string;
  framing: string;
  finding_ids: string[];
  color_by: "paper" | "condition" | "curve_type";
  hint: string;
};

export const COMPARISONS: ComparisonSpec[] = [
  {
    id: "macaque-vs-human-rdm",
    question: "How do macaque and human random-dot motion psychometrics compare?",
    framing:
      "Roitman & Shadlen 2002 (two macaques) and Palmer-Huk-Shadlen 2005 (six human observers) both ran the same signed motion coherence 2AFC at processed-trial level. They use the same canonical axis but different species and different report modalities (saccade vs button-press), so a slope difference is a candidate signature of perceptual sensitivity at the species level.",
    finding_ids: [
      "finding.roitman-shadlen-2002.psychometric",
      "finding.palmer-huk-shadlen-2005.psychometric",
    ],
    color_by: "paper",
    hint: "Larger σ = shallower slope = lower discriminability. Compare Δσ.",
  },
  {
    id: "rdm-chronometric-species",
    question: "Do humans and macaques show comparable RT-vs-coherence chronometrics on RDM?",
    framing:
      "Both papers also report median response time as a function of absolute coherence. The chronometric speed-accuracy tradeoff has been used to argue for shared bounded-accumulation dynamics across species, but the absolute time scales differ.",
    finding_ids: [
      "finding.roitman-shadlen-2002.chronometric",
      "finding.palmer-huk-shadlen-2005.chronometric",
    ],
    color_by: "paper",
    hint: "RTs are in seconds; lower curves are faster. Pre-baked logistic fits do not apply here (curve type is chronometric).",
  },
  {
    id: "ibl-prior-blocks",
    question: "How does prior probability shift the IBL psychometric in mice?",
    framing:
      "The IBL trainingChoiceWorld biased variant cycles through three blocks of leftward prior probability (0.2 / 0.5 / 0.8). A bias-shift across blocks is the textbook signature of prior integration; the slope (σ) should remain stable.",
    finding_ids: [
      "finding.ibl-2021-standardized.psychometric.p_left-0.2",
      "finding.ibl-2021-standardized.psychometric.p_left-0.5",
      "finding.ibl-2021-standardized.psychometric.p_left-0.8",
    ],
    color_by: "condition",
    hint: "Δμ across blocks measures the bias shift in % contrast units.",
  },
  {
    id: "walsh-prior-cue",
    question: "Do prior-probability cues bias contrast discrimination in humans?",
    framing:
      "Walsh et al. 2024 manipulate trial-by-trial prior cues (valid / neutral / invalid). The prediction is that valid cues produce a bias toward the cued side without changing slope, and invalid cues produce the opposite shift.",
    finding_ids: [
      "finding.walsh-2024-prior-cue.psychometric.cue-invalid",
      "finding.walsh-2024-prior-cue.psychometric.cue-neutral",
      "finding.walsh-2024-prior-cue.psychometric.cue-valid",
    ],
    color_by: "condition",
    hint: "Compare Δμ between valid and invalid; if cueing is symmetric, |valid − neutral| ≈ |invalid − neutral|.",
  },
];
