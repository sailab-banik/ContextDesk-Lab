// The three acceptance scenarios from PLAN.md, phrased as what a presenter
// needs to know to run each one.
export const SCENARIOS = [
  {
    message: "My API is slow again.",
    note: "Needs memory: “again” refers to an earlier report.",
  },
  {
    message: "What plan am I currently on?",
    note: "Needs retrieval. Turn retrieval off and the model can't answer.",
  },
  {
    message: "How do I reset my API key?",
    note: "Tests the cache. Ask it, then ask again in other words.",
  },
];
