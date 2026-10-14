import dayjs from 'dayjs';
export function displayDate(value) {
  if (!value) return '—';
  const date = dayjs(value);
  return date.isValid() ? date.format('DD-MM-YYYY') : '—';
}
