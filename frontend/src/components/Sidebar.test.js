import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from './Sidebar';
test('menu renders supplied items and allows keyboard expansion', async () => {
  const user = userEvent.setup();
  render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <Sidebar menu={[{ menu_id: 1, label: 'Group', children: [{ menu_id: 2, label: 'Allowed', path: '/allowed' }] }]} />
  </MemoryRouter>);
  const group = screen.getByRole('button', { name: 'Group' });
  act(() => group.focus());
  await act(async () => { await user.keyboard('{Enter}'); });
  expect(group).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByRole('link', { name: 'Allowed' })).toHaveAttribute('href', '/allowed');
  expect(screen.queryByText('Admin')).not.toBeInTheDocument();
});
