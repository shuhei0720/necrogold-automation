"""A new device test reuses verified publication with a separate namespace."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import zipfile

from necroprobe import test069 as publication
from tests.test_native_publication069 import seed


class Release070Tests(unittest.TestCase):
    def test_new_number_isolates_archive_root_and_prevents_a_second_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root/'local'/'test-070'
            mounted = root/'mounted'
            mounted.mkdir()
            old = root/'local'/'test-069'
            previous = seed(old, 'b'*32)
            before = (old/'active.json').read_bytes()
            record = seed(base)
            session = Mock(side_effect=AssertionError('publish the completed run before another game'))
            result, archive = publication.run(mounted, spool=base, session=session,
                test_number='070', notice=lambda _: None)
            self.assertEqual('test-070-'+record['run_id']+'.zip', archive.name)
            self.assertEqual(record['run_id'], result['run_id'])
            session.assert_not_called()
            with zipfile.ZipFile(archive) as contents:
                self.assertIsNone(contents.testzip())
                self.assertTrue(all(name.startswith('test-070/') for name in contents.namelist()))
                self.assertNotIn(previous['run_id'], ''.join(contents.namelist()))
            self.assertEqual(before, (old/'active.json').read_bytes())

    def test_missing_publication_is_repaired_before_a_new_run_and_default_069_stays(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for number in ('069', '070'):
                base = root/'local'/('test-'+number)
                mounted = root/number
                mounted.mkdir()
                record = seed(base)
                options = {} if number == '069' else {'test_number': number}
                session = Mock(side_effect=AssertionError('a missing ZIP is not a new game'))
                _, archive = publication.run(mounted, spool=base, session=session,
                    notice=lambda _: None, **options)
                self.assertEqual('test-'+number+'-'+record['run_id']+'.zip', archive.name)
                archive.unlink()
                _, restored = publication.run(mounted, spool=base, session=session,
                    notice=lambda _: None, **options)
                self.assertTrue(restored.is_file())
                session.assert_not_called()

    def test_invalid_numbers_do_not_read_journals_or_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for value in ('../070', '70', '０７０', '', 70, None):
                with self.subTest(value=value):
                    session = Mock()
                    with self.assertRaises(publication.PublicationError):
                        publication.run(root, spool=root/'uncreated', session=session,
                            test_number=value, notice=lambda _: None)
                    session.assert_not_called()
                    self.assertFalse((root/'uncreated').exists())
