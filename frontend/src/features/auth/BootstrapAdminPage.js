import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, Container, Paper, Stack, TextField, Typography } from '@mui/material';
import { api, errorMessage } from '../../lib/api';

// Public testing token: REACT_APP variables are included in the browser bundle.
const BOOTSTRAP_ADMIN_TOKEN = process.env.REACT_APP_BOOTSTRAP_ADMIN_TOKEN || 'QqguIjFjutXXnvTbJTo55443B5LyK93bFvnmkzAuL0M';

export default function BootstrapAdminPage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [errors, setErrors] = useState({});

  const submit = async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    setError(''); setSuccess(''); setErrors({});
    if (values.password !== values.confirm_password) {
      setErrors({ confirm_password: ['Passwords do not match.'] });
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post('auth/bootstrap-admin/', values, {
        headers: { 'X-Bootstrap-Token': BOOTSTRAP_ADMIN_TOKEN },
      });
      setSuccess(data.message);
      form.reset();
    } catch (failure) {
      setError(errorMessage(failure));
      setErrors(failure.response?.data?.errors || {});
    } finally { setBusy(false); }
  };

  const fields = [
    ['first_name', 'First name', 'text'], ['last_name', 'Last name', 'text'],
    ['email', 'Email', 'email'], ['password', 'Password', 'password'],
    ['confirm_password', 'Confirm password', 'password'],
  ];
  return <Container maxWidth="sm" sx={{ py: 6 }}><Paper sx={{ p: { xs: 3, sm: 5 } }}>
    <Stack component="form" onSubmit={submit} spacing={3}>
      <Typography component="h1" variant="h1">Create testing administrator</Typography>
      <Alert severity="warning">Testing only. This page creates an administrator with full access.</Alert>
      {!BOOTSTRAP_ADMIN_TOKEN && <Alert severity="error">The testing setup token is not configured.</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      {success && <Alert severity="success">{success}</Alert>}
      {errors.non_field_errors && <Alert severity="error">{[].concat(errors.non_field_errors).join(' ')}</Alert>}
      {fields.map(([name, label, type]) => <TextField key={name} name={name} label={label} type={type}
        required disabled={busy} error={!!errors[name]} autoComplete={type === 'password' ? 'new-password' : undefined}
        inputProps={type === 'password' ? { minLength: 12 } : { maxLength: name === 'email' ? 254 : 150 }}
        helperText={errors[name] ? [].concat(errors[name]).join(' ') : name === 'password'
          ? 'Use 12+ characters with uppercase, lowercase, a number and a special character.' : ''} />)}
      <Button type="submit" variant="contained" disabled={busy || !BOOTSTRAP_ADMIN_TOKEN}>
        {busy ? 'Creating administrator…' : 'Create administrator'}
      </Button>
      <Button component={Link} to="/login">Go to login</Button>
    </Stack>
  </Paper></Container>;
}
