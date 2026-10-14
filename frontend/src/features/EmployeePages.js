import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, MenuItem, Stack, Tabs, Tab, TextField, Typography, Paper } from '@mui/material';
import { api, errorMessage } from '../lib/api';
import { useAuth } from '../app/AuthContext';
import { DataTable } from './Workflows';
import RecordEditor from '../components/RecordEditor';
export function NewEmployee(){
 const navigate=useNavigate(),[form,setForm]=useState({first_name:'',last_name:'',email:'',username:'',password:'',phone:'',date_of_joining:'',employee_code:'',process:''}),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const options=useQuery({queryKey:['processes'],queryFn:async ()=>(await api.get('lookups/processes/')).data});
 const save=async()=>{setBusy(true);try{const {date_of_joining,employee_code,process,...account}=form;if(!account.first_name || !account.email || !date_of_joining)throw new Error('First name, email and joining date are required.');const {data}=await api.post('employees/onboard/',{account:{...account,role:4},profile:{date_of_joining,employee_code,process}});navigate(`/employees/${data.id}`);}catch(e){setError(e.response ? Object.values(e.response.data.errors || {}).flat().join(' ') || errorMessage(e):e.message);}finally{setBusy(false);}};
 return <Stack spacing={2} maxWidth={650}><Typography component="h1" variant="h1">New employee</Typography>{error && <Alert severity="error">{error}</Alert>}{['first_name','last_name','email','username','phone','password','employee_code','date_of_joining'].map(k=><TextField key={k} label={k.replaceAll('_',' ')} type={k==='password'?'password':k==='date_of_joining'?'date':'text'} InputLabelProps={k==='date_of_joining'?{shrink:true}:undefined} value={form[k]} onChange={e=>setForm({...form,[k]:e.target.value})} />)}<TextField select label="Process" value={form.process} onChange={e=>setForm({...form,process:e.target.value})}>{options.data?.map(p=><MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}</TextField><Button variant="contained" disabled={busy} onClick={save}>Create employee</Button></Stack>;
}
export function EmployeeProfile({own=false}){
 const {id}=useParams(),auth=useAuth(),cache=useQueryClient();const [section,setSection]=useState('emergency-contacts'),[editor,setEditor]=useState(undefined),[message,setMessage]=useState('');
 const profile=useQuery({queryKey:['profile',id,own],queryFn:async ()=>(await api.get(own?'me/profile/':`employees/${id}/`)).data});
 const employeeId=profile.data?.id;
 const sections=['emergency-contacts','addresses','dependents','documents','education','experience','skills','languages','memberships','circumstance-changes','paperwork',...([1,2].includes(auth.user.role_id)?['salary']:[])];
 const q=useQuery({queryKey:['profile-section',employeeId,section],enabled:!!employeeId,queryFn:async ()=>(await api.get(`employees/${employeeId}/${section}/`)).data});
 const meta=useQuery({queryKey:['profile-meta',section],queryFn:async ()=>(await api.get(`ui/profile-fields/${section}/`)).data});
 const writable=[1,2].includes(auth.user.role_id)||['addresses','emergency-contacts','documents'].includes(section);
 const refresh=()=>{setEditor(undefined);cache.invalidateQueries({queryKey:['profile-section']});};
 const verify=async row=>{try{await api.post(`employees/${employeeId}/documents/${row.id}/verify/`);refresh();}catch(e){setMessage(errorMessage(e));}};
 return <Stack spacing={3}><Typography variant="h1" component="h1">Employee profile · {profile.data?.employee_code}</Typography>{(profile.isError||q.isError) && <Alert severity="error">{errorMessage(profile.error||q.error)}</Alert>}{message && <Alert severity="error">{message}</Alert>}<Paper sx={{p:2}}><DataTable rows={profile.data?[profile.data]:[]} /></Paper><Tabs value={section} onChange={(_,v)=>setSection(v)} variant="scrollable" scrollButtons="auto">{sections.map(s=><Tab key={s} label={s.replaceAll('-',' ')} value={s} />)}</Tabs>{writable && meta.data && <Button variant="contained" onClick={()=>setEditor(null)}>Add {section.replaceAll('-',' ')}</Button>}<DataTable rows={q.data?.results} />{q.data?.results?.map(row=><Stack direction="row" key={row.id} spacing={1}><Typography>Record {row.id}</Typography>{writable && <Button onClick={()=>setEditor(row)}>Edit</Button>}{row.file && <Button href={`/api/v1/files/${row.file}/download/`}>Download</Button>}{section==='documents' && [1,2].includes(auth.user.role_id) && !row.verified && <Button onClick={()=>verify(row)}>Verify document</Button>}</Stack>)}
 {editor!==undefined && meta.data && <RecordEditor resource={meta.data} record={editor} endpoint={`employees/${employeeId}/${section}/${editor?editor.id+'/':''}`} purpose={own?'employee':'employee-admin'} onClose={()=>setEditor(undefined)} onSaved={refresh} />}</Stack>;
}
