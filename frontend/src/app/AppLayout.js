import { useState } from 'react';
import { AppBar, Box, Button, Drawer, IconButton, Toolbar, Typography, useMediaQuery, Alert } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import { Link, Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { useAuth } from './AuthContext';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { errorMessage } from '../lib/api';
const width=260;
export default function AppLayout(){
 const desktop=useMediaQuery('(min-width:1024px)'),[desktopOpen,setDesktopOpen]=useState(true),[mobileOpen,setMobileOpen]=useState(false),[error,setError]=useState('');
 const branding=useQuery({queryKey:['branding'],queryFn:async ()=>(await api.get('branding/')).data});
 const auth=useAuth(),open=desktop?desktopOpen:mobileOpen;
 const toggle=()=>desktop?setDesktopOpen(!desktopOpen):setMobileOpen(!mobileOpen);
 const logout=async()=>{try{await auth.signOut();}catch(e){setError(errorMessage(e));}};
 return <Box sx={{display:'flex',minHeight:'100vh'}}><AppBar position="fixed" sx={{zIndex:t=>t.zIndex.drawer+1,background:`linear-gradient(100deg,${branding.data?.primary_color || '#021156'} 65%,${branding.data?.secondary_color || '#a40404'})`}}><Toolbar><IconButton color="inherit" aria-label="Toggle navigation" aria-expanded={open} onClick={toggle}><MenuIcon /></IconButton><Typography sx={{ml:2,fontWeight:700,flexGrow:1}}>{branding.data?.company_name || 'HRDESK'}</Typography><Typography sx={{display:{xs:'none',sm:'block'},mr:2}}>{auth.user.first_name}</Typography><Button component={Link} to="/change-password" color="inherit">Password</Button><Button onClick={logout} color="inherit">Sign out</Button></Toolbar></AppBar>
 <Drawer variant={desktop?'persistent':'temporary'} open={open} onClose={()=>setMobileOpen(false)} sx={{width:desktop&&open?width:0,flexShrink:0,'& .MuiDrawer-paper':{width,bgcolor:branding.data?.sidebar_color || '#0d339c',color:'#fff'}}}><Toolbar /><Sidebar menu={auth.menu} onNavigate={()=>setMobileOpen(false)} /><Typography variant="caption" sx={{mt:'auto',p:2}}>HRDESK · 1.0</Typography></Drawer><Box component="main" sx={{flexGrow:1,minWidth:0,p:{xs:2,md:4}}}><Toolbar />{error && <Alert severity="error">{error}</Alert>}<Outlet /></Box></Box>;
}
