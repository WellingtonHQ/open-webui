export type FolderSortMode = 'alphabetical' | 'recent_activity';

type SortableFolder = {
	id: string;
	name?: string;
	last_activity_at?: number | null;
	created_at?: number;
};

export const compareFolders = (
	a: SortableFolder,
	b: SortableFolder,
	mode: FolderSortMode = 'alphabetical'
) => {
	if (mode === 'recent_activity') {
		const delta =
			(b.last_activity_at ?? b.created_at ?? 0) - (a.last_activity_at ?? a.created_at ?? 0);
		if (delta) return delta;
	}
	return (
		(a.name ?? '').localeCompare(b.name ?? '', undefined, { numeric: true, sensitivity: 'base' }) ||
		a.id.localeCompare(b.id)
	);
};
