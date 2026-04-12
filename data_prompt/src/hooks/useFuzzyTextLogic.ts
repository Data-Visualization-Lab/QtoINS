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

/**
 * 专门处理 fuzzy_text 类型消息的逻辑
 */
export function useFuzzyTextLogic(params: UseFuzzyTextLogicParams) {
  const {
    messages,
    setMessages,
    appendMessage,
    setVisData,
    setIsLoading,
    onTranslationReady,
  } = params;

  /** 用户修改 fuzzy_text 消息的文本输入 */
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

  /** 用户在多选时切换选项 */
  const handleFuzzyTextToggle = useCallback(
    (msgId: number, index: number) => {
      setMessages((prev) =>
        prev.map((m) => {
          if (m.role === "fuzzy_text" && m.id === msgId) {
            const fm = m as FuzzyTextMessage;
            if (fm.submitted) return m;
            const currentIndices = fm.userSelectedIndices || [];
            let newIndices = [...currentIndices];
            if (newIndices.includes(index)) {
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

  /** 用户提交 fuzzy_text 消息，调用后端接口 /api/fuzzytext */
  const handleFuzzyTextSubmit = useCallback(
    async (msgId: number) => {
      const fuzzyMsg = messages.find(
        (m) => m.id === msgId && m.role === "fuzzy_text"
      ) as FuzzyTextMessage | undefined;
      if (!fuzzyMsg || fuzzyMsg.submitted) return;

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
        // 立即更新状态为提交中，防止重复点击
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
        const result = await resp.json();

        if (result.awaitingFollowup === true && result.finalquestion) {
          onTranslationReady(
            result.finalquestion,
            result.initial_fuzzy_recommendations
          );
        }

        // 如果返回了 vis 数据，则更新并关闭加载状态
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
                  keyName: `${outerKey} - ${subKey}`, // 拼接外层 key 与子字段名
                  columnname: subKey, // 使用子字段名作为 columnname
                  category: "multiple_string", // 固定为 multiple_string
                  solution: subValue.solution,
                  userSelectedIndices: [],
                  submitted: false,
                  // 新增字段 backendKey，保存后端返回的外层 key
                  backendKey: outerKey,
                });
              });
            }
          );
          setMessages((prev) => [...prev, ...fuzzyStringMsgs]);
        }

        const fuzzyResult = result.fuzzyresult;
        if (!fuzzyResult) {
          // 后端没有返回 fuzzyResult，将 submitted 状态重置为 false，允许用户重新提交
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
        // 如果请求出错，重置 submitted 状态，允许用户重试
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
          text: "Submission of fuzzy text failed. Please try again.",
        });
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
