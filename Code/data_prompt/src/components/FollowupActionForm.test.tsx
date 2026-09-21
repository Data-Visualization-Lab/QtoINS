import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import FollowupActionForm from "./FollowupActionForm";
import { FollowupActionMessage } from "../data/messageTypes";

const uuid = "11111111-1111-1111-1111-111111111111";
const token = `[uuid:${uuid}]`;

const renderForm = (
  finalQuestion: string,
  recommendation: unknown,
  selectedByUuid?: Record<string, string[]>
) => {
  const onSubmit = jest.fn();
  const message: FollowupActionMessage = {
    id: 1,
    role: "followup_action",
    text: "Review the query.",
    finalQuestion,
    initialFuzzyRecommendations: { [uuid]: recommendation },
    selectedByUuid,
  };
  render(<FollowupActionForm message={message} handleFollowupActionSubmit={onSubmit} />);
  return onSubmit;
};

test("shared single column choices preserve and synchronize both mentions", () => {
  const onSubmit = renderForm(`Show Genre${token} and group by Genre${token}.`, {
    options: ["Genre", "Type"],
    single_select: true,
  });

  expect(screen.getByText("and group by")).toBeInTheDocument();
  const inputs = screen.getAllByRole("combobox");
  expect(inputs).toHaveLength(2);
  fireEvent.mouseDown(inputs[0]);
  fireEvent.click(screen.getByRole("option", { name: "Type" }));
  inputs.forEach((input: HTMLElement) => expect(input).toHaveValue("Type"));
  fireEvent.click(screen.getByRole("button", { name: "Run Next Two Steps" }));

  expect(onSubmit).toHaveBeenCalledWith(1, {
    finalQuestion: "Show Type and group by Type.",
    selectedByUuid: { [uuid]: ["Type"] },
  });
});

test("ordinary SELECT column choices still allow multiple selections", () => {
  const onSubmit = renderForm(`Show Genre${token}.`, ["Genre", "Type"]);

  fireEvent.mouseDown(screen.getByRole("combobox"));
  fireEvent.click(screen.getByRole("option", { name: "Type" }));
  fireEvent.click(screen.getByRole("button", { name: "Run Next Two Steps" }));

  expect(onSubmit).toHaveBeenCalledWith(1, {
    finalQuestion: "Show Genre, Type.",
    selectedByUuid: { [uuid]: ["Genre", "Type"] },
  });
});

test("aggregate aliases preserve a previously selected second column", () => {
  const onSubmit = renderForm(
    `In table movies\nReturn the maximum value of IMDB Rating and the Best ${token}`,
    { options: ["Rotten_Tomatoes_Rating", "IMDB_Rating"], single_select: true }
  );

  expect(screen.getByRole("combobox")).toHaveValue("IMDB Rating");
  expect(screen.getByText("and the Best")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Run Next Two Steps" }));
  expect(onSubmit).toHaveBeenCalledWith(1, {
    finalQuestion: "In table movies\nReturn the maximum value of IMDB Rating and the Best",
    selectedByUuid: { [uuid]: ["IMDB Rating"] },
  });
});

test("consecutive enumerated choices still use one multi-select control", () => {
  const onSubmit = renderForm(`Show Genre${token}, Type${token}.`, ["Genre", "Type"]);

  expect(screen.getAllByRole("combobox")).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Run Next Two Steps" }));
  expect(onSubmit.mock.calls[0][1]).toEqual({
    finalQuestion: "Show Genre, Type.",
    selectedByUuid: { [uuid]: ["Genre", "Type"] },
  });
});

test("restored multi-select choices do not duplicate values in the sentence", () => {
  const onSubmit = renderForm(`Show Genre${token}.`, ["Genre", "Type"], {
    [uuid]: ["Genre", "Type"],
  });

  fireEvent.click(screen.getByRole("button", { name: "Run Next Two Steps" }));
  expect(onSubmit.mock.calls[0][1].finalQuestion).toBe("Show Genre, Type.");
});

test("range endpoints sharing a UUID remain independent", () => {
  const onSubmit = renderForm(`Keep values from 1${token} to 10${token}.`, "from 1 to 10");
  const inputs = screen.getAllByRole("spinbutton");

  fireEvent.change(inputs[0], { target: { value: "2" } });
  expect(inputs[1]).toHaveValue(10);
  fireEvent.click(screen.getByRole("button", { name: "Run Next Two Steps" }));
  expect(onSubmit).toHaveBeenCalledWith(1, {
    finalQuestion: "Keep values from 2 to 10.",
    selectedByUuid: { [uuid]: ["2", "10"] },
  });
});
