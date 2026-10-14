import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Alert, Button, Container, Paper, Stack, TextField, Typography, InputAdornment, IconButton } from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { api, clearCsrf, errorMessage } from '../../lib/api';
import { useAuth } from '../../app/AuthContext';
const strong = 'Password must be 12+ chars with upper, lower, number & special character.';
export default function LoginPage({ mode = 'login' }) {
  const [show, setShow] = useState(false), [message, setMessage] = useState(''), [success, setSuccess] = useState('');
  const auth = useAuth(), navigate = useNavigate(), params = useParams();
  const isNew = mode === 'reset' || mode === 'change';
  const schema = z.object({
    email: mode === 'login' || mode === 'forgot' ? z.string().email('Please enter a valid email.') : z.string().optional(),
    password: mode === 'forgot' ? z.string().optional() : isNew ? z.string().regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$/, strong) : z.string().min(1, 'Please enter password.'),
    old_password: mode === 'change' ? z.string().min(1, 'Please enter the current password.') : z.string().optional(),
    confirm_password: z.string().optional(),
  }).refine(data => !isNew || data.password === data.confirm_password, { message: 'Passwords do not match.', path: ['confirm_password'] });
  const { register, handleSubmit, setError, formState: { errors, isSubmitting } } = useForm({ resolver: zodResolver(schema) });
  const submit = async values => {
    setMessage(''); setSuccess('');
    try {
      const endpoint = mode === 'login' ? 'auth/login/' : `auth/password/${mode}/`;
      const { data } = await api.post(endpoint, { ...values, token: params.token });
      clearCsrf();
      if (mode === 'login') { await auth.reload(); navigate('/', { replace: true }); }
      else { setSuccess(data.message); if (mode === 'change') await auth.reload(); }
    } catch (error) {
      setMessage(errorMessage(error));
      Object.entries(error.response?.data?.errors || {}).forEach(([name, msgs]) => setError(name, { message: Array.isArray(msgs) ? msgs.join(' ') : String(msgs) }));
    }
  };
  const title = { login: 'Welcome to HRDESK', forgot: 'Reset your password', reset: 'Choose a new password', change: 'Change password' }[mode];
  return <Container maxWidth="sm" sx={{ py: 6 }}><Paper sx={{ p: { xs: 3, sm: 5 } }}>
    <Stack component="form" onSubmit={handleSubmit(submit)} spacing={3} noValidate>
      <Typography component="h1" variant="h1">{title}</Typography>
      {message && <Alert severity="error">{message}</Alert>}{success && <Alert severity="success">{success}</Alert>}
      {auth.expired && mode === 'login' && <Alert severity="warning">Session Expired! Please log in again to continue</Alert>}
      {['login', 'forgot'].includes(mode) && <TextField label="Email" type="email" autoComplete="username" {...register('email')} error={!!errors.email} helperText={errors.email?.message} required />}
      {mode === 'change' && <TextField label="Current password" type="password" {...register('old_password')} error={!!errors.old_password} helperText={errors.old_password?.message} required />}
      {mode !== 'forgot' && <TextField label={isNew ? 'New password' : 'Password'} type={show ? 'text' : 'password'} autoComplete={isNew ? 'new-password' : 'current-password'} {...register('password')} error={!!errors.password} helperText={errors.password?.message || (isNew ? strong : '')} required InputProps={{ endAdornment: <InputAdornment position="end"><IconButton aria-label={show ? 'Hide password' : 'Show password'} onClick={() => setShow(!show)}>{show ? <VisibilityOff /> : <Visibility />}</IconButton></InputAdornment> }} />}
      {isNew && <TextField label="Confirm password" type="password" {...register('confirm_password')} error={!!errors.confirm_password} helperText={errors.confirm_password?.message} required />}
      <Button type="submit" variant="contained" disabled={isSubmitting}>{isSubmitting ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Submit'}</Button>
      {mode === 'login' ? <Button component={Link} to="/forgot-password">Forgot password?</Button> : <Button component={Link} to="/login">Back to sign in</Button>}
    </Stack>
  </Paper></Container>;
}
