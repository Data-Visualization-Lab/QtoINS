/*
import React, { useState, useCallback, useContext } from "react";
import { Box, Button, Container, TextField } from "@mui/material";
import MyContext from "../state/MyContext";
import FuzzyRecommend from "../components/fuzzyrecommend";

const containerStyles = { padding: 0, margin: 0, maxWidth: "100%" };

const Question = () => {
  const [inputValue, setInputValue] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const { setResult, setFuzzyRecommend } = useContext(MyContext);

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value);
  };

  const handleSubmit = useCallback(async () => {
    try {
      const response = await fetch("/gettext", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: inputValue }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch data");
      }

      const result = await response.json();

      if (response.ok) {
        setMessage(result.message);
        if (result.fuzzy) {
          setFuzzyRecommend(result.recommend);
         console.log(result.recommend)
        } else {
          setResult(result.data);
        }
      }
    } catch (error) {
      setMessage("An error occurred while fetching data.");
    }
  }, [inputValue, setResult, setFuzzyRecommend]);

  return (
    <Container style={containerStyles}>
      <Box display="flex" alignItems="center" marginTop={2} style={{ width: "100%" }}>
        <TextField
          label="Enter your Question"
          variant="outlined"
          value={inputValue}
          onChange={handleInputChange}
          fullWidth
        />
        <Button
          variant="contained"
          color="primary"
          onClick={handleSubmit}
          style={{ marginLeft: "8px" }}
        >
          Submit
        </Button>
      </Box>
      {message && <Box marginTop={2}>{message}</Box>}
      <FuzzyRecommend></FuzzyRecommend>
    </Container>
  );
};

export default Question;
*/
export default {};
