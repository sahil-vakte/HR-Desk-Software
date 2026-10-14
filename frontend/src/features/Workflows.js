import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Button, Card, CardContent, Grid, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material';
import dayjs from 'dayjs';
import { api, errorMessage } from '../lib/api';
import { useAuth } from '../app/AuthContext';
import { displayDate } from '../lib/format';

function DataTable({ rows }) {
  if (!rows?.length) return <Typography>No data found!</Typography>;
  const columns = Object.keys(rows[0]);
  return <Box sx={{ overflowX: 'auto' }}><Table size="small"><TableHead><TableRow>{columns.map(c => <TableCell key={c}>{c.replaceAll('_', ' ')}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map((r, i) => <TableRow key={r.id || i}>{columns.map(c => <TableCell key={c}>{typeof r[c] === 'object' ? JSON.stringify(r[c]) : String(r[c] ?? '—')}</TableCell>)}</TableRow>)}</TableBody></Table></Box>;
}
export function DashboardPage() {
  const { user } = useAuth();
  const query = useQuery({ queryKey: ['dashboard'], queryFn: async () => (await api.get(`dashboard/${[1,2].includes(user.role_id) ? 'admin' : 'me'}/`)).data });
  if (query.isPending) return <Typography>Loading dashboard…</Typography>;
  if (query.isError) return <Alert severity="error">{errorMessage(query.error)}</Alert>;
  return <Stack spacing={3}><Typography variant="h1" component="h1">Dashboard</Typography><Typography>Welcome, {user.first_name}</Typography><Grid container spacing={2}>
    {Object.entries(query.data).filter(([,v]) => typeof v === 'number').map(([k,v]) => <Grid item xs={12} sm={6} md={3} key={k}><Card><CardContent><Typography color="text.secondary">{k.replaceAll('_',' ')}</Typography><Typography variant="h3">{v}</Typography></CardContent></Card></Grid>)}
  </Grid>{Object.entries(query.data).filter(([,v]) => typeof v === 'object').map(([k,v]) => <Paper sx={{ p: 3 }} key={k}><Typography variant="h6" sx={{ mb: 2 }}>{k.replaceAll('_',' ')}</Typography><DataTable rows={Array.isArray(v) ? v : v ? [v] : []} /></Paper>)}</Stack>;
}
export function AttendancePage() {
  const cache = useQueryClient(), [error,setError] = useState(''), [busy,setBusy] = useState(false);
  const q = useQuery({ queryKey: ['attendance'], queryFn: async () => (await api.get('attendance/me/')).data });
  const open = q.data?.results?.some(x => !x.punch_out);
  const punch = async () => { setBusy(true); setError(''); try { await api.post(`attendance/${open ? 'punch-out' : 'punch-in'}/`); cache.invalidateQueries({ queryKey: ['attendance'] }); } catch(e) { setError(errorMessage(e)); } finally { setBusy(false); } };
  return <Stack spacing={3}><Typography variant="h1" component="h1">My attendance</Typography>{error && <Alert severity="error">{error}</Alert>}{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<Button variant="contained" onClick={punch} disabled={busy || q.isPending || q.isError}>{open ? 'Punch out' : 'Punch in'}</Button><DataTable rows={q.data?.statistics ? [q.data.statistics] : []} /><DataTable rows={q.data?.results} /></Stack>;
}
export function BalancePage() {
  const q = useQuery({ queryKey:['balance'],queryFn:async ()=>(await api.get('leave/balance/')).data });
  return <Stack spacing={3}><Typography variant="h1" component="h1">Leave balance</Typography>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<DataTable rows={q.data?.results} /></Stack>;
}
export function TimesheetPage() {
  const { user } = useAuth(), cache=useQueryClient();
  const [week,setWeek]=useState(dayjs().subtract((dayjs().day()+6)%7,'day').format('YYYY-MM-DD'));
  const [lines,setLines]=useState(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
  const q=useQuery({queryKey:['week',user.id,week],queryFn:async ()=>(await api.get(`timesheets/${user.id}/${week}/`)).data});
  const projects=useQuery({queryKey:['my-projects'],queryFn:async ()=>(await api.get('projects/',{params:{page_size:100}})).data.results});
  const current=lines || q.data?.lines || [];
  const change=(index,name,value)=>setLines(current.map((r,i)=>i===index?{...r,[name]:value}:r));
  const save=async()=>{
    setBusy(true);setMessage('');
    try {
      if (!current.length || current.some(r=>!r.project || !r.activity)) throw new Error('Project and activity are required for every line.');
      if(current.some(r=>[1,2,3,4,5,6,7].some(i=>Number(r[`day${i}`])<0 || Number(r[`day${i}`])>10))) throw new Error('Enter hours from 0 to 10. Please enter up to 10 hr.');
      await api.put(`timesheets/${user.id}/${week}/`,{lines:current});setLines(null);cache.invalidateQueries({queryKey:['week']});setMessage('Timesheet saved.');
    } catch(e){setMessage(e.response ? Object.values(e.response.data.errors || {}).flat().join(' ') || errorMessage(e) : e.message);} finally{setBusy(false);}
  };
  return <Stack spacing={3}><Typography variant="h1" component="h1">Weekly timesheet</Typography><TextField type="date" label="Week starting Monday" value={week} onChange={e=>{setWeek(e.target.value);setLines(null);}} InputLabelProps={{shrink:true}} />
    {message && <Alert severity={message==='Timesheet saved.'?'success':'error'}>{message}</Alert>}{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}
    <Typography>Status: {q.data?.approval_status || 'Pending'}</Typography><Box sx={{overflowX:'auto'}}><Table><TableHead><TableRow><TableCell>Project</TableCell><TableCell>Activity</TableCell>{q.data?.days?.map(d=><TableCell key={d.date}>{displayDate(d.date)}</TableCell>)}<TableCell>Action</TableCell></TableRow></TableHead><TableBody>
      {current.map((r,index)=><TableRow key={index}><TableCell sx={{minWidth:180}}><TextField select fullWidth label="Project" value={r.project || ''} onChange={e=>change(index,'project',e.target.value)}>{projects.data?.map(p=><MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}</TextField></TableCell><TableCell><TextField label="Activity" value={r.activity || ''} onChange={e=>change(index,'activity',e.target.value)} /></TableCell>
        {[1,2,3,4,5,6,7].map((i)=><TableCell key={i}><TextField type="number" inputProps={{min:0,max:10,step:0.25,'aria-label':`Day ${i} hours`}} value={r[`day${i}`] || 0} disabled={q.data?.days?.[i-1]?.disabled || q.data?.approval_status==='Accepted'} onChange={e=>change(index,`day${i}`,e.target.value)} sx={{minWidth:85}} /></TableCell>)}<TableCell><Button color="error" onClick={()=>setLines(current.filter((_,i)=>i!==index))}>Remove</Button></TableCell></TableRow>)}
    </TableBody></Table></Box><Stack direction="row" spacing={2}><Button disabled={q.isPending || q.isError || q.data?.approval_status==='Accepted'} onClick={()=>setLines([...current,{project:'',activity:'',day1:0,day2:0,day3:0,day4:0,day5:0,day6:0,day7:0}])}>Add line</Button><Button variant="contained" disabled={busy || q.isError || q.data?.approval_status==='Accepted'} onClick={save}>Save timesheet</Button></Stack></Stack>;
}
export function ReportPage({ kind }) {
  const [month,setMonth]=useState(dayjs().format('MM')),[year,setYear]=useState(dayjs().format('YYYY'));
  const q=useQuery({queryKey:['report',kind,month,year],queryFn:async ()=>(await api.get(`reports/${kind}/`,{params:{month,year}})).data});
  return <Stack spacing={3}><Typography variant="h1" component="h1">{kind} report</Typography><Stack direction="row" spacing={2}><TextField label="Month" type="number" value={month} onChange={e=>setMonth(e.target.value)} /><TextField label="Year" type="number" value={year} onChange={e=>setYear(e.target.value)} />{['csv','pdf'].map(f=><Button key={f} href={`/api/v1/reports/${kind}/?month=${month}&year=${year}&export=${f}`}>Download {f.toUpperCase()}</Button>)}</Stack>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<DataTable rows={q.data?.results} /></Stack>;
}
export function QueryThread() {
  const {id}=useParams(),cache=useQueryClient();const [message,setMessage]=useState(''),[error,setError]=useState('');
  const q=useQuery({queryKey:['thread',id],queryFn:async ()=>(await api.get(`queries/${id}/replies/`)).data});
  const reply=async()=>{try{await api.post(`queries/${id}/replies/`,{message});setMessage('');cache.invalidateQueries({queryKey:['thread',id]});}catch(e){setError(errorMessage(e));}};
  return <Stack spacing={3}><Typography variant="h1" component="h1">Query conversation</Typography>{error && <Alert severity="error">{error}</Alert>}<DataTable rows={q.data} /><TextField label="Reply" multiline rows={4} value={message} onChange={e=>setMessage(e.target.value)} /><Button variant="contained" onClick={reply} disabled={!message.trim()}>Send reply</Button></Stack>;
}
export { DataTable };
