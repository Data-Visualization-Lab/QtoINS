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

// 导入图片
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
  // 辅助函数：如果文本以 "I generate chart" 或 "I generate charts" 开头，
  // 则将前缀后的内容用 <mark> 标签高亮显示
  const renderText = (text: string) => {
    // 如果文本匹配 "I generate a chart to answer the question:" 后跟空格
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
  
    // 若不匹配 prefixRegex，则对文本做以下替换：
    // 1. 被单引号包围的所有文本 ('...') 都转换为粗体显示  
    // 2. 出现 nominal、quantitative 或 categorical 的单词转换为粗体（不区分大小写）  
    // 3. 如果出现 rows 或 columns，则把其前面的那个单词和 rows/columns 一起粗体显示
  
    // 构造一个组合正则表达式：
    // 1) '([^']+)' —— 匹配单引号内的内容（不含单引号本身的捕获组）
    // 2) \b(nominal|quantitative|categorical)\b —— 匹配目标单词（不区分边界）
    // 3) (\S+\s+(rows|columns)) —— 匹配非空白字符开头的单词和紧随的 rows 或 columns
    const pattern = /'([^']+)'|\b(nominal|quantitative|categorical)\b|(\S+\s+(rows|columns))/gi;
  
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
  
    while ((match = pattern.exec(text)) !== null) {
      // 将匹配前的部分作为普通文本添加
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
  
      // 根据捕获组决定如何处理匹配的文本
      if (match[1]) {
        // 捕获组1：单引号内的内容，把整段（含单引号）设为粗体
        parts.push(<strong key={match.index}>{`'${match[1]}'`}</strong>);
      } else if (match[2]) {
        // 捕获组2：匹配到 nominal, quantitative 或 categorical
        parts.push(<strong key={match.index}>{match[2]}</strong>);
      } else if (match[3]) {
        // 捕获组3：匹配到前面的单词及其后面的 rows/columns
        parts.push(<strong key={match.index}>{match[3]}</strong>);
      }
  
      lastIndex = pattern.lastIndex;
    }
  
    // 将最后剩余的文本添加到结果中
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }
  
    return <>{parts}</>;
  };

  // 仅显示第一个未提交的 fuzzy_text 消息（其它待处理的隐藏）
  const firstUnsubmittedFuzzyTextIndex = messages.findIndex(
    (m) => m.role === "fuzzy_text" && !m.submitted
  );

  // 对于 fuzzy_string 消息（multiple_string 类型），仅显示第一个未提交的
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
            // 若 fuzzy_string 消息不属于 multiple_string 类型，则直接显示
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
          // system 与 user 消息
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
