import { describe, expect, it } from 'vitest';
import { compareFolders } from './folderSort';

describe('sidebar folder ordering', () => {
	const folders = [
		{ id: 'a', name: 'Folder 10', last_activity_at: 100 },
		{ id: 'b', name: 'Folder 2', last_activity_at: 200 },
		{ id: 'c', name: 'Alpha', last_activity_at: 100 }
	];
	it('keeps natural alphabetical ordering as the default', () => {
		expect([...folders].sort(compareFolders).map((f) => f.id)).toEqual(['c', 'b', 'a']);
	});
	it('sorts newest activity first and breaks timestamp ties by name', () => {
		expect(
			[...folders].sort((a, b) => compareFolders(a, b, 'recent_activity')).map((f) => f.id)
		).toEqual(['b', 'c', 'a']);
	});
	it('supports old API responses and stable name ties', () => {
		const a = { id: 'a', name: 'alpha', created_at: 300 };
		const b = { id: 'b', name: 'Alpha', created_at: 100 };
		expect(compareFolders(a, b, 'recent_activity')).toBeLessThan(0);
		expect(compareFolders(a, b)).toBeLessThan(0);
	});
});
