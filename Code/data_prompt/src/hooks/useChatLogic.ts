import { useEffect, useState, useCallback } from "react";
import {
  Message,
  FuzzyTextMessage,
  FuzzyStringMessage,
  FollowupActionMessage,
  FollowupActionPayload,
} from "../data/messageTypes";
import { useMyContext } from "../state/MyContext";
import { useFuzzyTextLogic } from "./useFuzzyTextLogic";
import { useFuzzyStringLogic } from "./useFuzzyStringLogic";

type SelectedByUuidMap = Record<string, string[]>;
type SelectedByUuidApiResult = Record<string, string | string[]>;

const buildFinalUuidResult = (
  selectedByUuid: SelectedByUuidMap
): SelectedByUuidApiResult[] => {
  return Object.entries(selectedByUuid).reduce<SelectedByUuidApiResult[]>(
    (acc, [uuid, values]) => {
      const normalized = values
        .filter((item): item is string => typeof item === "string")
        .map((item) => item.trim())
        .filter((item) => item.length > 0);

      if (normalized.length === 0) {
        return acc;
      }

      acc.push({
        [uuid]: normalized.length === 1 ? normalized[0] : normalized,
      });

      return acc;
    },
    []
  );
};

export function useChatLogic(initialDescription?: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { setVisData } = useMyContext();


  const appendMessage = useCallback(
    (msg: Message) => {
      setMessages((prev) => [...prev, msg]);
    },
    [setMessages]
  );

  const onTranslationReady = useCallback(
    (
      finalQuestion: string,
      initialFuzzyRecommendations?: Record<string, unknown>
    ) => {
      appendMessage({
        id: Date.now() + Math.random(),
        role: "followup_action",
        text: 'Click "Run Next Two Steps" to continue.',
        finalQuestion,
        initialFuzzyRecommendations,
        submitted: false,
        submitting: false,
      });
      setIsLoading(false);
    },
    [appendMessage]
  );


  const fuzzyTextLogic = useFuzzyTextLogic({
    messages,
    setMessages,
    appendMessage,
    setVisData,
    setIsLoading,
    onTranslationReady,
  });
  const fuzzyStringLogic = useFuzzyStringLogic({
    messages,
    setMessages,
    appendMessage,
    setVisData,
    setIsLoading,
    onTranslationReady,
  });


  useEffect(() => {
    if (initialDescription?.trim()) {
      setMessages((prev) => {
        if (prev[0]?.role === "system" && prev[0]?.text === initialDescription) {
          return prev;
        }
        return [
          {
            id: Date.now(),
            role: "system",
            text: initialDescription,
          },
          ...prev,
        ];
      });
    }
  }, [initialDescription]);

  
  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const trimText = inputText.trim();
      if (!trimText) return;


      setIsLoading(true);


      appendMessage({
        id: Date.now(),
        role: "user",
        text: trimText,
      });
      setInputText("");

      try {
        const response = await fetch("/gettext", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: trimText }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.error || data.message || "Failed to process the query.");
        }


        if (data.textfuzzy === false && data.stringfuzzy === false) {
          if (data.awaitingFollowup === true && data.finalquestion) {
            onTranslationReady(
              data.finalquestion,
              data.initial_fuzzy_recommendations
            );
            return;
          }


          if (data.vis !== null && data.vis !== undefined) {
            setVisData((prevData: any) => [...prevData, data.vis]);
            appendMessage({
              id: Date.now() + 1,
              role: "system",
              text: "I generate a chart to answer the question: " + data.finalquestion,
            });
            setIsLoading(false);
          } else {
            setIsLoading(false);
          }
        } else if (data.textfuzzy === true && data.stringfuzzy === false) {

          const textrecommend = data.textrecommend;
          appendMessage({
            id: Date.now() + 2,
            role: "system",
            text: "I detected some ambiguities in your query. Please review the following recommendations.",
          });

          const fuzzyMsgs = Object.entries(textrecommend).map(([keyName, rec]) => {
            const { category, solution, single_select } = rec as {
              category: "no_scientific_basis" | "multiple_column" ;
              solution: any;
              single_select?: boolean;
            };

            let messageText = "";
            let defaultUserInput = "";

            if (category === "no_scientific_basis" && typeof solution === "object" && solution !== null) {
              messageText = `Key: ${keyName}, Category: ${category}, Summary: ${solution.Summary}`;
              defaultUserInput = solution.Recommend;
            } else if (category === "no_scientific_basis" ) {
              messageText = `Key: ${keyName}, Category: ${category}, Solution: ${solution}`;
              defaultUserInput = solution;
            } else if (category === "multiple_column") {
              messageText = `Key: ${keyName}, Category: ${category}, Solution: ${solution}`;
              defaultUserInput = "";
            }
            return {
              id: Date.now() + Math.random(),
              role: "fuzzy_text",
              text: messageText,
              keyName,
              category,
              solution,
              single_select,
              summary: solution.Summary,
              userInput: defaultUserInput,
              submitted: false,
              userSelectedIndices: [],
            } as FuzzyTextMessage;
          });
          setMessages((prev) => [...prev, ...fuzzyMsgs]);

        } else if (data.textfuzzy === false && data.stringfuzzy === true) {
          appendMessage({
            id: Date.now() + 3,
            role: "system",
            text: "I detected some ambiguities in your query. Please review the following recommendations.",
          });
          console.log("Received stringfuzzy response:", data); 
          const fuzzyStringData = data.stringresult;
          if (fuzzyStringData && Object.keys(fuzzyStringData).length > 0) {
            const fuzzyStringMsgs: (FuzzyStringMessage & { backendKey: string })[] = [];
            Object.entries(fuzzyStringData).forEach(([outerKey, innerObj]) => {
              const innerEntries = innerObj as Record<string, { solution: string[] }>;
              Object.entries(innerEntries).forEach(([subKey, subValue]) => {
                fuzzyStringMsgs.push({
                  id: Date.now() + Math.random(),
                  role: "fuzzy_string" as const,
                  text: `Select option(s) for ${subKey} in ${outerKey}`,
                  keyName: `${outerKey} - ${subKey}`,
                  columnname: subKey,
                  category: "multiple_string",
                  solution: subValue.solution,
                  userSelectedIndices: [],
                  submitted: false,
                  backendKey: outerKey,
                });
              });
            });
            setMessages((prev) => [...prev, ...fuzzyStringMsgs]);
          } else {
            appendMessage({
              id: Date.now() + 3,
              role: "fuzzy_string",
              text: data.message || "Detected fuzzy string processing.",
            });
          }

        }
      } catch (err) {
        console.error("Error fetching /gettext:", err);
        appendMessage({
          id: Date.now() + 4,
          role: "system",
          text: err instanceof Error ? err.message : "Error: Failed to get response from server.",
        });
        setIsLoading(false);
      }
    },
    [inputText, appendMessage, onTranslationReady, setVisData]
  );

  const handleRunFollowups = useCallback(async (
    msgId: number,
    payload?: FollowupActionPayload
  ) => {
    const followupMessage = messages.find(
      (m) => m.role === "followup_action" && m.id === msgId
    ) as FollowupActionMessage | undefined;
    if (!followupMessage || followupMessage.submitted || followupMessage.submitting) return;

    const finalQuestionForRun =
      payload?.finalQuestion ||
      followupMessage.resolvedFinalQuestion ||
      followupMessage.finalQuestion;

    setMessages((prev) =>
      prev.map((m) =>
        m.role === "followup_action" && m.id === msgId
          ? {
              ...m,
              submitting: true,
              ...(payload
                ? {
                    resolvedFinalQuestion: payload.finalQuestion,
                    selectedByUuid: payload.selectedByUuid,
                  }
                : {}),
            }
          : m
      )
    );
    setIsLoading(true);

    try {
      const response = await fetch("/api/runfollowups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          payload
            ? buildFinalUuidResult(payload.selectedByUuid)
            : []
        ),
      });
      const data = await response.json().catch(() => ({}));

      if (response.ok && data.vis !== null && data.vis !== undefined) {
        setVisData((prevData: any) => [...prevData, data.vis]);
        appendMessage({
          id: Date.now() + Math.random(),
          role: "system",
          text: "I generate a chart to answer the question: " + finalQuestionForRun,
        });
        setMessages((prev) =>
          prev.map((m) =>
            m.role === "followup_action" && m.id === msgId
              ? { ...m, submitting: false, submitted: true }
              : m
          )
        );
      } else {
        appendMessage({
          id: Date.now() + Math.random(),
          role: "system",
          text: data.error || data.message || "Failed to run the next two steps.",
        });
        setMessages((prev) =>
          prev.map((m) =>
            m.role === "followup_action" && m.id === msgId
              ? { ...m, submitting: false }
              : m
          )
        );
      }
    } catch (err) {
      console.error("Error fetching /api/runfollowups:", err);
      appendMessage({
        id: Date.now() + Math.random(),
        role: "system",
        text: "Error: Failed to run the next two steps.",
      });
      setMessages((prev) =>
        prev.map((m) =>
          m.role === "followup_action" && m.id === msgId
            ? { ...m, submitting: false }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [appendMessage, messages, setVisData]);

  return {
    messages,
    inputText,
    setInputText,
    handleSend,
    isLoading,
    handleRunFollowups,

    handleFuzzyTextChange: fuzzyTextLogic.handleFuzzyTextChange,
    handleFuzzyTextSubmit: fuzzyTextLogic.handleFuzzyTextSubmit,
    handleFuzzyTextToggle: fuzzyTextLogic.handleFuzzyTextToggle,
    handleFuzzyStringSubmit: fuzzyStringLogic.handleFuzzyStringSubmit,
    handleFuzzyStringToggle: fuzzyStringLogic.handleFuzzyStringToggle,
  };
}
