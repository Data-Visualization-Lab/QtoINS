// PlotPreview.tsx
import React, { useState, useEffect } from "react";
import { VegaLite } from "react-vega";
import { useMyContext } from "../state/MyContext";
import { global } from "../styles/global";
import {
  Box,
  Typography,
  TextField,
  Button,
  CircularProgress,
} from "@mui/material";

const inputFieldHeight = "30px";

const PlotPreview: React.FC = () => {
  const { selectedSpec, setSelectedSpec, visData, setVisData } = useMyContext();
  const [chartInput, setChartInput] = useState("");
  const [insightList, setInsightList] = useState<
    Array<{ key: string; value: string }>
  >([]);
  const [loading, setLoading] = useState(false);

  // 根据 selectedSpec.insight 初始化 insightList
  useEffect(() => {
    if (selectedSpec && selectedSpec.insight) {
      const insightData = selectedSpec.insight;
      if (Array.isArray(insightData)) {
        setInsightList(insightData);
      } else if (typeof insightData === "object") {
        const list = Object.entries(insightData).map(([key, value]) => ({
          key,
          value: value as string,
        }));
        setInsightList(list);
      } else {
        setInsightList([{ key: "", value: insightData }]);
      }
    } else {
      setInsightList([]);
    }
  }, [selectedSpec]);

  // 当前大图的 Vega-Lite 配置
  const spec = selectedSpec?.VisualRecommend_instance_result;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setChartInput(e.target.value);
  };

  const handleInsightKeyChange = (index: number, newKey: string) => {
    setInsightList((prev) => {
      const newList = [...prev];
      newList[index] = { ...newList[index], key: newKey };
      return newList;
    });
  };

  const handleInsightValueChange = (index: number, newValue: string) => {
    setInsightList((prev) => {
      const newList = [...prev];
      newList[index] = { ...newList[index], value: newValue };
      return newList;
    });
  };

  // 处理 insight 更新（逻辑不变，保持更新对应 spec 的 insight）
  const handleStepClick = async (index: number) => {
    if (loading) return;
    setLoading(true);
    const stepsToSend = insightList.slice(0, index + 1);
    try {
      const payload = {
        steps: stepsToSend,
        key: selectedSpec?.uuid,
      };
      const response = await fetch("/api/changeinsight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();

      if (!selectedSpec) return;
      let updatedSpec = { ...selectedSpec };

      if (result.changeinsight && Array.isArray(result.changeinsight)) {
        const newInsightList = [
          ...insightList.slice(0, index),
          ...result.changeinsight,
        ];
        setInsightList(newInsightList);
        updatedSpec.insight = newInsightList;
      }

      if (result.vegalite !== null) {
        updatedSpec.VisualRecommend_instance_result = result.vegalite;
      }

      // 更新全局 selectedSpec
      setSelectedSpec(updatedSpec);

      // 更新 visData 中对应的 spec，其他图保持不变
      setVisData((prevVisData: any[]) => {
        return prevVisData.map((item) => {
          const currentKey = Object.keys(item)[0];
          if (currentKey === selectedSpec.uuid) {
            return { [selectedSpec.uuid]: updatedSpec };
          }
          return item;
        });
      });
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 仅更新对应 uuid 的图，同时保留其他图表
  const handleSubmit = async () => {
    if (!selectedSpec?.uuid) {
      console.error("selectedSpec 或 uuid 不存在");
      return;
    }
    setLoading(true);
    try {
      const payload = {
        vegaliteSpec: selectedSpec.VisualRecommend_instance_result,
        chartParam: chartInput,
        key: selectedSpec.uuid,
      };

      const response = await fetch("/api/changechart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = await response.json();

      if (!result.chart) {
        console.error("API 没有返回有效的 chart 数据");
        return;
      }

      // 后端返回新的 key，若有则用其替换，否则保留原 uuid
      const updatedKey = result.key || selectedSpec.uuid;
      const updatedSpec = {
        ...selectedSpec,
        uuid: updatedKey,
        VisualRecommend_instance_result: result.chart,
      };

      setSelectedSpec(updatedSpec);

      // 更新 visData 中对应的 spec 对象（只更新匹配的那个，其他不动）
      setVisData((prevVisData: any[]) => {
        // 先遍历，找到是否已经存在相同的 key
        let found = false;
        const updatedArray = prevVisData.map((item) => {
          const currentKey = Object.keys(item)[0];
          // 注意确保 currentKey 与 updatedKey 是同一类型并且没有多余空格等问题
          if (currentKey === updatedKey) {
            found = true;
            return { [updatedKey]: updatedSpec };
          }
          return item;
        });
        // 如果找不到，则追加
        if (!found) {
          updatedArray.push({ [updatedKey]: updatedSpec });
        }
        return updatedArray;
      });
    } catch (error) {
      console.error("handleSubmit 出错:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "calc(100vh - 50px)",
        gap: 0,
        p: 0,
        backgroundColor: global.backgroundColor,
      }}
    >
      {loading && (
        <Box
          sx={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor:
              global.loadingOverlayBackground || "rgba(255,255,255,0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
        >
          <CircularProgress size={36} sx={{ color: global.buttonColor }} />
        </Box>
      )}

      {/* 上半部分：大图 */}
      <Box
        sx={{
          position: "relative",
          height: "50%",
          display: "flex",
          flexDirection: "column",
          border: `2px solid ${global.borderColor}`,
          borderRadius: 2,
          p: 1,
          backgroundColor: global.backgroundColor,
          boxShadow: 3,
          overflow: "hidden",
        }}
      >
        <Typography
          variant="h6"
          sx={{ fontWeight: "bold", color: global.textColor }}
        >
          Expanded Chart View
        </Typography>
        <Box
          sx={{
            width: "100%",
            height: "4px",
            backgroundColor: global.borderColor,
            mb: 1,
          }}
        />
        {selectedSpec ? (
          <Box
            sx={{
              p: "0px",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              flexGrow: 1,
              pt: "0px",
            }}
          >
            {/* Another Box to ensure full width/height usage */}
            <Box sx={{ width: "80%", height: 500 }}>
              <VegaLite
                spec={{
                  ...spec,
                  // Let the chart fill whatever space is available
                  width: "container",
                  height: 450,

                  autosize: {
                    type: "fit",
                    contains: "padding",
                  },
                }}
                // Force the React element itself to fill the parent Box
                style={{ width: "100%", height: "100%" }}
              />
            </Box>
          </Box>
        ) : (
          <Typography
            align="center"
            sx={{ mt: "2rem", color: global.placeholderColor }}
          >
            Please select a chart.
          </Typography>
        )}

        {/* 固定在底部的参数输入区域 */}
        <Box
          component="form"
          sx={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
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
            value={chartInput}
            onChange={handleInputChange}
            placeholder="Change Chart type (eg. change pie chart to bar chart)"
            sx={{ border: `1px solid ${global.borderColor}` }}
          />
          <Button
            type="submit"
            variant="contained"
            color="primary"
            onClick={handleSubmit}
            sx={{ backgroundColor: global.buttonColor }}
            disabled={loading}
          >
            {loading ? <CircularProgress size={20} color="inherit" /> : "Send"}
          </Button>
        </Box>
      </Box>

      {/* 下半部分：Insight 及修改参数 */}
      <Box
        sx={{
          border: `2px solid ${global.borderColor}`,
          borderRadius: 2,
          p: 1,
          flex: 1,
          backgroundColor: global.backgroundColor,
          boxShadow: 3,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <Typography
          variant="h6"
          sx={{ fontWeight: "bold", color: global.textColor }}
        >
          Insight View
        </Typography>
        <Box
          sx={{
            width: "100%",
            height: "4px",
            backgroundColor: global.borderColor,
            mb: 1,
          }}
        />
        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            pr: "2rem",
            mb: "1rem",
            "&::-webkit-scrollbar": { display: "none" },
          }}
        >
          {selectedSpec &&
            insightList.length > 0 &&
            insightList.map((item, index) => (
              <Box key={index} sx={{ mb: "1rem" }}>
                <Box sx={{ display: "flex", alignItems: "center" }}>
                  <Box
                    sx={{
                      width: "30px",
                      height: inputFieldHeight,
                      backgroundColor: "#ECECED",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      mr: "0.1rem",
                      borderRadius: 1,
                    }}
                  >
                    {`${index + 1}`}
                  </Box>
                  <TextField
                    variant="outlined"
                    size="small"
                    value={item.key}
                    onChange={(e) =>
                      handleInsightKeyChange(index, e.target.value)
                    }
                    placeholder="Key"
                    sx={{
                      width: "360px",
                      mr: "0.1rem",
                      "& .MuiInputBase-root": {
                        height: inputFieldHeight,
                        padding: 0,
                      },
                    }}
                    InputProps={{
                      style: { height: inputFieldHeight, padding: "0 0px" },
                    }}
                  />
                  <Button
                    variant="contained"
                    color="primary"
                    sx={{
                      backgroundColor: global.buttonColor,
                      height: inputFieldHeight,
                      cursor: loading ? "not-allowed" : "pointer",
                    }}
                    onClick={() => !loading && handleStepClick(index)}
                  >
                    submit
                  </Button>
                </Box>
                <TextField
                  variant="outlined"
                  size="small"
                  value={item.value}
                  onChange={(e) =>
                    handleInsightValueChange(index, e.target.value)
                  }
                  placeholder="Content"
                  multiline
                  fullWidth
                  minRows={1}
                  inputProps={{ readOnly: true }}
                  InputProps={{
                    sx: {
                      "& fieldset": {
                        border: "none",
                      },
                      backgroundColor: "#ECECED",
                      padding: "0.1rem",
                    },
                  }}
                  sx={{ mt: "0.5rem", ml: "calc(30px + 0.1rem)" }}
                />
              </Box>
            ))}
        </Box>
      </Box>
    </Box>
  );
};

export default PlotPreview;
