import React from "react";
import { Paper, Box, TextField, Button, CircularProgress } from "@mui/material";
import { useChatLogic } from "../hooks/useChatLogic";
import MessageList from "./MessageList";
import { global } from "../styles/global";

interface ChatBoxProps {
  description?: string;
}

const ChatBox: React.FC<ChatBoxProps> = ({ description }) => {
  const {
    messages,
    inputText,
    setInputText,
    handleSend,
    isLoading,
    handleRunFollowups,
    handleFuzzyTextChange,
    handleFuzzyTextSubmit,
    handleFuzzyTextToggle,
    handleFuzzyStringToggle,
    handleFuzzyStringSubmit,
  } = useChatLogic(description);

  return (
    <Paper
      elevation={3}
      sx={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        boxSizing: "border-box",
        backgroundColor: global.backgroundColor,
      }}
    >
      <Box
        sx={{
          flex: 1,
          overflowY: "auto",
          p: 2,
          scrollbarWidth: "none",
          msOverflowStyle: "none",
          "&::-webkit-scrollbar": {
            display: "none",
          },
        }}
      >
        <MessageList
          messages={messages}
          handleFuzzyTextChange={handleFuzzyTextChange}
          handleFuzzyTextSubmit={handleFuzzyTextSubmit}
          handleFuzzyTextToggle={handleFuzzyTextToggle}
          handleFuzzyStringToggle={handleFuzzyStringToggle}
          handleFuzzyStringSubmit={handleFuzzyStringSubmit}
          handleFollowupActionSubmit={handleRunFollowups}
        />
      </Box>

      <Box
        component="form"
        onSubmit={handleSend}
        sx={{
          position: "sticky",
          bottom: 0,
          display: "flex",
          gap: 1,
          alignItems: "center",
          p: 1,
          boxSizing: "border-box",
          backgroundColor: global.backgroundColor,
          zIndex: 10,
        }}
      >
        <TextField
          fullWidth
          size="small"
          placeholder="Type your message..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          sx={{
            border: `1px solid ${global.borderColor}`,
          }}
        />
        <Button type="submit" variant="contained" disabled={isLoading} sx={{ backgroundColor: global.buttonColor }}>
          {isLoading ? <CircularProgress size={20} /> : "Send"}
        </Button>
      </Box>
    </Paper>
  );
};

export default ChatBox;
