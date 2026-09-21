import { useCallback } from "react";
import { Message, FuzzyTextMessage, FuzzyStringMessage } from "../data/messageTypes";

interface UseFuzzyTextLogicParams {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  appendMessage: (msg: Message) => void;
  setVisData: React.Dispatch<React.SetStateAction<any>>;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  onTranslationReady: (
    finalQuestion: string,
    initialFuzzyRecommendations?: Record<string, unknown>
  ) => void;
}


export function useFuzzyTextLogic(params: UseFuzzyTextLogicParams) {
  const {
    messages,
    setMessages,
    appendMessage,
    setVisData,
    setIsLoading,
    onTranslationReady,
  } = params;

  
  const handleFuzzyTextChange = useCallback(
    (msgId: number, newValue: string) => {
      setMessages((prev) =>
        prev.map((m) => {
          if (m.role === "fuzzy_text" && m.id === msgId) {
            const fm = m as FuzzyTextMessage;
            if (fm.submitted) return m;
            return {
              ...fm,
              userInput: newValue,
              userSelectedIndices: newValue.trim() ? [] : fm.userSelectedIndices,
            };
          }
          return m;
        })
      );
    },
    [setMessages]
  );

  
  const handleFuzzyTextToggle = useCallback(
    (msgId: number, index: number) => {
      setMessages((prev) =>
        prev.map((m) => {
          if (m.role === "fuzzy_text" && m.id === msgId) {
            const fm = m as FuzzyTextMessage;
            if (fm.submitted) return m;
            const currentIndices = fm.userSelectedIndices || [];
            let newIndices = [...currentIndices];
            if (fm.single_select) {
              newIndices = [index];
            } else if (newIndices.includes(index)) {
              newIndices = newIndices.filter((i) => i !== index);
            } else {
              newIndices.push(index);
            }
            return {
              ...fm,
              userInput: newIndices.length > 0 ? "" : fm.userInput,
              userSelectedIndices: newIndices,
            };
          }
          return m;
        })
      );
    },
    [setMessages]
  );

  
  const handleFuzzyTextSubmit = useCallback(
    async (msgId: number) => {
      const fuzzyMsg = messages.find(
        (m) => m.id === msgId && m.role === "fuzzy_text"
      ) as FuzzyTextMessage | undefined;
      if (!fuzzyMsg || fuzzyMsg.submitted) return;

      if (fuzzyMsg.single_select && (
        (fuzzyMsg.userSelectedIndices?.length || 0) > 1 ||
        (!fuzzyMsg.userSelectedIndices?.length && !fuzzyMsg.userInput?.trim())
      )) {
        appendMessage({
          id: Date.now() + Math.random(),
          role: "system",
          text: "Please select exactly one column.",
        });
        return;
      }

      let finalUserInput = fuzzyMsg.userInput || "";
      if (fuzzyMsg.category === "multiple_column") {
        try {
          const arr = Array.isArray(fuzzyMsg.solution)
            ? fuzzyMsg.solution
            : (typeof fuzzyMsg.solution === "string"
                ? JSON.parse(fuzzyMsg.solution) as string[]
                : []);
          if (fuzzyMsg.userSelectedIndices && fuzzyMsg.userSelectedIndices.length > 0) {
            const selectedValues = fuzzyMsg.userSelectedIndices.map((i) => arr[i]);
            finalUserInput = JSON.stringify(selectedValues);
          }
        } catch (err) {
          console.error("Error parsing solution as array:", err);
        }
      }

      const payload = {
        keyName: fuzzyMsg.keyName,
        category: fuzzyMsg.category,
        solution: fuzzyMsg.solution,
        userInput: finalUserInput,
      };

      try {

        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId && m.role === "fuzzy_text"
              ? { ...m, submitted: true }
              : m
          )
        );

        const resp = await fetch("/api/fuzzytext", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const result = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(result.error || result.message || "Submission of fuzzy text failed. Please try again.");
        }

        if (result.awaitingFollowup === true && result.finalquestion) {
          onTranslationReady(
            result.finalquestion,
            result.initial_fuzzy_recommendations
          );
        }


        if (result.vis !== null && result.vis !== undefined) {
          setVisData((prevData: any) => [...prevData, result.vis]);
          setIsLoading(false);
          appendMessage({
            id: Date.now() + 1,
            role: "system",
            text: "I generate a chart to answer the question: "+result.finalquestion,
          });
        }
        if (
          result.stringresult !== null &&
          result.stringresult !== undefined &&
          Object.keys(result.stringresult).length > 0
        ) {
          appendMessage({
            id: Date.now() + 1,
            role: "system",
            text: "I detected some ambiguities in your query. Please review the following recommendations.",
          });
          const fuzzyStringMsgs: (FuzzyStringMessage & {
            backendKey: string;
          })[] = [];
          Object.entries(result.stringresult).forEach(
            ([outerKey, innerObj]) => {
              const innerEntries = innerObj as Record<
                string,
                { solution: string[] }
              >;
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
            }
          );
          setMessages((prev) => [...prev, ...fuzzyStringMsgs]);
        }

        const fuzzyResult = result.fuzzyresult;
        if (!fuzzyResult) {

          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId && m.role === "fuzzy_text"
                ? { ...m, submitted: false }
                : m
            )
          );
          appendMessage({
            id: Date.now() + Math.random(),
            role: "system",
            text: "Error: No fuzzy result returned from server.",
          });
          setIsLoading(false);
          return;
        }
        if (fuzzyResult.level === "fully_resolvable") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId ? { ...m, fuzzyResult } : m
            )
          );
         
        } else if (fuzzyResult.level === "completely_unresolvable") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === msgId ? { ...m, fuzzyResult, submitted: false } : m
            )
          );
        
        }
        
      } catch (err) {
        console.error("Error in handleFuzzyTextSubmit:", err);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId && m.role === "fuzzy_text"
              ? { ...m, submitted: false }
              : m
          )
        );
        appendMessage({
          id: Date.now() + Math.random(),
          role: "system",
          text: err instanceof Error ? err.message : "Submission of fuzzy text failed. Please try again.",
        });
        setIsLoading(false);
      }
    },
    [messages, setMessages, appendMessage, setVisData, setIsLoading, onTranslationReady]
  );

  return {
    handleFuzzyTextChange,
    handleFuzzyTextToggle,
    handleFuzzyTextSubmit,
  };
}
