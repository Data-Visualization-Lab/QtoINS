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

      
      <Box
        sx={{
          height: "30%",
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

                boxShadow: 0,
                border: "none",
                maxHeight: "100%",
                "&::-webkit-scrollbar": {
                  display: "none",
                },
                overflowY: "auto",
                backgroundColor: global.backgroundColor,


                "& table": {
                  borderCollapse: "collapse",
                },


                "& th, & td": {
                  border: "none !important",
                },


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

                  "& .MuiTableCell-stickyHeader": {
                    borderBottom: "none",
                    boxShadow: "none",

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
                          border: "none",
                          padding: "8px 16px",
                          fontSize: "1.2rem",
          
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
                  mt: -1.9,
                  pt: 0,
                  "& .MuiTablePagination-toolbar": {
                    justifyContent: "flex-end",
                    py: 0,
                    minHeight: "1px"
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
