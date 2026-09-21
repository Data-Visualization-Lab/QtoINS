import React, { useEffect, useMemo, useState } from "react";
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  TextField,
  Autocomplete,
  Chip,
  Tooltip,
} from "@mui/material";
import {
  FollowupActionMessage,
  FollowupActionPayload,
} from "../data/messageTypes";

interface FollowupActionFormProps {
  message: FollowupActionMessage;
  handleFollowupActionSubmit: (
    msgId: number,
    payload?: FollowupActionPayload
  ) => void;
}

type RecommendationSpec =
  | { kind: "options"; options: string[]; single_select?: boolean }
  | { kind: "range"; min: string; max: string }
  | { kind: "text"; suggestion: string }
  | { kind: "none" };

type QuestionPart =
  | { type: "text"; text: string }
  | {
      type: "token";
      uuid: string;
      occurrence: number;
      recommendation: RecommendationSpec;
    };

const UUID_PATTERN = /\[uuid:([0-9a-fA-F-]{36})\]/g;
const HAS_ALNUM = /[A-Za-z0-9]/;

const parseRangeString = (raw: string): { min: string; max: string } | null => {
  const fromTo = raw.match(
    /from\s+(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)/i
  );
  if (fromTo) {
    return { min: fromTo[1], max: fromTo[2] };
  }

  const generic = raw.match(/(-?\d+(?:\.\d+)?)\s*(?:to|-|~|–|—)\s*(-?\d+(?:\.\d+)?)/i);
  if (generic) {
    return { min: generic[1], max: generic[2] };
  }

  return null;
};

const flattenUnknownToStrings = (value: unknown): string[] => {
  if (value === null || value === undefined) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.flatMap((item) => flattenUnknownToStrings(item));
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? [trimmed] : [];
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return [String(value)];
  }

  return [];
};

const buildRecommendationSpec = (value: unknown): RecommendationSpec => {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const detail = value as { options?: unknown; single_select?: boolean };
    if (Array.isArray(detail.options)) {
      const options = Array.from(new Set(flattenUnknownToStrings(detail.options)));
      return options.length > 0
        ? { kind: "options", options, single_select: detail.single_select === true }
        : { kind: "none" };
    }
  }

  if (typeof value === "string") {
    const range = parseRangeString(value);
    if (range) {
      return { kind: "range", min: range.min, max: range.max };
    }
    return { kind: "text", suggestion: value.trim() };
  }

  if (Array.isArray(value)) {
    const flattened = Array.from(new Set(flattenUnknownToStrings(value)));
    if (flattened.length === 0) {
      return { kind: "none" };
    }

    if (flattened.length === 1) {
      const range = parseRangeString(flattened[0]);
      if (range) {
        return { kind: "range", min: range.min, max: range.max };
      }
    }

    return { kind: "options", options: flattened };
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return { kind: "text", suggestion: String(value) };
  }

  return { kind: "none" };
};

const recommendationDisplayValue = (value: string): string =>
  value.replace(/_/g, " ").trim();

const buildDisplayOptions = (recommendation: RecommendationSpec): string[] => {
  if (recommendation.kind !== "options") {
    return [];
  }
  return Array.from(
    new Set(
      recommendation.options
        .map((opt) => recommendationDisplayValue(opt))
        .filter((opt) => opt.length > 0)
    )
  );
};

const tokenStateKey = (uuid: string, occurrence: number): string =>
  `${uuid}::${occurrence}`;

const normalizeOptionKey = (value: string): string =>
  value
    .trim()
    .replace(/^["'`]+|["'`]+$/g, "")
    .replace(/^the\s+/i, "")
    .replace(/\s+/g, " ")
    .toLowerCase();

const parseOptionSelectionFromValue = (
  rawValue: string,
  options: string[]
): string[] => {
  const normalizedMap = new Map<string, string>();
  options.forEach((opt) => normalizedMap.set(normalizeOptionKey(opt), opt));

  const raw = rawValue.trim();
  if (!raw) {
    return [];
  }

  const direct = normalizedMap.get(normalizeOptionKey(raw));
  if (direct) {
    return [direct];
  }

  const pieces = raw
    .split(/\s*,\s*|\s+and\s+/i)
    .map((s) => s.trim())
    .filter(Boolean);
  const selected = Array.from(
    new Set(
      pieces
        .map((piece) => normalizedMap.get(normalizeOptionKey(piece)))
        .filter((v): v is string => !!v)
    )
  );
  return selected;
};

const escapeRegExp = (value: string): string =>
  value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const matchWithRecommendation = (
  core: string,
  recommendation: RecommendationSpec
): { prefix: string; anchor: string; suffix?: string } | null => {
  if (recommendation.kind === "options") {
    const options = buildDisplayOptions(recommendation);
    const optionStartPositions = Array.from(
      new Set(
        options.flatMap((option) => {
          if (!option) {
            return [];
          }
          const pattern = new RegExp(
            `(^|[^A-Za-z0-9_])(${escapeRegExp(option)})(?=$|[^A-Za-z0-9_])`,
            "ig"
          );
          const starts: number[] = [];
          let result: RegExpExecArray | null;
          while ((result = pattern.exec(core)) !== null) {
            starts.push(result.index + (result[1]?.length ?? 0));
          }
          return starts;
        })
      )
    ).sort((a, b) => a - b);

    if (recommendation.single_select && optionStartPositions.length === 1) {
      const start = optionStartPositions[0];
      const candidate = [...options].sort((a, b) => b.length - a.length).find(
        (option) => core.slice(start).toLowerCase().startsWith(option.toLowerCase())
      );
      if (candidate) {
        return {
          prefix: core.slice(0, start),
          anchor: candidate,
          suffix: core.slice(start + candidate.length),
        };
      }
    }

    if (optionStartPositions.length >= 2) {
      const start = optionStartPositions[0];
      return {
        prefix: core.slice(0, start),
        anchor: core.slice(start),
      };
    }

    const candidates = Array.from(
      new Set(
        recommendation.options
          .map((opt) => recommendationDisplayValue(opt))
          .filter((opt) => opt.length > 0)
      )
    ).sort((a, b) => b.length - a.length);

    for (const candidate of candidates) {
      if (core.toLowerCase().endsWith(candidate.toLowerCase())) {
        const start = core.length - candidate.length;
        return {
          prefix: core.slice(0, start),
          anchor: core.slice(start),
        };
      }
    }
    return null;
  }

  if (recommendation.kind === "range") {
    const candidates = [recommendation.min, recommendation.max];
    for (const candidate of candidates) {
      if (core.toLowerCase().endsWith(candidate.toLowerCase())) {
        const start = core.length - candidate.length;
        return {
          prefix: core.slice(0, start),
          anchor: core.slice(start),
        };
      }
    }
    return null;
  }

  if (recommendation.kind === "text") {
    const candidate = recommendationDisplayValue(recommendation.suggestion);
    if (candidate && core.toLowerCase().endsWith(candidate.toLowerCase())) {
      const start = core.length - candidate.length;
      return {
        prefix: core.slice(0, start),
        anchor: core.slice(start),
      };
    }
  }

  return null;
};

const splitEditableChunk = (
  chunk: string,
  recommendation: RecommendationSpec
): { prefix: string; anchor: string; suffix: string } => {
  const trailingSpaces = chunk.match(/\s*$/)?.[0] ?? "";
  const core = chunk.slice(0, chunk.length - trailingSpaces.length);
  if (!core) {
    return { prefix: chunk, anchor: "", suffix: "" };
  }

  const recMatch = matchWithRecommendation(core, recommendation);
  if (recMatch) {
    return {
      prefix: recMatch.prefix,
      anchor: recMatch.anchor,
      suffix: (recMatch.suffix ?? "") + trailingSpaces,
    };
  }

  const closedQuote = core.match(/^(.*?)(["'])([^"']+)\2$/s);
  if (closedQuote) {
    return {
      prefix: closedQuote[1] + closedQuote[2],
      anchor: closedQuote[3].trim(),
      suffix: closedQuote[2] + trailingSpaces,
    };
  }

  const lastDoubleQuote = core.lastIndexOf('"');
  const lastSingleQuote = core.lastIndexOf("'");
  const lastQuote = Math.max(lastDoubleQuote, lastSingleQuote);
  if (lastQuote >= 0 && lastQuote < core.length - 1) {
    const anchor = core.slice(lastQuote + 1).trim();
    if (anchor) {
      return {
        prefix: core.slice(0, lastQuote + 1),
        anchor,
        suffix: trailingSpaces,
      };
    }
  }

  const lastToken = core.match(/^(.*?)([^\s]+)$/s);
  if (lastToken) {
    return {
      prefix: lastToken[1],
      anchor: lastToken[2],
      suffix: trailingSpaces,
    };
  }

  return { prefix: chunk, anchor: "", suffix: "" };
};

const getDefaultTokenValue = (
  anchor: string,
  recommendation: RecommendationSpec,
  occurrence: number
): string => {
  const trimmedAnchor = anchor.trim();
  if (trimmedAnchor) {
    if (recommendation.kind === "options") {
      const selections = parseOptionSelectionFromValue(
        trimmedAnchor,
        buildDisplayOptions(recommendation)
      );
      if (selections.length > 0) {
        return selections.join(", ");
      }
    }
    return trimmedAnchor;
  }

  if (recommendation.kind === "options") {
    return recommendationDisplayValue(recommendation.options[0] ?? "");
  }
  if (recommendation.kind === "range") {
    return occurrence === 0 ? recommendation.min : recommendation.max;
  }
  if (recommendation.kind === "text") {
    return recommendationDisplayValue(recommendation.suggestion);
  }
  return "";
};

const buildQuestionParts = (
  finalQuestion: string,
  recommendations?: Record<string, unknown>
): { parts: QuestionPart[]; initialSelectedByUuid: Record<string, string[]> } => {
  const parts: QuestionPart[] = [];
  const initialSelectedByUuid: Record<string, string[]> = {};
  const uuidCount: Record<string, number> = {};
  const mergedOptionDefaultsByUuid: Record<string, string[]> = {};
  let cursor = 0;
  let match: RegExpExecArray | null;

  UUID_PATTERN.lastIndex = 0;

  while ((match = UUID_PATTERN.exec(finalQuestion)) !== null) {
    const uuid = match[1];
    const recommendation = buildRecommendationSpec(recommendations?.[uuid]);
    const rawChunk = finalQuestion.slice(cursor, match.index);
    const { prefix, anchor, suffix } = splitEditableChunk(rawChunk, recommendation);

    if (recommendation.kind === "options") {
      const optionSelections = parseOptionSelectionFromValue(
        getDefaultTokenValue(anchor, recommendation, 0),
        buildDisplayOptions(recommendation)
      );
      if (!mergedOptionDefaultsByUuid[uuid]) {
        mergedOptionDefaultsByUuid[uuid] = [];
      }
      optionSelections.forEach((optionValue) => {
        if (!mergedOptionDefaultsByUuid[uuid].includes(optionValue)) {
          mergedOptionDefaultsByUuid[uuid].push(optionValue);
        }
      });
    }

    const previousToken = [...parts].reverse().find((p) => p.type === "token") as
      | Extract<QuestionPart, { type: "token" }>
      | undefined;
    const shouldMergeConsecutiveOptionsToken =
      !!previousToken &&
      previousToken.uuid === uuid &&
      previousToken.recommendation.kind === "options" &&
      recommendation.kind === "options" &&
      !recommendation.single_select &&
      /^[\s,;]*(?:(?:and|or)[\s,;]*)?$/i.test(prefix) &&
      parseOptionSelectionFromValue(anchor, buildDisplayOptions(recommendation)).length > 0;
    if (shouldMergeConsecutiveOptionsToken) {
      cursor = match.index + match[0].length;
      continue;
    }

    const rawTrimmed = rawChunk.trim();
    const shouldSkipDuplicateToken =
      !!previousToken &&
      previousToken.uuid === uuid &&
      !HAS_ALNUM.test(rawChunk) &&
      !!rawTrimmed &&
      /^["'`()[\]{}]+$/.test(rawTrimmed);

    if (shouldSkipDuplicateToken) {
      if (rawChunk) {
        parts.push({ type: "text", text: rawChunk });
      }
      cursor = match.index + match[0].length;
      continue;
    }

    if (prefix) {
      parts.push({ type: "text", text: prefix });
    }

    const occurrence = uuidCount[uuid] ?? 0;
    uuidCount[uuid] = occurrence + 1;
    const defaultValue = getDefaultTokenValue(anchor, recommendation, occurrence);
    if (!initialSelectedByUuid[uuid]) {
      initialSelectedByUuid[uuid] = [];
    }
    initialSelectedByUuid[uuid][occurrence] = defaultValue;

    parts.push({
      type: "token",
      uuid,
      occurrence,
      recommendation,
    });

    if (suffix) {
      parts.push({ type: "text", text: suffix });
    }

    cursor = match.index + match[0].length;
  }

  const tail = finalQuestion.slice(cursor);
  if (tail) {
    parts.push({ type: "text", text: tail });
  }

  parts.forEach((part) => {
    if (part.type !== "token" || part.recommendation.kind !== "options") {
      return;
    }
    const mergedDefaults = mergedOptionDefaultsByUuid[part.uuid];
    if (!mergedDefaults || mergedDefaults.length === 0) {
      return;
    }
    const selections = part.recommendation.single_select
      ? mergedDefaults.slice(0, 1)
      : mergedDefaults;
    initialSelectedByUuid[part.uuid][part.occurrence] = selections.join(", ");
  });

  return { parts, initialSelectedByUuid };
};

const buildResolvedQuestion = (
  parts: QuestionPart[],
  selectedByUuid: Record<string, string[]>
): string => {
  const optionsTokenCountByUuid: Record<string, number> = {};
  parts.forEach((part) => {
    if (part.type !== "token" || part.recommendation.kind !== "options") {
      return;
    }
    optionsTokenCountByUuid[part.uuid] =
      (optionsTokenCountByUuid[part.uuid] ?? 0) + 1;
  });

  return parts
    .map((part) => {
      if (part.type === "text") {
        return part.text;
      }
      if (
        part.recommendation.kind === "options" &&
        optionsTokenCountByUuid[part.uuid] === 1
      ) {
        return (selectedByUuid[part.uuid] ?? [])
          .map((item) => item.trim())
          .filter((item) => item.length > 0)
          .join(", ");
      }
      return selectedByUuid[part.uuid]?.[part.occurrence] ?? "";
    })
    .join("")
    .replace(/\s{2,}/g, " ")
    .trim();
};

const buildSubmitSelectedByUuid = (
  parts: QuestionPart[],
  selectedMap: Record<string, string[]>,
  selectedOptionsMap: Record<string, string[]>
): Record<string, string[]> => {
  const optionUuids = new Set<string>();
  const optionsTokenCountByUuid: Record<string, number> = {};

  parts.forEach((part) => {
    if (part.type !== "token" || part.recommendation.kind !== "options") {
      return;
    }
    optionUuids.add(part.uuid);
    optionsTokenCountByUuid[part.uuid] =
      (optionsTokenCountByUuid[part.uuid] ?? 0) + 1;
  });

  const normalized: Record<string, string[]> = {};
  Object.entries(selectedMap).forEach(([uuid, values]) => {
    if (optionUuids.has(uuid)) {
      return;
    }
    const cleaned = values
      .filter((item): item is string => typeof item === "string")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
    if (cleaned.length > 0) {
      normalized[uuid] = cleaned;
    }
  });

  parts.forEach((part) => {
    if (part.type !== "token" || part.recommendation.kind !== "options") {
      return;
    }
    const tokenKey = tokenStateKey(part.uuid, part.occurrence);
    const displayOptions = buildDisplayOptions(part.recommendation);
    const valuesForUuid = selectedMap[part.uuid] ?? [];
    const rawValue =
      optionsTokenCountByUuid[part.uuid] === 1
        ? valuesForUuid.join(", ")
        : valuesForUuid[part.occurrence] ?? "";
    const selected =
      selectedOptionsMap[tokenKey] ??
      parseOptionSelectionFromValue(rawValue, displayOptions);
    const cleaned = selected.map((item) => item.trim()).filter((item) => item.length > 0);
    if (cleaned.length === 0) {
      return;
    }
    const prev = normalized[part.uuid] ?? [];
    normalized[part.uuid] = Array.from(new Set([...prev, ...cleaned]));
  });

  return normalized;
};

const FollowupActionForm: React.FC<FollowupActionFormProps> = ({
  message,
  handleFollowupActionSubmit,
}) => {
  const {
    submitted,
    submitting,
    finalQuestion,
    text,
    initialFuzzyRecommendations,
    selectedByUuid: selectedByUuidFromMessage,
  } = message;

  const { parts, initialSelectedByUuid } = useMemo(
    () => buildQuestionParts(finalQuestion, initialFuzzyRecommendations),
    [finalQuestion, initialFuzzyRecommendations]
  );

  const [selectedByUuid, setSelectedByUuid] = useState<Record<string, string[]>>(
    selectedByUuidFromMessage && Object.keys(selectedByUuidFromMessage).length > 0
      ? selectedByUuidFromMessage
      : initialSelectedByUuid
  );
  const [selectedOptionsByToken, setSelectedOptionsByToken] = useState<
    Record<string, string[]>
  >({});

  const rebuildOptionSelections = (
    currentParts: QuestionPart[],
    selectedMap: Record<string, string[]>
  ): Record<string, string[]> => {
    const next: Record<string, string[]> = {};
    const optionsTokenCountByUuid: Record<string, number> = {};
    currentParts.forEach((part) => {
      if (part.type !== "token" || part.recommendation.kind !== "options") {
        return;
      }
      optionsTokenCountByUuid[part.uuid] =
        (optionsTokenCountByUuid[part.uuid] ?? 0) + 1;
    });

    currentParts.forEach((part) => {
      if (part.type !== "token" || part.recommendation.kind !== "options") {
        return;
      }

      const key = tokenStateKey(part.uuid, part.occurrence);
      const options = buildDisplayOptions(part.recommendation);
      const valuesForUuid = selectedMap[part.uuid] ?? [];
      const rawValue =
        optionsTokenCountByUuid[part.uuid] === 1
          ? valuesForUuid.join(", ")
          : valuesForUuid[part.occurrence] ?? "";
      const parsed = parseOptionSelectionFromValue(rawValue, options);
      if (parsed.length > 0) {
        next[key] = parsed;
      } else if (rawValue.trim().length === 0 && options.length > 0) {
        next[key] = [options[0]];
      } else {
        next[key] = [];
      }
    });
    return next;
  };

  useEffect(() => {
    const baseSelected =
      selectedByUuidFromMessage && Object.keys(selectedByUuidFromMessage).length > 0
        ? selectedByUuidFromMessage
        : initialSelectedByUuid;

    const synchronized = { ...baseSelected };
    parts.forEach((part) => {
      if (part.type !== "token" || part.recommendation.kind !== "options") {
        return;
      }
      const options = buildDisplayOptions(part.recommendation);
      const selections = Array.from(new Set(
        (baseSelected[part.uuid] ?? []).flatMap((value) =>
          parseOptionSelectionFromValue(value, options)
        )
      ));
      const values = part.recommendation.single_select ? selections.slice(0, 1) : selections;
      const nextValues = part.occurrence === 0 ? [] : [...synchronized[part.uuid]];
      nextValues[part.occurrence] = (values.length > 0 ? values : options.slice(0, 1)).join(", ");
      synchronized[part.uuid] = nextValues;
    });
    setSelectedByUuid(synchronized);
    setSelectedOptionsByToken(rebuildOptionSelections(parts, synchronized));
  }, [initialSelectedByUuid, message.id, parts, selectedByUuidFromMessage]);

  const hasUuid = useMemo(
    () => parts.some((part) => part.type === "token"),
    [parts]
  );

  const resolvedFinalQuestion = useMemo(
    () => buildResolvedQuestion(parts, selectedByUuid),
    [parts, selectedByUuid]
  );
  const selectedByUuidForSubmit = useMemo(
    () => buildSubmitSelectedByUuid(parts, selectedByUuid, selectedOptionsByToken),
    [parts, selectedByUuid, selectedOptionsByToken]
  );

  const handleTokenValueChange = (
    uuid: string,
    occurrence: number,
    value: string
  ) => {
    setSelectedByUuid((prev) => {
      const nextValues = prev[uuid] ? [...prev[uuid]] : [];
      nextValues[occurrence] = value;
      return {
        ...prev,
        [uuid]: nextValues,
      };
    });
  };

  const handleOptionsTokenChange = (
    part: Extract<QuestionPart, { type: "token" }>,
    rawValue: string[]
  ) => {
    const selections = Array.from(new Set(rawValue.filter((v) => v.trim().length > 0)));
    const nextSelection = part.recommendation.kind === "options" && part.recommendation.single_select
      ? selections.slice(0, 1)
      : selections;
    const linkedParts = parts.filter(
      (item): item is Extract<QuestionPart, { type: "token" }> =>
        item.type === "token" && item.uuid === part.uuid && item.recommendation.kind === "options"
    );

    setSelectedOptionsByToken((prev) => {
      const next = { ...prev };
      linkedParts.forEach((item) => {
        next[tokenStateKey(item.uuid, item.occurrence)] = nextSelection;
      });
      return next;
    });
    setSelectedByUuid((prev) => {
      const nextValues = prev[part.uuid] ? [...prev[part.uuid]] : [];
      linkedParts.forEach((item) => {
        nextValues[item.occurrence] = nextSelection.join(", ");
      });
      return { ...prev, [part.uuid]: nextValues };
    });
  };

  const tokenErrors = useMemo(() => {
    const errorMap: Record<string, string> = {};
    const rangeTokensByUuid: Record<
      string,
      { key: string; occurrence: number; value: number }[]
    > = {};

    parts.forEach((part) => {
      if (part.type !== "token") {
        return;
      }
      const key = tokenStateKey(part.uuid, part.occurrence);
      const value = (selectedByUuid[part.uuid]?.[part.occurrence] ?? "").trim();

      if (part.recommendation.kind === "options") {
        const displayOptions = buildDisplayOptions(part.recommendation);
        const selected =
          selectedOptionsByToken[key] ??
          parseOptionSelectionFromValue(value, displayOptions);
        if (selected.length === 0) {
          errorMap[key] = "Please select at least one option.";
        } else if (part.recommendation.single_select && selected.length !== 1) {
          errorMap[key] = "Please select exactly one column.";
        }
        return;
      }

      if (part.recommendation.kind === "range") {
        if (!value) {
          errorMap[key] = "Please enter a number.";
          return;
        }
        const numericValue = Number(value);
        if (Number.isNaN(numericValue)) {
          errorMap[key] = "Value must be a number.";
          return;
        }

        const min = Number(part.recommendation.min);
        const max = Number(part.recommendation.max);
        if (!Number.isNaN(min) && !Number.isNaN(max)) {
          if (numericValue < min || numericValue > max) {
            errorMap[key] = `Must be between ${part.recommendation.min} and ${part.recommendation.max}.`;
            return;
          }
          if (!rangeTokensByUuid[part.uuid]) {
            rangeTokensByUuid[part.uuid] = [];
          }
          rangeTokensByUuid[part.uuid].push({
            key,
            occurrence: part.occurrence,
            value: numericValue,
          });
        }
      }
    });

    Object.values(rangeTokensByUuid).forEach((tokens) => {
      if (tokens.length < 2) {
        return;
      }
      const sorted = [...tokens].sort((a, b) => a.occurrence - b.occurrence);
      const first = sorted[0];
      const second = sorted[1];
      if (first.value > second.value) {
        errorMap[first.key] = "Start must be less than or equal to end.";
        errorMap[second.key] = "End must be greater than or equal to start.";
      }
    });

    return errorMap;
  }, [parts, selectedByUuid, selectedOptionsByToken]);

  const canSubmit = useMemo(
    () => Object.keys(tokenErrors).length === 0 && !submitted && !submitting,
    [submitted, submitting, tokenErrors]
  );

  const renderTokenInput = (part: Extract<QuestionPart, { type: "token" }>, key: string) => {
    const tokenKey = tokenStateKey(part.uuid, part.occurrence);
    const errorText = tokenErrors[tokenKey];
    const value = selectedByUuid[part.uuid]?.[part.occurrence] ?? "";
    const disabled = !!submitted || !!submitting;
    const commonSx = {
      mx: 0.5,
      minWidth: 110,
      "& .MuiInputBase-input": {
        py: 0.7,
      },
    };

    if (part.recommendation.kind === "options") {
      const singleSelect = part.recommendation.single_select;
      const displayOptions = buildDisplayOptions(part.recommendation);
      const selectedOptions =
        selectedOptionsByToken[tokenKey] ??
        parseOptionSelectionFromValue(value, displayOptions);
      const allOptions = Array.from(new Set([...displayOptions, ...selectedOptions]));

      return (
        <Tooltip key={key} title="Select from recommended values">
          <Box sx={{ ...commonSx, minWidth: 260, maxWidth: 460 }}>
            <Autocomplete
              multiple={!singleSelect}
              disableCloseOnSelect={!singleSelect}
              options={allOptions}
              value={singleSelect ? selectedOptions[0] ?? null : selectedOptions}
              disabled={disabled}
              onChange={(_, nextValues) =>
                handleOptionsTokenChange(part, typeof nextValues === "string" ? [nextValues] : nextValues ?? [])
              }
              renderTags={(tagValue, getTagProps) =>
                tagValue.map((option, index) => (
                  <Chip
                    {...getTagProps({ index })}
                    key={option}
                    label={option}
                    size="small"
                  />
                ))
              }
              renderInput={(params) => (
                <TextField
                  {...params}
                  size="small"
                  error={!!errorText}
                  helperText={errorText ?? (singleSelect ? "Select one column." : "Select one or more values.")}
                  placeholder={selectedOptions.length === 0 ? "Select values" : ""}
                />
              )}
            />
          </Box>
        </Tooltip>
      );
    }

    let tooltipText = "Edit value";
    if (part.recommendation.kind === "range") {
      tooltipText = `Recommended range: ${part.recommendation.min} to ${part.recommendation.max}`;
    } else if (part.recommendation.kind === "text") {
      tooltipText = `Recommended: ${recommendationDisplayValue(part.recommendation.suggestion)}`;
    }

    return (
      <Tooltip key={key} title={tooltipText}>
        <TextField
          size="small"
          type={part.recommendation.kind === "range" ? "number" : "text"}
          value={value}
          disabled={disabled}
          onChange={(e) =>
            handleTokenValueChange(part.uuid, part.occurrence, e.target.value)
          }
          error={!!errorText}
          helperText={errorText}
          sx={{
            ...commonSx,
            width: Math.min(Math.max(value.length * 9 + 45, 110), 260),
          }}
        />
      </Tooltip>
    );
  };

  return (
    <Box
      sx={{
        maxWidth: "60%",
        p: 1,
        borderRadius: 2,
        bgcolor: submitted ? "#3B77BC" : "#F5F6F6",
        color: submitted ? "white" : "#3B77BC",
        mb: 2,
        border: "1px solid",
        borderColor: "#3B77BC",
      }}
    >
      <Typography variant="body1" sx={{ mb: 1, color: submitted ? "white" : "#3B77BC" }}>
        The complete translation sentence is:
      </Typography>
      {hasUuid ? (
        <Box
          sx={{
            mb: 1,
            px: 1,
            py: 1,
            borderRadius: 1,
            backgroundColor: submitted ? "rgba(255,255,255,0.12)" : "#F8D86A",
            color: submitted ? "white" : "#3B77BC",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            lineHeight: 2,
          }}
        >
          {parts.map((part, index) => {
            if (part.type === "text") {
              return (
                <Typography
                  key={`text-${index}`}
                  component="span"
                  variant="body1"
                  sx={{ whiteSpace: "pre-wrap" }}
                >
                  {part.text}
                </Typography>
              );
            }
            return renderTokenInput(part, `token-${part.uuid}-${part.occurrence}-${index}`);
          })}
        </Box>
      ) : (
        <Typography variant="body1" sx={{ mb: 1, color: submitted ? "white" : "#3B77BC" }}>
          <mark style={{ backgroundColor: "#F8D86A", fontWeight: "bold" }}>
            {finalQuestion}
          </mark>
        </Typography>
      )}
      <Typography variant="body1" sx={{ mb: 1, color: submitted ? "white" : "#3B77BC" }}>
        {text}
      </Typography>
      <Button
        variant="contained"
        size="small"
        onClick={() =>
          handleFollowupActionSubmit(message.id, {
            finalQuestion: resolvedFinalQuestion || finalQuestion.replace(UUID_PATTERN, "").trim(),
            selectedByUuid: selectedByUuidForSubmit,
          })
        }
        disabled={!canSubmit}
        sx={{
          ...(submitted && {
            "&.Mui-disabled": {
              color: "white",
              backgroundColor: "#3B77BC",
              border: "1px solid",
              borderColor: "white",
            },
          }),
        }}
      >
        {submitting ? (
          <CircularProgress size={20} />
        ) : submitted ? (
          <Typography variant="body1">Completed</Typography>
        ) : (
          <Typography variant="body1">Run Next Two Steps</Typography>
        )}
      </Button>
    </Box>
  );
};

export default FollowupActionForm;
