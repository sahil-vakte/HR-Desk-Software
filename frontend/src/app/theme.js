import { createTheme } from '@mui/material/styles';
export const theme = createTheme({
  palette: { primary: { main: '#021156' }, secondary: { main: '#ea0606' }, background: { default: '#f5f6fa' } },
  typography: { fontFamily: 'Arial, Helvetica, sans-serif', h1: { fontSize: '2rem', fontWeight: 700 } },
  shape: { borderRadius: 8 },
  components: { MuiButton: { styleOverrides: { root: { textTransform: 'none' } } } },
});
