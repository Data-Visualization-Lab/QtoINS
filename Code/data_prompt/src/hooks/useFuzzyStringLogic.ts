import { useCallback } from "react";
import { Message, FuzzyStringMessage } from "../data/messageTypes";

interface UseFuzzyStringLogicParams {
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


export function useFuzzyStringLogic(params: UseFuzzyStringLogicParams) {
  const {
    messages,
    setMessages,
    appendMessage,
    setVisData,
    setIsLoading,
    onTranslationReady,
  } = params;

  
  const handleFuzzyStringToggle = useCallback(
    (msgId: number, index: number) => {
      setMessages((prev) =>
        prev.map((m) => {
          if (
            m.role === "fuzzy_string" &&
            m.id === msgId &&
            m.category === "multiple_string"
          ) {
            const currentIndices = m.userSelectedIndices || [];
            let newIndices = [...currentIndices];
            if (newIndices.includes(index)) {
              newIndices = newIndices.filter((i) => i !== index);
            } else {
              newIndices.push(index);
            }
            return { ...m, userSelectedIndices: newIndices };
          }
          return m;
        })
      );
    },
    [setMessages]
  );

  
  const handleFuzzyStringSubmit = useCallback(
    async (msgId: number) => {
      const fuzzyMsg = messages.find(
        (m) =>
          m.id === msgId &&
          m.role === "fuzzy_string" &&
          m.category === "multiple_string"
      ) as FuzzyStringMessage | undefined;
      if (!fuzzyMsg || fuzzyMsg.submitted) return;

      if (
        !fuzzyMsg.userSelectedIndices ||
        fuzzyMsg.userSelectedIndices.length === 0
      ) {
        appendMessage({
          id: Date.now() + Math.random(),
          role: "system",
          text: "Please select at least one option.",
        });
        return;
      }


      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId ? { ...m, submitting: true } : m
        )
      );

      const finalUserInput = JSON.stringify(
        fuzzyMsg.userSelectedIndices.map(
          (idx) => (fuzzyMsg.solution ? fuzzyMsg.solution[idx] : "")
        )
      );

      const payload = {
        keyName: fuzzyMsg.keyName,
        category: fuzzyMsg.category,
        solution: fuzzyMsg.solution,
        userInput: finalUserInput,
        columnname: fuzzyMsg.columnname,
        backendKey: fuzzyMsg.backendKey,
      };

      try {
        const resp = await fetch("/api/fuzzystring", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const result = await resp.json().catch(() => ({}));
        if (!resp.ok) {
          throw new Error(result.error || result.message || "Submission of fuzzy string failed. Please try again.");
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
            id: Date.now() + Math.random(),
            role: "system",
            text: "I generate a chart to answer the question: " + result.finalquestion,
          });
        }


        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId ? { ...m, submitted: true, submitting: false } : m
          )
        );
      } catch (err) {
        console.error("Error in handleFuzzyStringSubmit:", err);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === msgId ? { ...m, submitting: false } : m
          )
        );
        appendMessage({
          id: Date.now() + Math.random(),
          role: "system",
          text: err instanceof Error ? err.message : "Submission of fuzzy string failed. Please try again.",
        });
        setIsLoading(false);
      }
    },
    [messages, setMessages, appendMessage, setVisData, setIsLoading, onTranslationReady]
  );

  return {
    handleFuzzyStringToggle,
    handleFuzzyStringSubmit,
  };
}
