import { useEffect, useState } from 'react';
import { Alert, Button, CssBaseline, ThemeProvider, Typography } from '@mui/material';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import 'dayjs/locale/en-gb';
import { theme } from './theme';
import { createTheme } from '@mui/material/styles';
import { AuthProvider, useAuth } from './AuthContext';
import AppLayout from './AppLayout';
import LoginPage from '../features/auth/LoginPage';
import BootstrapAdminPage from '../features/auth/BootstrapAdminPage';
import ResourcePage from '../features/ResourcePage';
import { DashboardPage,AttendancePage,BalancePage,TimesheetPage,ReportPage,QueryThread } from '../features/Workflows';
import { UsersPage,RolesPage,SettingsPage } from '../features/AdminPages';
import { EmployeeProfile,NewEmployee } from '../features/EmployeePages';
import { api } from '../lib/api';
import { TaskBoard, WhosWherePage, AttendanceGridPage, AuditPage, DirectoryPage, ApplicantPage, CandidatePage } from '../features/OperationsPages';
const queryClient=new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false}}});
function Protected(){
 const auth=useAuth();
 if(auth.status==='loading')return <Typography sx={{p:4}}>Loading session…</Typography>;
 if(auth.status==='error')return <Alert severity="error" action={<Button onClick={auth.reload}>Retry</Button>}>{auth.message}</Alert>;
 return auth.status==='authenticated'?<Outlet />:<Navigate to="/login" replace />;
}
function Gate({codes=[],adminOnly=false,hrOnly=false,children}){
 const auth=useAuth();
 if((adminOnly && auth.user.role_id!==1) || (hrOnly && ![1,2].includes(auth.user.role_id)) || (codes.length && !codes.some(c=>auth.permissions.includes(c))))return <Alert severity="error">You do not have permission to perform this action.</Alert>;
 return children;
}
function ApplicationRoutes(){
 const auth=useAuth();
 const meta=useQuery({queryKey:['resources',auth.user?.id,auth.user?.role_id],enabled:auth.status==='authenticated',queryFn:async ()=>(await api.get('ui/resources/')).data});
 const resources=(meta.data || []).filter(r=>!['timesheets','employees','tasks','whos-where','attendance/records'].includes(r.key));
 const employees=meta.data?.find(r=>r.key==='employees');
 return <Routes>{['test','cif','reference'].map(k=><Route key={k} path={'/'+k+'/:token'} element={<CandidatePage />} />)}<Route path="/login" element={<LoginPage />} /><Route path="/forgot-password" element={<LoginPage mode="forgot" />} /><Route path="/reset-password/:token" element={<LoginPage mode="reset" />} />
 <Route path="/testing/create-superadmin" element={<BootstrapAdminPage />} />
 <Route element={<Protected />}><Route element={<AppLayout />}><Route index element={<DashboardPage />} /><Route path="/change-password" element={<LoginPage mode="change" />} />
 <Route path="/audit-events" element={<Gate adminOnly><AuditPage /></Gate>} /><Route path="/directory" element={<Gate codes={[58]}><DirectoryPage /></Gate>} /><Route path="/rms/applicants/:id" element={<Gate codes={[47]}><ApplicantPage /></Gate>} /><Route path="/pmo/whos-where" element={<WhosWherePage />} /><Route path="/attendance/admin" element={<Gate codes={[28]} hrOnly><AttendanceGridPage /></Gate>} />
 <Route path="/tasks" element={meta.data?.find(r=>r.key==='tasks')?<TaskBoard resource={meta.data.find(r=>r.key==='tasks')} />:<Typography>No access.</Typography>} />
 <Route path="/attendance" element={<AttendancePage />} /><Route path="/leave/balance" element={<BalancePage />} /><Route path="/timesheets" element={<TimesheetPage />} />
 <Route path="/employees/new" element={<Gate codes={[29]} hrOnly><NewEmployee /></Gate>} /><Route path="/employees/:id" element={<Gate codes={[29]} hrOnly><EmployeeProfile /></Gate>} /><Route path="/me/profile" element={<Gate codes={[71]}><EmployeeProfile own /></Gate>} />
 <Route path="/employees" element={employees?<ResourcePage resource={employees} />:<Typography>Loading permissions…</Typography>} />
 <Route path="/admin/users" element={<Gate adminOnly><UsersPage /></Gate>} /><Route path="/admin/roles" element={<Gate adminOnly><RolesPage /></Gate>} />
 {['company','email','theme','localisation'].map(s=><Route key={s} path={'/settings/'+s} element={<Gate adminOnly><SettingsPage section={s} /></Gate>} />)}
 {['leave','attendance','pmo'].map(s=><Route key={s} path={'/reports/'+s} element={<Gate hrOnly><ReportPage kind={s} /></Gate>} />)}
 <Route path="/pmo/queries/:id" element={<QueryThread />} />
 {resources.map(r=><Route key={r.key} path={r.path} element={<ResourcePage resource={r} />} />)}
 <Route path="/leave/admin" element={meta.data?.find(r=>r.key==='leave/requests')?<ResourcePage resource={meta.data.find(r=>r.key==='leave/requests')} />:<Typography>No access.</Typography>} />
 <Route path="/leave/manager" element={meta.data?.find(r=>r.key==='leave/requests')?<ResourcePage resource={meta.data.find(r=>r.key==='leave/requests')} />:<Typography>No access.</Typography>} />
 <Route path="*" element={<Typography component="h1" variant="h1">Page not found or not permitted</Typography>} />
 </Route></Route></Routes>;
}
function OfflineNotice(){
 const [offline,setOffline]=useState(!navigator.onLine);
 useEffect(()=>{const update=()=>setOffline(!navigator.onLine);window.addEventListener('online',update);window.addEventListener('offline',update);return()=>{window.removeEventListener('online',update);window.removeEventListener('offline',update);};},[]);
 return offline?<Alert severity="warning" sx={{position:'fixed',bottom:0,zIndex:1500,width:'100%'}}>You are offline. Changes will not be saved.</Alert>:null;
}
function BrandedApp(){
 const branding=useQuery({queryKey:['branding'],queryFn:async ()=>(await api.get('branding/')).data});
 const colours=branding.data;
 const runtimeTheme=colours?createTheme(theme,{palette:{primary:{main:colours.primary_color},secondary:{main:colours.secondary_color}}}):theme;
 return <ThemeProvider theme={runtimeTheme}><CssBaseline /><LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale="en-gb"><BrowserRouter future={{v7_startTransition:true,v7_relativeSplatPath:true}}><AuthProvider><OfflineNotice /><ApplicationRoutes /></AuthProvider></BrowserRouter></LocalizationProvider></ThemeProvider>;
}
export default function App(){return <QueryClientProvider client={queryClient}><BrandedApp /></QueryClientProvider>;}

