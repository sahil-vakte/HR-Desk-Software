import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, TextField, Typography, Paper } from '@mui/material';
import { api, errorMessage } from '../lib/api';
export function UsersPage(){
  const cache=useQueryClient(),[form,setForm]=useState(null),[message,setMessage]=useState('');
  const q=useQuery({queryKey:['users'],queryFn:async ()=>(await api.get('admin/users/')).data});
  const roles=useQuery({queryKey:['roles'],queryFn:async ()=>(await api.get('admin/roles/')).data});
  const save=async()=>{try{await api[form.id?'patch':'post'](`admin/users/${form.id?form.id+'/':''}`,form);setForm(null);cache.invalidateQueries({queryKey:['users']});}catch(e){setMessage(Object.values(e.response?.data?.errors || {}).flat().join(' ') || errorMessage(e));}};
  return <Stack spacing={3}><Typography variant="h1" component="h1">Users</Typography>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}<Button variant="contained" onClick={()=>{setForm({first_name:'',last_name:'',email:'',username:'',password:'',phone:'',role:4,is_active:true});setMessage('');}}>Add user</Button>
    {q.data?.results?.map(u=><Paper key={u.id} sx={{p:2}}><Stack direction="row" justifyContent="space-between"><Typography>{u.first_name} {u.last_name} · {u.email} · {u.is_active?'Active':'Inactive'}</Typography><Button onClick={()=>{setForm(u);setMessage('');}}>Edit</Button></Stack></Paper>)}
    <Dialog open={!!form} onClose={()=>setForm(null)} fullWidth><DialogTitle>{form?.id?'Edit':'Add'} user</DialogTitle><DialogContent><Stack spacing={2} sx={{pt:1}}>{message && <Alert severity="error">{message}</Alert>}{form && ['first_name','last_name','email','username','phone','password'].map(k=><TextField key={k} label={k.replaceAll('_',' ')} type={k==='password'?'password':'text'} value={form[k] || ''} onChange={e=>setForm({...form,[k]:e.target.value})} />)}<TextField select label="Role" value={form?.role || ''} onChange={e=>setForm({...form,role:e.target.value})}>{roles.data?.results?.map(r=><MenuItem key={r.id} value={r.id}>{r.title}</MenuItem>)}</TextField><FormControlLabel label="Active" control={<Checkbox checked={!!form?.is_active} onChange={e=>setForm({...form,is_active:e.target.checked})} />} /></Stack></DialogContent><DialogActions><Button onClick={()=>setForm(null)}>Cancel</Button><Button onClick={save}>Save</Button></DialogActions></Dialog></Stack>;
}
export function RolesPage(){
  const cache=useQueryClient(),[form,setForm]=useState(null),[message,setMessage]=useState('');
  const q=useQuery({queryKey:['roles'],queryFn:async ()=>(await api.get('admin/roles/')).data});
  const menus=useQuery({queryKey:['menus'],queryFn:async ()=>(await api.get('admin/menu-items/',{params:{page_size:100}})).data});
  const save=async()=>{try{await api.patch(`admin/roles/${form.id}/`,form);setForm(null);cache.invalidateQueries({queryKey:['roles']});}catch(e){setMessage(errorMessage(e));}};
  return <Stack spacing={3}><Typography variant="h1" component="h1">Roles and permissions</Typography>{q.isError && <Alert severity="error">{errorMessage(q.error)}</Alert>}{q.data?.results?.map(r=><Paper key={r.id} sx={{p:2}}><Typography>{r.title} · {r.permissions.length} grants</Typography><Button onClick={()=>setForm(r)}>Edit permissions</Button></Paper>)}<Dialog open={!!form} onClose={()=>setForm(null)} fullWidth maxWidth="md"><DialogTitle>Edit role</DialogTitle><DialogContent>{message && <Alert severity="error">{message}</Alert>}<TextField fullWidth label="Role name" value={form?.title || ''} onChange={e=>setForm({...form,title:e.target.value})} /><Stack>{menus.data?.results?.map(m=><FormControlLabel key={m.id} label={`${m.title} (${m.id})`} control={<Checkbox checked={form?.permissions.includes(m.id) || false} onChange={e=>setForm({...form,permissions:e.target.checked?[...form.permissions,m.id]:form.permissions.filter(id=>id!==m.id)})} />} />)}</Stack></DialogContent><DialogActions><Button onClick={()=>setForm(null)}>Cancel</Button><Button onClick={save}>Save</Button></DialogActions></Dialog></Stack>;
}
export function SettingsPage({section}){
  const cache=useQueryClient(),[values,setValues]=useState(null),[profile,setProfile]=useState('HR'),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
  const q=useQuery({queryKey:['settings',section],queryFn:async ()=>(await api.get(`settings/${section}/`)).data});
  const defaults={profile,host:'',username:'',password:'',port:587,from_address:'',from_name:'',security:'TLS',status:true};
  const base=section==='email'?(q.data?.find?.(r=>r.profile===profile)||defaults):q.data;
  const data=values||base;
  const save=async()=>{setBusy(true);setMessage('');try{const payload={...data};if(section==='email'&&!payload.password)delete payload.password;await api.put(`settings/${section}/`,payload);setValues(null);setMessage('Settings saved.');q.refetch();cache.invalidateQueries({queryKey:['branding']});}catch(e){setMessage(Object.values(e.response?.data?.errors||{}).flat().join(' ')||errorMessage(e));}finally{setBusy(false);}};
  const fields=section==='email'?['host','username','password','port','from_address','from_name','security']:Object.keys(data||{}).filter(k=>!['id','created_at','updated_at','logo','handbook','site_logo','favicon'].includes(k));
  const upload=async(event,key)=>{const file=event.target.files?.[0];if(!file)return;const body=new FormData();body.append('file',file);body.append('purpose','settings');try{const result=await api.post('files/',body);setValues({...data,[key]:result.data.id});}catch(e){setMessage(errorMessage(e));}};
  return <Stack spacing={3} maxWidth={800}><Typography variant="h1" component="h1">{section} settings</Typography>{message&&<Alert severity={message==='Settings saved.'?'success':'error'}>{message}</Alert>}{q.isError&&<Alert severity="error">{errorMessage(q.error)}</Alert>}
    {section==='email'&&<TextField select label="Email profile" value={profile} onChange={e=>{setProfile(e.target.value);setValues(null);}}><MenuItem value="HR">HR</MenuItem><MenuItem value="PMO">PMO</MenuItem></TextField>}
    {data&&fields.map(k=>typeof data[k]==='boolean'?<FormControlLabel key={k} label={k.replaceAll('_',' ')} control={<Checkbox checked={data[k]} onChange={e=>setValues({...data,[k]:e.target.checked})}/>} />:<TextField key={k} label={k.replaceAll('_',' ')} type={k==='password'?'password':k.includes('color')?'color':k==='port'?'number':'text'} value={data[k]??''} onChange={e=>setValues({...data,[k]:e.target.value})} helperText={k==='password'?'Leave blank to keep the configured secret.':undefined}/>)}
    {section==='company'&&['logo','handbook'].map(k=><Button component="label" key={k}>Upload {k}<input hidden type="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" onChange={e=>upload(e,k)}/></Button>)}
    {section==='theme'&&['site_logo','favicon'].map(k=><Button component="label" key={k}>Upload {k}<input hidden type="file" accept=".png,.jpg,.jpeg" onChange={e=>upload(e,k)}/></Button>)}
    <Button onClick={save} variant="contained" disabled={busy||!data}>Save settings</Button>
  </Stack>;
}
