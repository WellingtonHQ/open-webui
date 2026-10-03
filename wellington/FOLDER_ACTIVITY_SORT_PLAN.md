# Activity-based folder sorting

## Goal

Add a per-user sidebar setting that sorts sibling folders by the newest chat
created or updated anywhere in their subtree. A new chat in
Career / Job Search / Interviews should raise Interviews within Job Search,
Job Search within Career, and Career among the top-level folders.

Implemented on 2026-10-03. The sections below retain the design and verification
criteria for future maintenance.

## Findings (2026-10-03)

- This checkout identifies itself as Open WebUI 0.11.4 in package.json.
- Sidebar/Folders.svelte:30 sorts root folders alphabetically.
- Sidebar/RecursiveFolder.svelte:900 sorts child folders alphabetically.
- Sidebar.svelte:255 and :285 also sort intermediate data by folder.updated_at,
  but the rendering components override that order with alphabetical sorting.
- There is no folder-sort preference in the inspected frontend source.
- Folder.updated_at records folder changes, including expand/collapse, not the
  most recent contained chat activity. It is unsuitable for this feature.
- Chat.updated_at is indexed, and the existing
  user_id_folder_unread_idx index includes user_id, folder_id, archived, and
  updated_at. An aggregate query can start with these existing indexes.
- Current chat folder moves also update Chat.updated_at. A first version based
  on chat modification times will therefore count normal folder moves as updates.
- Existing folder chat lists load incrementally. Calculating folder activity from
  loaded frontend chat rows would miss collapsed folders and unloaded chats.

## Upstream research

The upstream main branch's Folders.svelte was read and still uses alphabetical
root-folder sorting. No confirmed roadmap commitment or matching implementation
was found in the searched issues, releases, and source. This is not proof that
no matching request exists.

Sources:

- https://github.com/open-webui/open-webui/blob/main/src/lib/components/layout/Sidebar/Folders.svelte
  confirms alphabetical folder ordering.
- https://github.com/open-webui/open-webui/releases/tag/v0.11.0
  introduces folder pages with sorting of chats by title or last updated. That
  is different from sorting sidebar folders by their contents' activity.
- https://github.com/open-webui/open-webui/issues/15804
  requests sorting chats inside folders, not sorting the folders themselves.
- https://github.com/open-webui/open-webui/issues/21067
  is a closed request for recent selection or fixed ordering in the Move to
  Folder picker, not sidebar chat-activity ordering. Closure alone does not
  establish that the requested behavior shipped.
- https://github.com/open-webui/open-webui/issues/30362
  explains that moving chats changes updated_at and apparent recency. It
  requests message-based activity instead of general modification time.
- https://docs.openwebui.com/features/chat-conversations/chat-features/conversation-organization/
  describes nested folders and unread-first, recent-activity chat ordering,
  but does not document an activity-based folder-sort setting.

## Behavior contract

1. Offer Alphabetical and Recent chat activity as the two sort modes.
2. Preserve Alphabetical as the default for accounts without a preference.
3. Save ui.folderSort = alphabetical | recent_activity using the existing
   updateUserSettings flow. Select Recent chat activity for this user's account
   when deploying the feature.
4. In activity mode, calculate each nonempty folder's timestamp as the maximum
   coalesce(chat.updated_at, chat.created_at) across eligible chats in that
   folder and all its descendants. Normalize values to epoch seconds.
5. Ignore archived and internal chats, matching the visible sidebar population.
   Confirm the existing folder chat-list eligibility rules during implementation,
   including handling of pinned chats, and share those filters where practical.
6. For an empty subtree only, use folder.created_at. Do not let the creation time
   of a newly empty child outweigh real chat activity in a nonempty parent.
7. Rename, expansion, collapse, folder prompt edits, and reading a chat must not
   promote a folder merely because folder.updated_at or last_read_at changed.
8. Break timestamp ties by natural, case-insensitive folder name, then folder ID.
9. Sort siblings only; preserve parent-child relationships, owned/shared sections,
   selected folder, and expansion state.
10. When the newest chat is moved, archived, or deleted, recompute both affected
    subtrees and their ancestors; timestamps can decrease as well as increase.
11. Use current chat modification timestamps in version one. Moving a chat or
    other actions that change Chat.updated_at can affect ordering. A separate
    message-activity timestamp is a larger follow-up, not a hidden requirement
    for this change.

## Implementation steps

### 1. Compute activity on the server

- Add a batched max-activity helper in backend/open_webui/models/chats.py.
  Query folder_id and MAX(COALESCE(updated_at, created_at)), grouping eligible
  chats by folder_id. Do not load chat JSON and do not query once per folder.
- Add a reusable aggregation helper for rolling direct timestamps up the folder
  tree. Track whether a subtree has any eligible chat separately from its empty
  fallback. Use cycle protection and tolerate missing parents.
- Extend FolderNameIdResponse in backend/open_webui/models/folders.py with an
  optional last_activity_at field; do not repurpose folder.updated_at.
- Populate last_activity_at in backend/open_webui/routers/folders.py GET /folders/.
  Follow the existing ancestor aggregation approach used for unread counts.
- Include the same metadata in the shared-folder response. Reuse the existing
  folder chat access rules; only aggregate chats visible to the requesting user.
  Do not expose other users' private chat activity through shared folders.
- No new stored timestamp or database migration is necessary for the first
  version. Check the query plan before considering another index.

### 2. Add preference and consistent sorting

- Add a compact sort menu beside the Folders section header, using the existing
  dropdown components and user settings persistence in Sidebar.svelte.
- Add a pure comparator in src/lib/utils/folderSort.ts, with focused tests.
- Apply the comparator in Sidebar/Folders.svelte for root folders and in
  Sidebar/RecursiveFolder.svelte for every level of child folders.
- Pass the selected sort mode through recursive components, or consistently
  derive it from the settings store. Use copied arrays rather than mutating
  shared store arrays while sorting.
- Remove or align intermediate sorts in Sidebar.svelte so there is a single
  definition of sidebar folder order. Leave chat ordering within each folder
  and Move to Folder picker behavior unchanged unless separately requested.
- Add translated labels through the existing i18n mechanism.

### 3. Keep ordering fresh

- Extend the existing folder refresh path in src/lib/stores/chatList.ts and the
  Sidebar.svelte chat:list handler to refresh activity metadata after chat
  creation, updates, completed responses, imports, moves, deletes, archive/
  unarchive, bulk actions, and folder reparenting.
- Prefer one coalesced metadata request when multiple changes happen close
  together. Avoid a request for each streamed token and avoid remounting or
  reloading every folder's chat list just to reorder the folder tree.
- Refresh folder metadata on reconnect. Preserve expansion state and selection
  when applying results, and prevent older responses from replacing newer ones.
- Cover cross-tab updates using existing chat:list events. Audit event emission
  in backend/open_webui/main.py, utils/middleware.py, routers/chats.py,
  utils/automations.py, and socket/main.py. Add missing notifications only where
  necessary. Read-only last_read_at events need not recompute activity.
- Suspend visible reordering during drag-and-drop and apply pending order after
  the drag finishes so targets do not move under the pointer.

### 4. Verify and deploy

- Test aggregate timestamps for direct chats, deep descendants, empty trees,
  archived/internal exclusion, missing parents, cycle handling, and permissions.
- Test alphabetical mode, activity mode, tie-breaking, and all sibling levels.
- Test deleting/archiving/moving the newest chat, including downward timestamp
  changes and old/new ancestor paths.
- Test preference persistence, collapsed folders, paginated chat lists,
  reconnects, cross-tab updates, bulk actions, and automated chat creation.
- Confirm that expansion, collapse, reads, and folder renames do not promote
  folders, and that the existing unread badges and unread-first chat order work.
- Run focused backend tests and frontend Vitest tests, npm run check, and the
  frontend build. Record pre-existing check failures separately.
- Rebuild and deploy with the existing Wellington Compose workflow, preserving
  the data volume. Enable Recent chat activity for the user's account and verify
  the actual running instance interactively in BrowserOS neo.
- Roll back by reverting/redeploying the code or selecting Alphabetical; no chat
  migration or timestamp rewrite is needed.

## Expected result

Creating or updating a chat under Career / Job Search / Interviews raises Career
in the root list, Job Search among Career's children, and Interviews among Job
Search's children. This works even when all those folders are collapsed and
without loading every chat into the browser.

## Verification results

- Three frontend Vitest tests passed for both ordering modes and stable ties.
- Four backend unittest tests passed, including execution of the production
  aggregate query against SQLite with archived, internal, pinned, cross-user,
  and unauthorized-folder fixtures.
- The Docker production frontend build and image build passed.
- BrowserOS neo verification on an isolated instance of the built image passed
  for the sort menu, saved preference after reload, descendant activity,
  cross-tab chat updates, moves, deletion of the newest chat, archive exclusion,
  new chat creation, and unchanged activity after folder expansion, collapse,
  and rename.
- Existing single-chat archiving removes folder membership. An unarchived chat
  therefore contributes to folder activity only after being refiled; this
  existing behavior is preserved.
- The full type check remains blocked by existing repository diagnostics:
  7,021 errors and 197 warnings versus 7,025 errors and 197 warnings in a clean
  worktree of the pre-change commit.
- The built image was deployed to the main Docker instance. Its health check
  passed, and authenticated verification confirmed activity timestamps for all
  24 folders against the live SQLite metadata. Recent chat activity was enabled
  for the user's account while preserving unrelated settings, both accounts'
  chat counts, and database integrity.
