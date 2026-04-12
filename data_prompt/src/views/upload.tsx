import { useEffect, useState, useRef } from "react";
import { global } from "../styles/global";
import {
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Box,
  Typography,
} from "@mui/material";
import Papa from "papaparse";
import ChatBox from "./ChatBox";

interface CsvData {
  [key: string]: any;
}

const Upload = () => {
  const [file, setFile] = useState<File | null>(null);
  const [csvData, setCsvData] = useState<Record<string, string>[]>([]);
  const [page, setPage] = useState(0);
  const [message, setMessage] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [snackbarOpen, setSnackbarOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const rowsPerPage = 5;

  const handleChangePage = (
    event: React.MouseEvent<HTMLButtonElement> | null,
    newPage: number
  ) => {
    setPage(newPage);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      const selectedFile = event.target.files[0];
      setFile(selectedFile);
      uploadCsvToFlask(selectedFile);
    }
  };

  const uploadCsvToFlask = async (fileToUpload: File) => {
    const formData = new FormData();
    const fileName = fileToUpload.name;
    const baseName =
      fileName.lastIndexOf(".") !== -1
        ? fileName.substring(0, fileName.lastIndexOf("."))
        : fileName;

    formData.append("csv_file", fileToUpload);
    formData.append("file_name", baseName);

    try {
      const response = await fetch("/upload", {
        method: "POST",
        body: formData,
      });
      const result = await response.json();
      if (response.ok) {
        setMessage(`File uploaded successfully: ${result.message}`);
        setDescription(result.description);
      } else {
        setMessage(`Upload failed: ${result.error}`);
      }
      setSnackbarOpen(true);
    } catch (error) {
      setMessage(`Error: ${error}`);
      setSnackbarOpen(true);
    }
  };

  useEffect(() => {
    if (file) {
      Papa.parse<CsvData>(file, {
        complete: (result: Papa.ParseResult<CsvData>) => {
          const parsedData = result.data;
          setCsvData(parsedData);
        },
        header: true,
      });
    }
  }, [file]);

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
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        accept=".csv"
        onChange={handleFileUpload}
      />

      {/* 修改后的 Table View 部分，采用了与 ChatBox (plot) 类似的样式 */}
      <Box
        sx={{
          height: "30%",
          display: "flex",
          flexDirection: "column",
          border: `2px solid ${global.borderColor}`, // 修改：边框加粗为2px
          borderRadius: 2, // 修改：圆角由1调整为2
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
          Table View
        </Typography>
        <Box
          sx={{
            width: "100%",
            height: "4px",
            backgroundColor: global.borderColor,
            mb: 1,
          }}
        />
        <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
          <Button
            onClick={() => {
              fileInputRef.current?.click();
            }}
            variant="contained"
            color="primary"
            sx={{ backgroundColor: global.buttonColor }}
          >
            Upload
          </Button>
        </Box>

        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            "&::-webkit-scrollbar": {
              display: "none",
            },
            scrollbarWidth: "none",
            msOverflowStyle: "none",
          }}
        >
          {csvData.length > 0 ? (
            <TableContainer
              sx={{
                borderRadius: 2,
                // 如果不需要任何阴影或边框，可以直接去掉或改为 0
                boxShadow: 0,
                border: "none",
                maxHeight: "100%",
                "&::-webkit-scrollbar": {
                  display: "none",
                },
                overflowY: "auto",
                backgroundColor: global.backgroundColor,

                // 让内层 Table 直接无边框渲染
                "& table": {
                  borderCollapse: "collapse",
                },

                // 让所有单元格都不再显示边框
                "& th, & td": {
                  border: "none !important",
                },

                // 如果 sticky header 仍出现边线，可针对它进行强制覆盖
                "& .MuiTableCell-stickyHeader": {
                  borderBottom: "none !important",
                },
              }}
            >
              <Table
                stickyHeader
                sx={{
                  "& .MuiTableCell-root": {
                    borderBottom: "none",
                  },
                  "& .MuiTableCell-head": {
                    borderBottom: "none",
                  },
                  // 如果 stickyHeader 带来了阴影或边线，也可以覆盖
                  "& .MuiTableCell-stickyHeader": {
                    borderBottom: "none",
                    boxShadow: "none",
                    // 如果有其他竖向分割线，也可以试着设置 borderRight: "none" 等
                  },
                }}
              >
                <TableHead>
                  <TableRow>
                    {Object.keys(csvData[0]).map((key, index) => (
                      <TableCell
                      align="center"
                        key={index}
                        sx={{
                          fontWeight: "bold",
                          backgroundColor: global.buttonColor,
                          color: global.backgroundColor,
                          border: "none", // 移除所有边框
                          padding: "8px 16px", // 增加内边距
                          fontSize: "1.2rem",  // 增大字体大小
          
                        }}
                      >
                        {key}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {csvData
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((row, rowIndex) => (
                      <TableRow key={rowIndex} hover>
                        {Object.values(row).map((val, colIndex) => {
                          // 判断是否为数字：当值非空且转换为数字不是 NaN 时，认为是数字
                          const isNumeric =
                            typeof val === "string" &&
                            val.trim() !== "" &&
                            !isNaN(Number(val));
                          return (
                            <TableCell
                              key={colIndex}
                              align={isNumeric ? "right" : "left"}
                              sx={{ padding: "14.5px 8.1px" }}
                            >
                              {val}
                            </TableCell>
                          );
                        })}
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
              <TablePagination
                component="div"
                count={csvData.length - 1}
                page={page}
                onPageChange={handleChangePage}
                rowsPerPage={rowsPerPage}
                rowsPerPageOptions={[rowsPerPage]}
                sx={{
                  mt: -1.9,      // 外层 margin-top 设为 0
                  pt: 0,      // 外层 padding-top 设为 0
                  "& .MuiTablePagination-toolbar": {
                    justifyContent: "flex-end",
                    py: 0,            // 内部工具条的上下 padding 设为 0
                    minHeight: "1px" // 默认工具条高度通常较高，可根据需求设置为较低高度，如 32px
                  },
                }}
              />
            </TableContainer>
          ) : (
            <Typography
              align="center"
              sx={{ mt: "2rem", color: global.placeholderColor }}
            >
              No Data available
            </Typography>
          )}
        </Box>
      </Box>

      {/* ChatBox 部分保持不变 */}
      <Box
        sx={{
          border: `2px solid ${global.borderColor}`,
          borderRadius: 2,
          p: 1,
          flex: 7,
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
          Chatbot Query View
        </Typography>
        <Box
          sx={{
            width: "100%",
            height: "4px",
            backgroundColor: global.borderColor,
            mb: 0,
          }}
        />
        <Box sx={{ flexGrow: 1, overflow: "hidden" }}>
          <ChatBox description={description} />
        </Box>
      </Box>
    </Box>
  );
};

export default Upload;
