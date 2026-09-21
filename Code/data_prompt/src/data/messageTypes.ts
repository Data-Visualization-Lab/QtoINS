
export interface BaseMessage {
  id: number;
  role: "system" | "user";
  text: string;
}


export interface FuzzyTextMessage {
  id: number;
  role: "fuzzy_text";
  text: string;
  keyName: string;
  category: "no_scientific_basis" | "multiple_column";
  solution: string | string[] | { Summary: string; Recommend: string };
  single_select?: boolean;
  summary?: string;
  userInput?: string;
  submitted?: boolean;
  userSelectedIndices?: number[];
  fuzzyResult?: {
    level: "fully_resolvable" | "completely_unresolvable";
    solution: string[];
  };
}




// src/data/messageTypes.ts
export interface FuzzyStringMessage {
  id: number;
  role: "fuzzy_string";
  keyName?: string;
  columnname?: string;
  category?: "multiple_string";
  solution?: string[];
  userSelectedIndices?: number[];
  submitted?: boolean;
  text: string;
  backendKey?: string;

  submitting?: boolean;
}


export interface FollowupActionMessage {
  id: number;
  role: "followup_action";
  text: string;
  finalQuestion: string;
  initialFuzzyRecommendations?: Record<string, unknown>;
  resolvedFinalQuestion?: string;
  selectedByUuid?: Record<string, string[]>;
  submitted?: boolean;
  submitting?: boolean;
}

export interface FollowupActionPayload {
  finalQuestion: string;
  selectedByUuid: Record<string, string[]>;
}


export type Message =
  | BaseMessage
  | FuzzyTextMessage
  | FuzzyStringMessage
  | FollowupActionMessage;
