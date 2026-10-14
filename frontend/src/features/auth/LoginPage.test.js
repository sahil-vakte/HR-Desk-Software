import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from './LoginPage';
import { api } from '../../lib/api';
jest.mock('../../app/AuthContext', () => ({ useAuth: () => ({ reload: jest.fn(), expired: false }) }));
jest.mock('../../lib/api', () => ({ api: { post: jest.fn() }, clearCsrf: jest.fn(), errorMessage: () => 'Invalid credentials' }));
function page() { return render(<MemoryRouter future={{v7_startTransition:true,v7_relativeSplatPath:true}}><LoginPage /></MemoryRouter>); }
test('login requires valid email and password before contacting the server', async () => {
  page(); fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(await screen.findByText('Please enter a valid email.')).toBeInTheDocument();
  expect(api.post).not.toHaveBeenCalled();
});
test('server login validation is displayed under email', async () => {
  api.post.mockRejectedValueOnce({ response: { data: { errors: { email: ['These credentials do not match our records.'] } } } });
  page(); fireEvent.change(screen.getByLabelText(/Email/), { target: { value: 'fictional@example.invalid' } });
  fireEvent.change(screen.getByLabelText(/^Password/), { target: { value: 'Wrong-password1!' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(await screen.findByText('These credentials do not match our records.')).toBeInTheDocument();
});
