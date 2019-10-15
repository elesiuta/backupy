import unittest
import os
import shutil
import zlib
import zipfile
import time

import backupy

def crc(fileName, prev = 0):
    with open(fileName,"rb") as f:
        for line in f:
            prev = zlib.crc32(line, prev)
    return prev

def dirStats(path):
    total_crc = 0
    file_count = 0
    dir_count = 0
    total_file_size = 0
    total_folder_size = 0
    for dir_path, sub_dir_list, file_list in os.walk(path):
        sub_dir_list.sort()
        dir_count += len(sub_dir_list)
        file_count += len(file_list)
        total_folder_size += os.path.getsize(dir_path)
        for f in sorted(file_list):
            full_path = os.path.join(dir_path, f)
            total_file_size += os.path.getsize(full_path)
            total_crc += crc(full_path)
            total_crc %= (0xFFFFFFFF + 1)
    return {"total_crc": total_crc, "file_count": file_count, "dir_count": dir_count, "total_file_size": total_file_size, "total_folder_size": total_folder_size}

def setupTestDir(test_name):
    shutil.unpack_archive("backupy_test_dir.zip", test_name)
    with zipfile.ZipFile("backupy_test_dir.zip", "r") as z:
        for f in z.infolist():
            file_name = os.path.join(test_name, f.filename)
            date_time = time.mktime(f.date_time + (0, 0, -1))
            os.utime(file_name, (date_time, date_time))

def cleanupTestDir(test_name):
    shutil.rmtree(test_name)

def runTest(test_name, config):
    setupTestDir(test_name)
    config["source"] = os.path.join(test_name, "dir A")
    config["dest"] = os.path.join(test_name, "dir B")
    backup_man = backupy.BackupManager(config)
    backup_man.backup()
    dirA = dirStats(os.path.join(test_name, "dir A"))
    dirB = dirStats(os.path.join(test_name, "dir B"))
    dirAsol = dirStats(os.path.join("backupy_test_solutions", test_name, "dir A"))
    dirBsol = dirStats(os.path.join("backupy_test_solutions", test_name, "dir B"))
    cleanupTestDir(test_name)
    return dirA, dirB, dirAsol, dirBsol

class TestBackupy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree("backupy_test_solutions", ignore_errors=True)
        shutil.unpack_archive("backupy_test_solutions.zip", "backupy_test_solutions")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree("backupy_test_solutions")

    def test_mirror_new(self):
        test_name = "mirror-new"
        config = {"m": "mirror", "c": "new", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_mirror_source(self):
        test_name = "mirror-source"
        config = {"m": "mirror", "c": "source", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_mirror_dest(self):
        test_name = "mirror-dest"
        config = {"m": "mirror", "c": "dest", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_mirror_no(self):
        test_name = "mirror-no"
        config = {"m": "mirror", "c": "no", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_backup_new(self):
        test_name = "backup-new"
        config = {"m": "backup", "c": "new", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_backup_source(self):
        test_name = "backup-source"
        config = {"m": "backup", "c": "source", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_backup_dest(self):
        test_name = "backup-dest"
        config = {"m": "backup", "c": "dest", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_backup_no(self):
        test_name = "backup-no"
        config = {"m": "backup", "c": "no", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_sync_new(self):
        test_name = "sync-new"
        config = {"m": "sync", "c": "new", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_sync_source(self):
        test_name = "sync-source"
        config = {"m": "sync", "c": "source", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_sync_dest(self):
        test_name = "sync-dest"
        config = {"m": "sync", "c": "dest", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_sync_no(self):
        test_name = "sync-no"
        config = {"m": "sync", "c": "no", "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_mirror_new_archive(self):
        test_name = "mirror-new-archive"
        config = {"m": "mirror", "c": "new", "goahead": True, "suppress": True, "noarchive": False, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_backup_new_moved(self):
        test_name = "backup-new-moved"
        config = {"m": "backup", "c": "new", "d": True, "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_backup_new_moved_match(self):
        test_name = "backup-new-moved-match"
        config = {"m": "backup", "c": "new", "r": "match", "d": True, "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_backup_new_moved_all(self):
        test_name = "backup-new-moved-all"
        config = {"m": "backup", "c": "new", "r": "all", "d": True, "goahead": True, "suppress": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

    def test_mirror_new_moved_archive(self):
        test_name = "mirror-new-moved-archive"
        config = {"m": "mirror", "c": "new", "d": True, "goahead": True, "suppress": True, "noarchive": False, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol)
        self.assertEqual(dirB, dirBsol)

if __name__ == '__main__':
    unittest.main()
