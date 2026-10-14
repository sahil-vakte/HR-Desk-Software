import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, TextField, Typography } from '@mui/material';
import { api, errorMessage } from '../lib/api';
import RichText from './RichText';

function ReferenceField({ field, control, errors }) {
  const project = useWatch({ control, name: 'project' });
  const kinds = { process: 'processes', work_mode: 'working-modes', sub_unit: 'sub-units', job_title: 'job-titles', designation: 'designations', nationality: 'nationalities', country: 'countries', employment_type: 'employment-statuses', document_list_item: 'document-list', skill: 'skills', language: 'languages', level: 'education-levels', work_authorization: 'work-authorizations' };
  const url = field.name === 'assignees' && project ? `projects/${project}/assignable-users/` : `lookups/${kinds[field.name] || field.relation}/`;
  const lookup = useQuery({ queryKey: ['lookup', url], enabled: field.name !== 'assignees' || !!project, queryFn: async () => (await api.get(url)).data });
  return <Controller name={field.name} control={control} render={({ field: input }) => <TextField {...input} value={input.value ?? (field.multiple ? [] : '')} select fullWidth label={field.label} SelectProps={{ multiple: field.multiple }} required={field.required} error={!!errors[field.name]} helperText={errors[field.name]?.message || (lookup.isError ? 'Unable to load options.' : '')}>
    {!field.multiple && <MenuItem value="">Select</MenuItem>}{(lookup.data || []).map(row => <MenuItem key={row.id} value={row.id}>{row.name}</MenuItem>)}
  </TextField>} />;
}
export default function RecordEditor({ resource, record, onClose, onSaved, endpoint, purpose }) {
  const fields = resource.fields.filter(f => !f.read_only && f.name !== 'is_archived');
  const [message, setMessage] = useState('');
  const defaults = useMemo(() => Object.fromEntries(fields.map(f => [f.name, f.type === 'json' ? JSON.stringify(record?.[f.name] ?? f.default ?? {}) : record?.[f.name] ?? f.default ?? (f.multiple ? [] : f.type === 'boolean' ? false : '')])), [record, resource]); // eslint-disable-line react-hooks/exhaustive-deps
  const schema = useMemo(() => z.object(Object.fromEntries(fields.map(f => {
    let rule = z.any();
    if (f.required) rule = rule.refine(v => v !== '' && v !== null && v !== undefined && (!Array.isArray(v) || v.length > 0), f.message || `${f.label} is required.`);
    if (f.type === 'number') rule = rule.refine(v => v === '' || (Number.isFinite(Number(v)) && Number(v) >= 0), 'Enter a non-negative number.');
    return [f.name, rule];
  }))).superRefine((data, ctx) => {
    if (data.from_date && data.to_date && (resource.key.endsWith('years') ? data.from_date >= data.to_date : data.from_date > data.to_date)) ctx.addIssue({ code: 'custom', path: ['to_date'], message: 'End date must be after start date.' });
    if (data.start_date && data.end_date && data.start_date > data.end_date) ctx.addIssue({ code: 'custom', path: ['end_date'], message: 'End date must not precede start date.' });
    if (data.week_start && new Date(data.week_start + 'T12:00:00').getDay() !== 1) ctx.addIssue({ code: 'custom', path: ['week_start'], message: 'Please select a Monday.' });
    if (data.duration && data.duration !== 'Full Day' && data.from_date && data.to_date && data.from_date !== data.to_date) ctx.addIssue({ code: 'custom', path: ['duration'], message: 'Half-day leave must cover one date.' });
  }), [resource]); // eslint-disable-line react-hooks/exhaustive-deps
  const { register, control, handleSubmit, setValue, setError, formState: { errors, isSubmitting } } = useForm({ defaultValues: defaults, resolver: zodResolver(schema) });
  const submit = async values => {
    setMessage('');
    try {
      const data = { ...values };
      fields.forEach(f => { if (f.type === 'json' && typeof data[f.name] === 'string') data[f.name] = JSON.parse(data[f.name] || '{}'); if (data[f.name] === '' && ['select', 'file', 'date', 'datetime-local'].includes(f.type)) data[f.name] = null; });
      const url = endpoint || resource.key + '/';
      await api[record ? 'patch' : 'post'](url + (record && !endpoint ? `${record.id}/` : ''), data);
      onSaved();
    } catch (error) {
      setMessage(error instanceof SyntaxError ? 'Enter valid JSON.' : errorMessage(error));
      Object.entries(error.response?.data?.errors || {}).forEach(([key, messages]) => setError(key, { message: Array.isArray(messages) ? messages.join(' ') : String(messages) }));
    }
  };
  const upload = async (event, field) => {
    const file = event.target.files?.[0]; if (!file) return;
    if (file.size > 10 * 1024 * 1024) { setError(field.name, { message: 'File must be 10 MB or smaller' }); return; }
    const form = new FormData(); form.append('file', file); form.append('purpose', purpose || (resource.key === 'wsr' ? 'wsr' : resource.key === 'queries' ? 'query' : resource.key.startsWith('rms') ? 'recruitment' : resource.key === 'policies' ? 'policy' : resource.key === 'newsletters' ? 'newsletter' : resource.key === 'ho-documents' ? 'ho' : 'employee-admin'));
    try { const { data } = await api.post('files/', form); setValue(field.name, data.id, { shouldValidate: true }); }
    catch (error) { setMessage(errorMessage(error)); }
  };
  return <Dialog open onClose={isSubmitting ? undefined : onClose} fullWidth maxWidth="md"><DialogTitle>{record ? 'Edit' : 'Add'} {resource.title}</DialogTitle>
    <DialogContent><Stack component="form" id="record-form" onSubmit={handleSubmit(submit)} spacing={2} sx={{ pt: 1 }}>
      {message && <Alert severity="error">{message}</Alert>}
      {fields.map(field => {
        if (field.type === 'select') return <ReferenceField key={field.name} field={field} control={control} errors={errors} />;
        if (field.type === 'boolean') return <Controller key={field.name} control={control} name={field.name} render={({ field: input }) => <FormControlLabel label={field.label} control={<Checkbox checked={!!input.value} onChange={e => input.onChange(e.target.checked)} />} />} />;
        if (field.type === 'richtext') return <Controller key={field.name} control={control} name={field.name} render={({ field: input }) => <RichText label={field.label} value={input.value} onChange={input.onChange} error={errors[field.name]?.message} />} />;
        if (field.type === 'file') return <Stack key={field.name}><Button component="label" variant="outlined">{field.label}<input hidden type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.png,.jpg,.jpeg" onChange={e => upload(e, field)} /></Button>{errors[field.name] && <Typography color="error">{errors[field.name].message}</Typography>}</Stack>;
        return <TextField key={field.name} label={field.label} {...register(field.name)} required={field.required} error={!!errors[field.name]} helperText={errors[field.name]?.message} type={['date','datetime-local','number'].includes(field.type) ? field.type : 'text'} InputLabelProps={['date','datetime-local'].includes(field.type) ? { shrink: true } : undefined} multiline={['textarea','json'].includes(field.type)} minRows={['textarea','json'].includes(field.type) ? 3 : undefined} select={field.type === 'choice'}>
          {field.type === 'choice' && field.choices.map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </TextField>;
      })}
    </Stack></DialogContent><DialogActions><Button onClick={onClose} disabled={isSubmitting}>Cancel</Button><Button type="submit" form="record-form" variant="contained" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : 'Save'}</Button></DialogActions>
  </Dialog>;
}
