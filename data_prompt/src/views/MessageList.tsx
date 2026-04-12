// views/MessageList.tsx
import React from "react";
import { List, ListItem, Box, Typography } from "@mui/material";
import {
  Message,
  FuzzyTextMessage,
  FuzzyStringMessage,
  FollowupActionMessage,
  FollowupActionPayload,
} from "../data/messageTypes";
import FuzzyTextForm from "../components/FuzzyTextForm";
import FuzzyStringForm from "../components/FuzzyStringForm";
import FollowupActionForm from "../components/FollowupActionForm";


import robotImg from "../assets/robot_icon.jpg";
import userImg from "../assets/human_icon.jpg";

interface MessageListProps {
  messages: Message[];
  handleFuzzyTextChange: (msgId: number, newValue: string) => void;
  handleFuzzyTextSubmit: (msgId: number) => void;
  handleFuzzyTextToggle: (msgId: number, index: number) => void;
  handleFuzzyStringToggle: (msgId: number, index: number) => void;
  handleFuzzyStringSubmit: (msgId: number) => void;
  handleFollowupActionSubmit: (
    msgId: number,
    payload?: FollowupActionPayload
  ) => void;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  handleFuzzyTextChange,
  handleFuzzyTextSubmit,
  handleFuzzyTextToggle,
  handleFuzzyStringToggle,
  handleFuzzyStringSubmit,
  handleFollowupActionSubmit,
}) => {


  const renderText = (text: string) => {

    const prefixRegex = /^I generate a chart to answer the question:\s*/;
    const prefixMatch = text.match(prefixRegex);
    if (prefixMatch) {
      const prefix = prefixMatch[0];
      const remainder = text.slice(prefix.length);
      return (
        <>
          {prefix}
          <mark style={{ backgroundColor: "#FCEBB1" }}>{remainder}</mark>
        </>
      );
    }
  




  




    const pattern = /'([^']+)'|\b(nominal|quantitative|categorical)\b|(\S+\s+(rows|columns))/gi;
  
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
  
    while ((match = pattern.exec(text)) !== null) {

      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
  

      if (match[1]) {

        parts.push(<strong key={match.index}>{`'${match[1]}'`}</strong>);
      } else if (match[2]) {

        parts.push(<strong key={match.index}>{match[2]}</strong>);
      } else if (match[3]) {

        parts.push(<strong key={match.index}>{match[3]}</strong>);
      }
  
      lastIndex = pattern.lastIndex;
    }
  

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }
  
    return <>{parts}</>;
  };


  const firstUnsubmittedFuzzyTextIndex = messages.findIndex(
    (m) => m.role === "fuzzy_text" && !m.submitted
  );


  const fuzzyStringMessages = messages.filter(
    (m) =>
      m.role === "fuzzy_string" &&
      m.category === "multiple_string" &&
      !m.submitted
  ) as FuzzyStringMessage[];
  const firstUnsubmittedFuzzyStringId =
    fuzzyStringMessages.length > 0 ? fuzzyStringMessages[0].id : null;

  return (
    <Box sx={{ flex: 1, overflowY: "auto", mb: 2 }}>
      <List sx={{ display: "flex", flexDirection: "column" }}>
        {messages.map((msg, index) => {
          if (msg.role === "fuzzy_text") {
            const fuzzyMsg = msg as FuzzyTextMessage;
            if (!fuzzyMsg.submitted && index !== firstUnsubmittedFuzzyTextIndex) {
              return null;
            }
            return (
              <ListItem
                key={fuzzyMsg.id}
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "flex-end",
                }}
              >
                <FuzzyTextForm
                  message={fuzzyMsg}
                  handleFuzzyTextChange={handleFuzzyTextChange}
                  handleFuzzyTextSubmit={handleFuzzyTextSubmit}
                  handleFuzzyTextToggle={handleFuzzyTextToggle}
                />
                <img
                  src={userImg}
                  alt="user"
                  style={{ width: 25, height: 25, marginLeft: 8 }}
                />
              </ListItem>
            );
          }

          if (msg.role === "fuzzy_string" && msg.category === "multiple_string") {
            const fuzzyMsg = msg as FuzzyStringMessage;
            if (!fuzzyMsg.submitted && fuzzyMsg.id !== firstUnsubmittedFuzzyStringId) {
              return null;
            }
            return (
              <ListItem
                key={fuzzyMsg.id}
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "flex-end",
                }}
              >
                <FuzzyStringForm
                  message={fuzzyMsg}
                  handleFuzzyStringToggle={handleFuzzyStringToggle}
                  handleFuzzyStringSubmit={handleFuzzyStringSubmit}
                />
                <img
                  src={userImg}
                  alt="user"
                  style={{ width: 25, height: 25, marginLeft: 8 }}
                />
              </ListItem>
            );
          }

          if (msg.role === "followup_action") {
            const followupMsg = msg as FollowupActionMessage;
            return (
              <ListItem
                key={followupMsg.id}
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "flex-end",
                }}
              >
                <FollowupActionForm
                  message={followupMsg}
                  handleFollowupActionSubmit={handleFollowupActionSubmit}
                />
                <img
                  src={userImg}
                  alt="user"
                  style={{ width: 25, height: 25, marginLeft: 8 }}
                />
              </ListItem>
            );
          }

          if (msg.role === "fuzzy_string") {

            return (
              <ListItem
                key={msg.id}
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "flex-start",
                }}
              >
                <img
                  src={robotImg}
                  alt="robot"
                  style={{ width: 30, height: 30, marginRight: 8 }}
                />
                <Box
                  sx={{
                    maxWidth: "60%",
                    p: 1,
                    borderRadius: 2,
                    bgcolor: "grey.300",
                    color: "text.primary",
                  }}
                >
                  <Typography variant="body1">
                    <strong>Fuzzy String:</strong> {renderText(msg.text)}
                  </Typography>
                </Box>
              </ListItem>
            );
          }

          const isUser = msg.role === "user";
          const imageSrc = isUser ? userImg : robotImg;
          return (
            <ListItem
              key={msg.id}
              sx={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: isUser ? "flex-end" : "flex-start",
              }}
            >
              {!isUser && (
                <img
                  src={imageSrc}
                  alt="robot"
                  style={{ width: 30, height: 30, marginRight: 8 }}
                />
              )}
              <Box
                sx={{
                  maxWidth: "60%",
                  border: "2px solid",        // Adds a border style.
                  borderColor: isUser ? "#ffffff": "#DEDEDE",
                  p: 1,
                  borderRadius: 2,
                  bgcolor: isUser ? "#3B77BC" : "#ffffff",
                  color: isUser ? "primary.contrastText" : "#2D2E35",
                }}
              >
                <Typography variant="body1" whiteSpace="pre-line">
                  {renderText(msg.text)}
                </Typography>
              </Box>
              {isUser && (
                <img
                  src={imageSrc}
                  alt="user"
                  style={{ width: 25, height: 25, marginLeft: 8 }}
                />
              )}
            </ListItem>
          );
        })}
      </List>
    </Box>
  );
};

export default MessageList;
