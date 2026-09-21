// src/components/FuzzyTextForm.tsx
import React from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  FormControlLabel,
  Checkbox,
  Radio,
  CircularProgress,
  Slider,
} from "@mui/material";
import { FuzzyTextMessage } from "../data/messageTypes";

interface FuzzyTextFormProps {
  message: FuzzyTextMessage;
  handleFuzzyTextChange: (msgId: number, newValue: string) => void;

  handleFuzzyTextSubmit: (msgId: number, sliderValue?: number[]) => void;
  handleFuzzyTextToggle: (msgId: number, index: number) => void;
}

const FuzzyTextForm: React.FC<FuzzyTextFormProps> = ({
  message,
  handleFuzzyTextChange,
  handleFuzzyTextSubmit,
  handleFuzzyTextToggle,
}) => {
  const {
    category,
    keyName,
    solution,
    userInput,
    submitted,
    fuzzyResult,
    userSelectedIndices,
    summary,
    single_select,
  } = message;


  const [initialUserInput] = React.useState(userInput);

  let options: string[] = [];
  if (category === "multiple_column") {
    if (Array.isArray(solution)) {
      options = solution;
    } else {
      try {
        options =
          typeof solution === "string"
            ? (JSON.parse(solution) as string[])
            : [];
      } catch (err) {
        console.error("Failed to parse solution as array:", err);
      }
    }
  }


  const isLoading = submitted && !fuzzyResult;
  const ChoiceControl = single_select ? Radio : Checkbox;


  const [sliderValue, setSliderValue] = React.useState<number[]>(() => {
    if (initialUserInput) {
      const parts = initialUserInput.split(/(\d+(?:\.\d+)?)/);
      
      const min = parseFloat(parts[1]);
      const max = parseFloat(parts[3]);
      console.log(initialUserInput)
      console.log(parts)
      console.log("Parsed slider range:", min, max);
      return [min, max];
    }
    return [];
  });

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
      <Typography
        variant="body1"
        sx={{ mb: 1, color: submitted ? "white" : "#3B77BC" }}
      >
        {category === "no_scientific_basis" && (
          <>
            <mark style={{ backgroundColor: "#F8D86A", fontWeight: "bold" }}>
              "{keyName.split('+')[0].replace(/_/g, " ")}"
            </mark>{" "}
            may relevant to :
          </>
        )}
        {category === "multiple_column" && (
          <>
            <mark style={{ backgroundColor: "#F8D86A", fontWeight: "bold" }}>
              "{keyName.split('+')[0].replace(/_/g, " ")}"
            </mark>{" "}
            may relevant to :
          </>
        )}
      </Typography>

      {summary && (
        <Typography
          variant="body1"
          sx={{
            mb: 1,
            fontStyle: "italic",
            color: submitted ? "white" : "#3B77BC",
          }}
        >
          {summary}
        </Typography>
      )}

      {category === "multiple_column" && (
        <>
          {options.map((opt, i) => {
            const checked = userSelectedIndices?.includes(i) || false;
            return (
              <FormControlLabel
                key={i}
                control={
                  <ChoiceControl
                    checked={checked}
                    name={`column-choice-${message.id}`}
                    onChange={() => handleFuzzyTextToggle(message.id, i)}
                    disabled={submitted}
                    sx={{
                      color: "#3B77BC",
                      "&.Mui-checked": { color: "black" },
                    }}
                  />
                }
                label={<Typography variant="body1">{opt}</Typography>}
                sx={{
                  "& .MuiFormControlLabel-label": {
                    color: submitted
                      ? checked
                        ? "white"
                        : "black"
                      : "#3B77BC",
                    "&.Mui-disabled": {
                      color: submitted
                        ? checked
                          ? "white"
                          : "black"
                        : "#3B77BC",
                    },
                  },
                }}
              />
            );
          })}
        </>
      )}

      {fuzzyResult && fuzzyResult.level === "completely_unresolvable" && (
        <Box sx={{ mb: 1 }}>
          <Typography variant="body1" color="error">
            Completely Unresolvable – Please provide new input:
          </Typography>
        </Box>
      )}

      {initialUserInput ? (

        (() => {
      const parts = initialUserInput.split(/(\d+(?:\.\d+)?)/);
      
      const min = parseFloat(parts[1]);
      const max = parseFloat(parts[3]);
          return (
            <Box>
              <Typography
                variant="body1"
                sx={{
                  mb: 1,
                  fontStyle: "italic",
                  color: submitted ? "white" : "#3B77BC",
                }}
              >
                {parts[0]}
                <Box
                  sx={{ display: "flex", alignItems: "center", mt: 1, mb: 1 }}
                >
                  
                  <Typography
                    variant="body1"
                    sx={{ mr: 1, color: submitted ? "white" : "#3B77BC" }}
                  >
                    {min}
                  </Typography>
                  
                  <Slider
                    value={sliderValue}
                    onChange={(e, newValue) => {
                      if (Array.isArray(newValue)) {
                        setSliderValue(newValue);
                        const sliderStr = `${newValue[0]} - ${newValue[1]}`;
                        handleFuzzyTextChange(message.id, sliderStr);
                      }
                    }}
                    valueLabelDisplay="auto"
                    min={min}
                    max={max}
                    /*step={0.1}*/
                    sx={{
                      flexGrow: 1,
                      mx: 2,
                      color: submitted ? "white" : "#3B77BC",
                    }}
                  />
                  
                  <Typography
                    variant="body1"
                    sx={{ ml: 1, color: submitted ? "white" : "#3B77BC" }}
                  >
                    {max}
                  </Typography>
                </Box>
                {parts[4]}
              </Typography>
              <Box
                sx={{ display: "flex", justifyContent: "flex-start", mt: 1 }}
              >
                <Button
                  variant="contained"
                  size="small"
                  onClick={() =>

                    handleFuzzyTextSubmit(message.id, sliderValue)
                  }
                  disabled={submitted}
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
                  {isLoading ? <CircularProgress size={20} /> : "Submit"}
                </Button>
              </Box>
            </Box>
          );
        })()
      ) : (
        <Box sx={{ display: "flex", alignItems: "center", my: 1 }}>
          <Typography
            variant="body1"
            sx={{
              mr: 1,
              whiteSpace: "nowrap",
              color: submitted ? "white" : "#3B77BC",
            }}
          >
            New Concept:
          </Typography>
          <TextField
            size="small"
            fullWidth
            multiline
            value={userInput || ""}
            onChange={(e) => handleFuzzyTextChange(message.id, e.target.value)}
            disabled={
              submitted ||
              (userSelectedIndices && userSelectedIndices.length > 0)
            }
            placeholder="Enter your input here..."
            sx={{
              my: 1,
              "& .MuiInputBase-input": {
                color: submitted ? "white" : "initial",
              },
              "& .MuiOutlinedInput-root .MuiOutlinedInput-notchedOutline": {
                borderColor: submitted ? "white" : "initial",
              },
              "& .MuiOutlinedInput-root.Mui-disabled .MuiOutlinedInput-notchedOutline":
                { borderColor: submitted ? "white !important" : "initial" },
              "& .MuiOutlinedInput-root.Mui-disabled .MuiOutlinedInput-input": {
                WebkitTextFillColor: submitted ? "white !important" : "initial",
                color: submitted ? "white !important" : "initial",
              },
            }}
          />

          <Button
            variant="contained"
            size="small"
            onClick={() => {
              handleFuzzyTextSubmit(message.id);
            }}
            disabled={submitted || (single_select && !userSelectedIndices?.length && !userInput?.trim())}
            sx={{
              ml: 2,
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
            {isLoading ? (
              <CircularProgress size={20} />
            ) : (
              <Typography variant="body1">Submit</Typography>
            )}
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default FuzzyTextForm;
