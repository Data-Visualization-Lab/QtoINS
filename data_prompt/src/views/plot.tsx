import React from "react";
import { VegaLite } from "react-vega";
import { useMyContext } from "../state/MyContext";
import { global } from "../styles/global";
import { Box, Typography, Paper } from "@mui/material";

interface VisDataItem {
  [key: string]: {
    VisualRecommend_instance_result?: {
      width?: number;
      height?: number;
      autosize?: any;
      [key: string]: any;
    };
    description?: string;
    [key: string]: any;
  };
}

const Plot: React.FC = () => {
  const { visData, setSelectedSpec } = useMyContext();

  let parsedData: any = visData;
  if (typeof visData === "string") {
    try {
      parsedData = JSON.parse(visData);
    } catch (error) {
      console.error("解析 visData 失败：", error);
      return <Typography>数据格式错误</Typography>;
    }
  }

  const visDataArray = Array.isArray(parsedData)
    ? parsedData
    : Object.values(parsedData);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 50px)",
        gap: 1,
        p: 0,
        backgroundColor: global.backgroundColor,
      }}
    >
      <Box
        sx={{
          border: `2px solid ${global.borderColor}`,
          height: "100%",
          borderRadius: 1,
          p: 1,
          backgroundColor: global.backgroundColor,
          boxShadow: 3,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <Typography
          variant="h6"
          sx={{ fontWeight: "bold", color: global.textColor }}
        >
          Preview Chart View
        </Typography>
        <Box
          sx={{
            width: "100%",
            height: "4px",
            backgroundColor: global.borderColor,
            mb: 0,
          }}
        />
        <Box
          sx={{
            flexGrow: 1,
            overflowY: "auto",
            scrollbarWidth: "none",
            "&::-webkit-scrollbar": {
              display: "none",
            },
          }}
        >
          <Paper
            elevation={3}
            sx={{
              display: "flex",
              flexDirection: "column",
              width: "100%",
              minHeight: "100%",
              boxSizing: "border-box",
              backgroundColor: global.backgroundColor,
            }}
          >
            {(!visDataArray || visDataArray.length === 0) && (
              <Typography
                align="center"
                sx={{ mt: "2rem", color: global.placeholderColor }}
              >
                No Chart
              </Typography>
            )}

{visDataArray &&
  visDataArray.length > 0 &&
  visDataArray.map((item: VisDataItem) =>
    Object.entries(item).map(([key, record]) => {
      const originalSpec = record?.VisualRecommend_instance_result;

      if (!originalSpec) {
        return (
          <Typography key={key}>
            数据 {key} 中没有 VisualRecommend_instance_result 字段，无法绘图
          </Typography>
        );
      }
      const { width, height, ...restSpec } = originalSpec;
      return (
        <Paper
          key={key} // 使用唯一的 key
          onClick={() => setSelectedSpec({ ...record, uuid: key })}
          sx={{
            cursor: "pointer",
            mb: "1rem",
            mt: "1rem",
            border: `1px solid ${global.borderColor}`,
            borderRadius: "8px",
            overflow: "hidden",
            transition:
              "transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out",
            "&:hover": {
              transform: "scale(1.02)",
              boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            },
            height: 300,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              p: "0.5rem 1rem",
              backgroundColor: global.buttonColor,
              color: global.backgroundColor,
              fontSize: "14px",
            }}
          >
            {record.description
              ? `Description: ${record.description}`
              : "No description"}
          </Box>
  
          <Box
            sx={{
              flex: 1,
              p: "1.2rem",
              backgroundColor: global.panelBackground || "#f0f0f0",
            }}
          >
            <Box
              sx={{
                width: "100%",
                height: "100%",
                position: "relative",
              }}
            >
<VegaLite
  key={key}  // 仅使用 uuid 作为 key
  spec={{
    ...restSpec,
    width: "container" as any,
    height: "container" as any,
    autosize: {
      type: "fit",
      contains: "padding",
    },
  }}
  actions={false}
  style={{ width: "100%", height: "100%" }}
/>

            </Box>
          </Box>
        </Paper>
      );
    })
  )}


          </Paper>
        </Box>
      </Box>
    </Box>
  );
};

export default Plot;
