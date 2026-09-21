import React, { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import FuzzyTextForm from "../components/FuzzyTextForm";
import { FuzzyTextMessage, Message } from "../data/messageTypes";
import { useFuzzyTextLogic } from "./useFuzzyTextLogic";

const Form = ({ singleSelect = true }: { singleSelect?: boolean }) => {
  const [messages, setMessages] = useState<Message[]>([{
    id: 1,
    role: "fuzzy_text",
    text: "Choose a column.",
    keyName: "category+GROUP_BY+uuid",
    category: "multiple_column",
    solution: ["Genre", "Type"],
    single_select: singleSelect,
    userSelectedIndices: [],
  }]);
  const [loading, setIsLoading] = useState(true);
  const logic = useFuzzyTextLogic({
    messages,
    setMessages,
    appendMessage: (message) => setMessages((prev) => [...prev, message]),
    setVisData: () => {},
    setIsLoading,
    onTranslationReady: () => {},
  });
  return <>
    <FuzzyTextForm message={messages[0] as FuzzyTextMessage} {...logic} />
    <span>{loading ? "Loading" : "Ready"}</span>
    {messages.slice(1).map((message) => <p key={message.id}>{message.text}</p>)}
  </>;
};

const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
  jest.restoreAllMocks();
});

test("single column choices use radios and require a choice or new concept", () => {
  render(<Form />);
  expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();
  fireEvent.click(screen.getByRole("radio", { name: "Genre" }));
  fireEvent.click(screen.getByRole("radio", { name: "Type" }));
  expect(screen.getByRole("radio", { name: "Genre" })).not.toBeChecked();
  expect(screen.getByRole("radio", { name: "Type" })).toBeChecked();
  expect(screen.getByRole("button", { name: "Submit" })).toBeEnabled();
});

test("ordinary SELECT retains checkbox multi-selection", () => {
  render(<Form singleSelect={false} />);
  fireEvent.click(screen.getByRole("checkbox", { name: "Genre" }));
  fireEvent.click(screen.getByRole("checkbox", { name: "Type" }));
  expect(screen.getByRole("checkbox", { name: "Genre" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "Type" })).toBeChecked();
});

test("a rejected column choice displays the backend error and allows retry", async () => {
  jest.spyOn(console, "error").mockImplementation(() => {});
  globalThis.fetch = jest.fn().mockResolvedValue({
    ok: false,
    json: async () => ({ error: "GROUP BY requires one column." }),
  });
  render(<Form />);
  fireEvent.click(screen.getByRole("radio", { name: "Genre" }));
  fireEvent.click(screen.getByRole("button", { name: "Submit" }));

  await waitFor(() => expect(screen.getByText("GROUP BY requires one column.")).toBeInTheDocument());
  expect(screen.getByText("Ready")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Submit" })).toBeEnabled();
  expect(JSON.parse((globalThis.fetch as jest.Mock).mock.calls[0][1].body).userInput).toBe('["Genre"]');
});
