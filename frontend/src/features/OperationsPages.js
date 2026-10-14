import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Grid, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material';
import dayjs from 'dayjs';
import { api, errorMessage } from '../lib/api';
import { useAuth } from '../app/AuthContext';
import { DataTable } from './Workflows';
import RecordEditor from '../components/RecordEditor';

export function TaskBoard({resource}){
 const cache=useQueryClient(),[editing,setEditing]=useState(undefined);
 const q=useQuery({queryKey:['task-board'],queryFn:async ()=>(await api.get('tasks/',{params:{page_size:100}})).data});
 const statuses=['To Do','Not Started','In progress','Testing','On Hold','Review','Completed'];
 return <Stack spacing={3}><Stack direction="row" justifyContent="space-between"><Typography variant="h1" component="h1">Task board</Typography><Button variant="contained" onClick={()=>setEditing(null)}>Add task</Button></Stack>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<Box sx={{display:'flex',gap:2,overflowX:'auto',pb:2}}>{statuses.map(status=><Paper key={status} sx={{minWidth:270,width:270,p:2,bgcolor:'#edf0f6'}}><Typography variant="h6" sx={{mb:2}}>{status}</Typography><Stack spacing={2}>{q.data?.results.filter(t=>t.status===status).map(task=><Card key={task.id}><CardContent><Typography fontWeight={700}>{task.name}</Typography><Typography variant="body2">{task.priority} priority · {task.estimated_hours} estimated hours</Typography><Button onClick={()=>setEditing(task)}>Edit task</Button></CardContent></Card>)}{!q.data?.results.some(t=>t.status===status) && <Typography>No tasks here</Typography>}</Stack></Paper>)}</Box>{editing!==undefined && <RecordEditor resource={resource} record={editing} onClose={()=>setEditing(undefined)} onSaved={()=>{setEditing(undefined);cache.invalidateQueries({queryKey:['task-board']});}} />}</Stack>;
}
export function WhosWherePage(){
 const auth=useAuth(),[week,setWeek]=useState(dayjs().subtract((dayjs().day()+6)%7,'day').format('YYYY-MM-DD')),[draft,setDraft]=useState(null),[message,setMessage]=useState('');
 const q=useQuery({queryKey:['where',week],queryFn:async ()=>(await api.get('whos-where/',{params:{week_start:week}})).data});
 const modes=useQuery({queryKey:['work-modes'],queryFn:async ()=>(await api.get('lookups/working-modes/')).data});
 const projects=useQuery({queryKey:['projects-lookup'],queryFn:async ()=>(await api.get('projects/',{params:{page_size:100}})).data.results});
 const rows=draft || q.data?.rows || [],writable=[1,2].includes(auth.user.role_id);
 const change=(id,key,value)=>setDraft(rows.map(r=>r.user===id?{...r,[key]:value}:r));
 const save=async()=>{try{await api.put(`whos-where/?week_start=${week}`,{rows});setMessage('Plan saved.');setDraft(null);q.refetch();}catch(e){setMessage(Object.values(e.response?.data?.errors || {}).flat().join(' ') || errorMessage(e));}};
 return <Stack spacing={3}><Typography variant="h1" component="h1">Who's Where</Typography><TextField type="date" label="Week starting Monday" value={week} onChange={e=>{setWeek(e.target.value);setDraft(null);}} InputLabelProps={{shrink:true}} />{message && <Alert>{message}</Alert>}{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<Box sx={{overflowX:'auto'}}><Table><TableHead><TableRow>{['Employee','Project','Monday','Tuesday','Wednesday','Thursday','Friday'].map(x=><TableCell key={x}>{x}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map(r=><TableRow key={r.user}><TableCell>{r.employee_code} · {r.name}</TableCell><TableCell><TextField label="Project" select value={r.project || ''} disabled={!writable} onChange={e=>change(r.user,'project',e.target.value)} sx={{minWidth:160}}><MenuItem value="">None</MenuItem>{projects.data?.map(p=><MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}</TextField></TableCell>{[1,2,3,4,5].map(i=><TableCell key={i}><TextField select label={`Day ${i}`} value={r[`day${i}`] || ''} disabled={!writable} onChange={e=>change(r.user,`day${i}`,e.target.value)} sx={{minWidth:140}}><MenuItem value="">Unplanned</MenuItem>{modes.data?.map(m=><MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>)}</TextField></TableCell>)}</TableRow>)}</TableBody></Table></Box><Stack direction="row" spacing={2}>{writable && <><Button variant="contained" onClick={save}>Submit</Button><Button onClick={()=>setDraft(null)}>Reset</Button></>}<Button href={`/api/v1/whos-where/?week_start=${week}&export=csv`}>Download CSV</Button><Button href={`/api/v1/whos-where/?week_start=${week}&export=pdf`}>Download PDF</Button></Stack></Stack>;
}
export function AttendanceGridPage(){
 const [month,setMonth]=useState(dayjs().format('MM')),[year,setYear]=useState(dayjs().format('YYYY'));
 const q=useQuery({queryKey:['attendance-grid',month,year],queryFn:async ()=>(await api.get('attendance/grid/',{params:{month,year}})).data});
 return <Stack spacing={3}><Typography variant="h1" component="h1">Attendance grid</Typography><Stack direction="row" spacing={2}><TextField label="Month" type="number" value={month} onChange={e=>setMonth(e.target.value)} /><TextField label="Year" type="number" value={year} onChange={e=>setYear(e.target.value)} /><Button href={`/api/v1/attendance/grid/?month=${month}&year=${year}&export=csv`}>CSV</Button><Button href={`/api/v1/attendance/grid/?month=${month}&year=${year}&export=pdf`}>PDF</Button></Stack>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<DataTable rows={q.data?.results} /></Stack>;
}
export function AuditPage(){
 const q=useQuery({queryKey:['audit'],queryFn:async ()=>(await api.get('audit-events/',{params:{page_size:100}})).data});
 return <Stack spacing={3}><Typography variant="h1" component="h1">Audit events</Typography>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<DataTable rows={q.data?.results} /></Stack>;
}
export function DirectoryPage(){
 const q=useQuery({queryKey:['directory'],queryFn:async ()=>(await api.get('directory/')).data});
 return <Stack spacing={3}><Typography variant="h1" component="h1">Employee directory</Typography>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<Grid container spacing={2}>{q.data?.results.map(r=><Grid item xs={12} md={4} key={r.id}><Card><CardContent><Typography variant="h6">{r.name}</Typography><Typography>{r.job_title}</Typography><Typography>{r.sub_unit}</Typography></CardContent></Card></Grid>)}</Grid></Stack>;
}
export function ApplicantPage(){
 const {id}=useParams(),[message,setMessage]=useState(''),[confirmation,setConfirmation]=useState(null),[ratings,setRatings]=useState(Array.from({length:8},()=>({rating:3,comment:''}))),[outcome,setOutcome]=useState('Potential');
 const auth=useAuth();const q=useQuery({queryKey:['applicant',id],queryFn:async ()=>(await api.get(`rms/applicants/${id}/`)).data});
 const factors=['Technical exposure','Applicable work skills','Applicable work experience','Domain exposure','Relevance to position','Job-move logic','Gaps','CV neatness'];
 const send=async()=>{try{await api.post(`rms/applicants/${id}/invite/${confirmation}/`);setMessage('Invitation sent.');}catch(e){setMessage(Object.values(e.response?.data?.errors || {}).flat().join(' ') || errorMessage(e));}setConfirmation(null);};
 const evaluate=async()=>{try{await api.put(`rms/applicants/${id}/cv-evaluation/`,{assessor_name:auth.user.first_name,assessment_date:dayjs().format('YYYY-MM-DD'),ratings,outcome});setMessage('Evaluation saved.');}catch(e){setMessage(errorMessage(e));}};
 const parse=async()=>{try{await api.post(`rms/applicants/${id}/parse-cv/`);q.refetch();setMessage('CV text extracted.');}catch(e){setMessage(Object.values(e.response?.data?.errors || {}).flat().join(' ') || errorMessage(e));}};
 return <Stack spacing={3}><Typography variant="h1" component="h1">Applicant tracking · {q.data?.name}</Typography>{message && <Alert>{message}</Alert>}{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<DataTable rows={q.data?[q.data]:[]} /><Stack direction="row" spacing={2}><Button onClick={parse}>Extract CV text</Button><Button onClick={()=>setConfirmation('test')}>Send technical test</Button><Button onClick={()=>setConfirmation('cif')}>Request candidate information</Button></Stack><Typography variant="h5">CV evaluation</Typography>{factors.map((factor,i)=><Stack key={factor} direction="row" spacing={2}><TextField select label={factor} value={ratings[i].rating} onChange={e=>setRatings(ratings.map((r,j)=>j===i?{...r,rating:Number(e.target.value)}:r))} sx={{minWidth:240}}>{[1,2,3,4,5].map(n=><MenuItem key={n} value={n}>{n}</MenuItem>)}</TextField><TextField label="Comment" value={ratings[i].comment} onChange={e=>setRatings(ratings.map((r,j)=>j===i?{...r,comment:e.target.value}:r))} fullWidth /></Stack>)}<TextField select label="Outcome" value={outcome} onChange={e=>setOutcome(e.target.value)}>{['Strong','Potential','Rejected'].map(v=><MenuItem key={v} value={v}>{v}</MenuItem>)}</TextField><Button variant="contained" onClick={evaluate}>Save evaluation</Button><Dialog open={!!confirmation} onClose={()=>setConfirmation(null)}><DialogTitle>Send candidate invitation?</DialogTitle><DialogContent>This will email a seven-day link to the applicant.</DialogContent><DialogActions><Button onClick={()=>setConfirmation(null)}>Cancel</Button><Button onClick={send}>Send</Button></DialogActions></Dialog></Stack>;
}
export function CandidatePage(){
 const {token}=useParams(),[answers,setAnswers]=useState({}),[message,setMessage]=useState(''),[done,setDone]=useState(false);
 const q=useQuery({queryKey:['candidate',token],queryFn:async ()=>(await api.get(`candidate/${token}/`)).data});
 const submit=async()=>{try{await api.post(`candidate/${token}/`,{answers});setDone(true);}catch(e){setMessage(errorMessage(e));}};
 if(done)return <Typography variant="h1" sx={{p:4}}>Thank you. Your response has been submitted.</Typography>;
 return <Stack sx={{maxWidth:800,mx:'auto',p:4}} spacing={3}><Typography component="h1" variant="h1">Candidate response</Typography>{message && <Alert severity="error">{message}</Alert>}{q.isError && <Alert severity="error">This link has expired or has already been used.</Alert>}
 {q.data?.kind==='test'?q.data.questions.map((question,index)=><Paper key={question.id} sx={{p:3}}><Typography>{index+1}. {question.question}</Typography><TextField fullWidth label="Your answer" select={question.type==='MCQ'} multiline={question.type!=='MCQ'} value={answers[question.id] || ''} onChange={e=>setAnswers({...answers,[question.id]:e.target.value})}>{question.type==='MCQ' && question.options.map((option,i)=><MenuItem key={i} value={option}>{option}</MenuItem>)}</TextField></Paper>):q.data && ['full_name','email','phone','address','work_authorization','availability','additional_information'].map(field=><TextField key={field} label={field.replaceAll('_',' ')} value={answers[field] || ''} onChange={e=>setAnswers({...answers,[field]:e.target.value})} multiline={field==='additional_information'} />)}
 <Button disabled={!q.data || q.isError} variant="contained" onClick={submit}>Submit response</Button></Stack>;
}
