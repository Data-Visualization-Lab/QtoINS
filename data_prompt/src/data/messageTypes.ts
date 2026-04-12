/** 基础消息类型 */
export interface BaseMessage {
  id: number;
  role: "system" | "user";
  text: string;
}

/**
 * 当后端返回 textfuzzy=true 时，
 * 每个 fuzzy_text 消息对应一个模糊概念（fuzzy concept）。
 */
export interface FuzzyTextMessage {
  id: number;
  role: "fuzzy_text";
  text: string;
  keyName: string;
  category: "no_scientific_basis" | "multiple_column";
  solution: string | string[] | { Summary: string; Recommend: string };
  summary?: string;        // 新增字段，用于展示 Summary
  userInput?: string;      // 用于编辑 Recommend
  submitted?: boolean;
  userSelectedIndices?: number[];
  fuzzyResult?: {
    level: "fully_resolvable" | "completely_unresolvable";
    solution: string[];
  };
}


/** 当后端返回 stringfuzzy=true 时的消息 */
/* 为了支持多选，我们扩展了该接口 */
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
  // 新增字段，用于表示提交中状态
  submitting?: boolean;
}

/** 触发 /api/runfollowups 的确认卡片消息 */
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

/** 统一的消息类型 */
export type Message =
  | BaseMessage
  | FuzzyTextMessage
  | FuzzyStringMessage
  | FollowupActionMessage;
