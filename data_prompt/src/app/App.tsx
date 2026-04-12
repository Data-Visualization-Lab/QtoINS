import './index.css'; 
import React from 'react';
import { MyProvider } from '../state/MyProvider';
import Upload from '../views/upload';
import Plot from '../views/plot';
import PlotPreview from '../views/PlotPreview';
import { Box, Stack, Typography } from '@mui/material';
import logo from '../assets/len.png';
import { global } from '../styles/global';
const App: React.FC = () => (
  <MyProvider>
    <Stack direction="column" sx={{ height: "100vh", margin: "0px 5px 0px 5px", padding: 0 }}>
      <Box sx={{ padding: '0.2rem', display: 'flex', alignItems: 'center', backgroundColor: global.backgroundColor}}>
        <img 
          src={logo} 
          alt="logo" 
          style={{ width: '38px', height: '30px', marginRight: '8px' }} 
        />
        <Typography variant="h6">QtoINS</Typography>
      </Box>
    
      <Stack
        direction="row"
        spacing={0}
        sx={{
          flex: 1,
          overflowX: "auto", 
          overflowY: "hidden", 
          "&::-webkit-scrollbar": { display: "none" },
          scrollbarWidth: "none",
          msOverflowStyle: "none",
        }}
      >
        <Box sx={{ flex: 5, minWidth: 0 }}>
          <Upload />
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Plot />
        </Box>
        <Box sx={{ flex: 4, minWidth: 0 }}>
          <PlotPreview />
        </Box>
      </Stack>
    </Stack>
  </MyProvider>
);

export default App;
