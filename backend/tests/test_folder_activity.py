import unittest
import ast
import os
from contextlib import asynccontextmanager
from pathlib import Path

from open_webui.utils.folder_activity import folder_activity_timestamps


class FolderActivityTests(unittest.TestCase):
    def setUp(self):
        self.folders = [
            {'id': 'career', 'parent_id': None, 'created_at': 1},
            {'id': 'search', 'parent_id': 'career', 'created_at': 2},
            {'id': 'interviews', 'parent_id': 'search', 'created_at': 3},
            {'id': 'empty', 'parent_id': 'career', 'created_at': 999},
        ]

    def test_deep_activity_promotes_all_ancestors_not_empty_creation(self):
        result = folder_activity_timestamps(self.folders, {'interviews': 100, 'career': 50})
        self.assertEqual(result, {'career': 100, 'search': 100, 'interviews': 100, 'empty': 999})

    def test_removed_latest_chat_allows_activity_to_decrease(self):
        result = folder_activity_timestamps(self.folders, {'career': 50})
        self.assertEqual(result['career'], 50)
        self.assertEqual(result['search'], 2)

    def test_cycles_missing_parents_and_unrecognized_activity(self):
        folders = [
            {'id': 'a', 'parent_id': 'b'},
            {'id': 'b', 'parent_id': 'a'},
            {'id': 'orphan', 'parent_id': 'missing'},
        ]
        self.assertEqual(
            folder_activity_timestamps(folders, {'a': 10, 'orphan': 20, 'private': 99}),
            {'a': 10, 'b': 10, 'orphan': 20},
        )


class FolderActivityQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_query_excludes_hidden_chats_and_scopes_ownership(self):
        # Exercise the production query against SQLite without initializing the
        # application or pointing its migration machinery at a real database.
        from sqlalchemy import JSON, Boolean, Column, Integer, String, create_engine, func, or_, select
        from sqlalchemy.orm import Session, declarative_base

        base = declarative_base()

        class Chat(base):
            __tablename__ = 'chat'
            id = Column(String, primary_key=True)
            folder_id = Column(String)
            user_id = Column(String)
            archived = Column(Boolean)
            pinned = Column(Boolean)
            meta = Column(JSON)
            updated_at = Column(Integer)
            created_at = Column(Integer)

        engine = create_engine('sqlite://')
        base.metadata.create_all(engine)
        with Session(engine) as session:
            for id, folder, user, updated, archived, pinned, meta in [
                ('old', 'a', 'owner', 10, False, None, {}),
                ('new', 'a', 'owner', 20, False, False, {}),
                ('archived', 'a', 'owner', 900, True, False, {}),
                ('internal', 'a', 'owner', 901, False, False, {'internal': True}),
                ('pinned', 'a', 'owner', 902, False, True, {}),
                ('other-user', 'a', 'other', 30, False, False, {}),
                ('private-folder', 'private', 'other', 999, False, False, {}),
                ('created-only', 'b', 'owner', None, False, False, {}),
            ]:
                session.add(Chat(id=id, folder_id=folder, user_id=user, updated_at=updated,
                                 created_at=5, archived=archived, pinned=pinned, meta=meta))
            session.commit()

            class AsyncSessionAdapter:
                async def execute(self, statement):
                    return session.execute(statement)

            @asynccontextmanager
            async def db_context(_db):
                yield AsyncSessionAdapter()

            source = Path(os.environ.get('FOLDER_ACTIVITY_QUERY_SOURCE') or
                          Path(__file__).parents[1] / 'open_webui/models/chats.py')
            tree = ast.parse(source.read_text(encoding='utf-8'))
            method = next(node for node in ast.walk(tree)
                          if isinstance(node, ast.AsyncFunctionDef) and node.name == 'get_activity_by_folder_ids')
            namespace = dict(Chat=Chat, select=select, func=func, or_=or_,
                             get_async_db_context=db_context, AsyncSession=object)
            exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
            query = namespace['get_activity_by_folder_ids']
            self.assertEqual(await query(None, ['a', 'b'], user_id='owner'), {'a': 20, 'b': 5})
            self.assertEqual(await query(None, ['a']), {'a': 30})
            self.assertEqual(await query(None, []), {})
        engine.dispose()


if __name__ == '__main__':
    unittest.main()
