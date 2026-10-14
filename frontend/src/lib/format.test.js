import { displayDate } from './format';
test('displays ISO dates in UK format', () => { expect(displayDate('2026-10-14')).toBe('14-10-2026'); });
test('handles missing dates', () => { expect(displayDate(null)).toBe('—'); });
