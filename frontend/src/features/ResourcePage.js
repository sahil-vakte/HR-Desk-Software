import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { DataGrid } from '@mui/x-data-grid';
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField, Typography, Snackbar, Chip } from '@mui/material';
import { Link } from 'react-router-dom';
import { api, errorMessage } from '../lib/api';
import { displayDate } from '../lib/format';
import RecordEditor from '../components/RecordEditor';
export default function ResourcePage({ resource }) {
  const cache = useQueryClient();
  const [search, setSearch] = useState(''), [appliedSearch, setAppliedSearch] = useState('');
  const [pagination, setPagination] = useState({ page: 0, pageSize: 20 });
  const [editing, setEditing] = useState(undefined), [confirm, setConfirm] = useState(null), [reason, setReason] = useState(''), [message, setMessage] = useState(''), [success, setSuccess] = useState(''), [busy, setBusy] = useState(false);
  const query = useQuery({ queryKey: ['resource', resource.key, appliedSearch, pagination], queryFn: async () => (await api.get(`${resource.key}/`, { params: { search: appliedSearch, page: pagination.page + 1, page_size: pagination.pageSize } })).data });
  const saved = () => { setEditing(undefined); setSuccess('Record saved'); cache.invalidateQueries({ queryKey: ['resource', resource.key] }); cache.invalidateQueries({ queryKey: ['lookup'] }); };
  const perform = async () => {
    setBusy(true); setMessage('');
    try {
      if (confirm.action === 'delete') await api.delete(`${resource.key}/${confirm.row.id}/`);
      else await api.post(`${resource.key}/${confirm.row.id}/${confirm.action}/`, { reason });
      setSuccess('Action completed'); setConfirm(null); setReason(''); cache.invalidateQueries({ queryKey: ['resource', resource.key] });
    } catch (error) { setMessage(Object.values(error.response?.data?.errors || {}).flat().join(' ') || errorMessage(error)); }
    finally { setBusy(false); }
  };
  const columns = useMemo(() => {
    const visible = resource.fields.filter(f => !['description', 'notes', 'message', 'password', 'bank_details'].includes(f.name)).slice(0, 9);
    return [...visible.map(field => ({ field: field.name, headerName: field.label, minWidth: 130, flex: 1,
      renderCell: ({ value }) => field.type === 'file' && value ? <Button size="small" href={`/api/v1/files/${value}/download/`}>Download</Button> : field.type === 'date' ? displayDate(value) : field.type === 'boolean' ? <Chip size="small" label={value ? 'Active' : 'Deactive'} /> : typeof value === 'object' ? JSON.stringify(value) : String(value ?? '—') })),
      { field: '_actions', headerName: 'Actions', width: 280, sortable: false, renderCell: ({ row }) => <Stack direction="row" spacing={0.5}>
        {resource.key === 'employees' && <Button component={Link} to={`/employees/${row.id}`}>Profile</Button>}
        {resource.key === 'queries' && <Button component={Link} to={`/pmo/queries/${row.id}`}>Open</Button>}
        {resource.key === 'rms/applicants' && <Button component={Link} to={`/rms/applicants/${row.id}`}>Track</Button>}
        {resource.writable && resource.key !== 'timesheets' && <Button onClick={() => setEditing(row)}>Edit</Button>}
        {resource.writable && <Button color="error" onClick={() => { setConfirm({ row, action: 'delete' }); setMessage(''); }}>Delete</Button>}
        {(resource.actions || []).map(action => <Button key={action} onClick={() => { setConfirm({ row, action }); setMessage(''); }}>{action}</Button>)}
      </Stack> },
    ];
  }, [resource]);
  return <Stack spacing={3}><Stack direction="row" justifyContent="space-between" alignItems="center"><Typography component="h1" variant="h1">{resource.title}</Typography>
    {resource.writable && !['employees','timesheets'].includes(resource.key) && <Button variant="contained" onClick={() => setEditing(null)}>Add</Button>}
    {resource.key === 'employees' && <Button variant="contained" component={Link} to="/employees/new">New employee</Button>}
  </Stack><Stack direction="row" spacing={1} component="form" onSubmit={event => { event.preventDefault(); setAppliedSearch(search); setPagination(p => ({ ...p, page: 0 })); }}><TextField label="Search" value={search} onChange={event => setSearch(event.target.value)} size="small" /><Button type="submit" variant="contained">Search</Button><Button onClick={() => { setSearch(''); setAppliedSearch(''); }}>Clear</Button></Stack>
    {query.isError && <Alert severity="error" action={<Button onClick={() => query.refetch()}>Retry</Button>}>{errorMessage(query.error)}</Alert>}
    <Box sx={{ height: 560, width: '100%', bgcolor: 'background.paper' }}><DataGrid rows={query.data?.results || []} columns={columns} loading={query.isPending} paginationMode="server" rowCount={query.data?.count || 0} paginationModel={pagination} onPaginationModelChange={setPagination} pageSizeOptions={[20,50,100]} disableRowSelectionOnClick localeText={{ noRowsLabel: 'No data found!' }} /></Box>
    {editing !== undefined && <RecordEditor resource={resource} record={editing} onClose={() => setEditing(undefined)} onSaved={saved} />}
    <Dialog open={!!confirm} onClose={busy ? undefined : () => setConfirm(null)}><DialogTitle>Are you sure?</DialogTitle><DialogContent><Stack spacing={2}>
      <Typography>Do you really want to {confirm?.action} this record?</Typography>{message && <Alert severity="error">{message}</Alert>}
      {confirm?.action === 'reject' && <TextField label="Reason" value={reason} onChange={e => setReason(e.target.value)} multiline required />}
    </Stack></DialogContent><DialogActions><Button disabled={busy} onClick={() => setConfirm(null)}>Cancel</Button><Button disabled={busy || (confirm?.action === 'reject' && !reason.trim())} onClick={perform}>Confirm</Button></DialogActions></Dialog>
    <Snackbar open={!!success} autoHideDuration={3000} onClose={() => setSuccess('')} message={success} />
  </Stack>;
}
