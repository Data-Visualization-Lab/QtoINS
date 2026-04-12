import React from "react";
import {
  Box,
  Typography,
  Button,
  FormControlLabel,
  Checkbox,
  CircularProgress,
} from "@mui/material";
import { FuzzyStringMessage } from "../data/messageTypes";

interface FuzzyStringFormProps {
  message: FuzzyStringMessage;
  handleFuzzyStringToggle: (msgId: number, index: number) => void;
  handleFuzzyStringSubmit: (msgId: number) => void;
}

const FuzzyStringForm: React.FC<FuzzyStringFormProps> = ({
  message,
  handleFuzzyStringToggle,
  handleFuzzyStringSubmit,
}) => {
  const { keyName, solution, userSelectedIndices, submitted, submitting } =
    message;

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
        <>
          Select option(s) for:{" "}
          {(() => {

const [head, uuidAndTail = ""] = (keyName ?? "").trim().split("+");


const tail = uuidAndTail
  .replace(
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\s*/i,
    ""
  )
  .trim()
  .replace(/_/g, " ");

return (
  <>
    
    <mark style={{ backgroundColor: "#F8D86A", fontWeight: "bold" }}>
      {head.trim().replace(/_/g, " ")}
    </mark>

    
    {tail && <> - {tail}</>}
  </>
);
          })()}
        </>
      </Typography>

      {solution &&
        solution.map((opt, i) => {
          const checked = userSelectedIndices?.includes(i) || false;
          return (
            <FormControlLabel
              key={i}
              control={
                <Checkbox
                  checked={checked}
                  onChange={() => handleFuzzyStringToggle(message.id, i)}
                  disabled={submitted || submitting}
                  sx={{
                    color: "#3B77BC",
                    "&.Mui-checked": {
                      color: "black",
                    },
                  }}
                />
              }
              label={<Typography variant="body1">{opt}</Typography>}
              sx={{
                "& .MuiFormControlLabel-label": {
                  color: submitted ? (checked ? "white" : "black") : "#3B77BC",
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

      <Button
        variant="contained"
        size="small"
        onClick={() => handleFuzzyStringSubmit(message.id)}
        disabled={submitted || submitting}
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
        ) : (
          <Typography variant="body1">Submit</Typography>
        )}
      </Button>
    </Box>
  );
};

export default FuzzyStringForm;
