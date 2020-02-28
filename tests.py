import unittest
import os
import shutil
import zlib
import zipfile
import time
import csv
import json

import backupy

def crc(fileName, prev = 0):
    with open(fileName,"rb") as f:
        for line in f:
            prev = zlib.crc32(line, prev)
    return prev

def readJson(file_path: str) -> dict:
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8", errors="surrogateescape") as json_file:
            data = json.load(json_file)
        return data
    return {}

def writeJson(file_path: str, data: dict, subdir: bool = True) -> None:
    if subdir and not os.path.isdir(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, "w", encoding="utf-8", errors="surrogateescape", newline="\r\n") as json_file:
        json.dump(data, json_file, indent=1, separators=(',', ': '))

def replaceDictKeySep(d):
    # replace path separators to windows for consistent testing
    new_d = {}
    for key in d:
        new_d[key.replace(os.path.sep, "\\")] = d[key]
    return new_d

def prerewriteDb(fName):
    # replace path separators so backupy can read database properly
    if os.path.exists(fName):
        db = readJson(fName)
        new_db = {}
        for key in db:
            new_db[key.replace("\\", os.path.sep)] = db[key]
        writeJson(fName, new_db)

def rewriteDb(fName):
    # replace path separators to windows for consistent testing
    if os.path.exists(fName):
        db = readJson(fName)
        writeJson(fName, replaceDictKeySep(db))

def rewriteSep(fName):
    # replace path separators to windows for consistent testing
    if os.path.exists(fName):
        with open(fName, "r") as f:
            data = []
            for row in f.readlines():
                data.append(row.replace(os.path.sep, "\\"))
        with open(fName, "w", encoding="utf-8", newline="\r\n") as f:
            f.writelines(data)

def rewriteLineEndings(fName):
    # rewrite line endings to windows (for the posix sep test)
    if os.path.exists(fName):
        with open(fName, "r") as f:
            data = f.readlines()
        with open(fName, "w", encoding="utf-8", newline="\r\n") as f:
            f.writelines(data)

def rewriteLog(fName):
    # rewrite paths as relative to cwd and remove settings
    if os.path.exists(fName):
        cwd = os.getcwd()
        cwd2 = cwd.replace(os.path.sep, "\\")
        cwd3 = cwd.replace("\\", "\\\\")
        cwd4 = cwd.replace(os.path.sep, "/")
        with open(fName, "r") as f:
            data = []
            reader = csv.reader(f)
            settings_line_count = 2
            for row in reader:
                if settings_line_count > 0:
                    settings_line_count -= 1
                    continue
                new_row = []
                for col in row:
                    if type(col) == str:
                        col = col.replace(cwd, "")
                        col = col.replace(cwd2, "")
                        col = col.replace(cwd3, "")
                        col = col.replace(cwd4, "")
                    new_row.append(col)
                data.append(new_row)
        with open(fName, "w", newline="", encoding="utf-8", errors="backslashreplace") as f:
            writer = csv.writer(f, delimiter=",")
            for row in data:
                writer.writerow(row)

def dirInfo(path, skip_time = True):
    # just used for assert message on failure to help with debugging
    file_dicts = {}
    for dir_path, subdir_list, file_list in os.walk(path):
        subdir_list.sort()
        for subdir in subdir_list:
            full_path = os.path.join(dir_path, subdir)
            if not skip_time:
                relativePath = os.path.relpath(full_path, path).replace(os.path.sep, "\\") + "\\"
                file_dicts[relativePath] = {"size": os.path.getsize(full_path), "mtime": os.path.getmtime(full_path), "crc": 0, "dir": True}
            elif len(os.listdir(full_path)) == 0:
                relativePath = os.path.relpath(full_path, path).replace(os.path.sep, "\\")
                file_dicts[relativePath] = {"size": 0, "mtime": 0, "crc": 0, "dir": True}
        for fName in sorted(file_list):
            full_path = os.path.join(dir_path, fName)
            relativePath = os.path.relpath(full_path, path).replace(os.path.sep, "\\")
            size = os.path.getsize(full_path)
            if skip_time:
                mtime = 0
            else:
                mtime = os.path.getmtime(full_path)
            file_dicts[relativePath] = {"size": size, "mtime": mtime, "crc": crc(full_path)}
    return file_dicts

def dirCompare(info_a, info_b):
    # just used for assert message on failure to help with debugging
    a_only = []
    b_only = []
    different = []
    info_a = replaceDictKeySep(info_a)
    info_b = replaceDictKeySep(info_b)    
    for relativePath in info_a:
        if relativePath in info_b:
            if info_a[relativePath]["crc"] != info_b[relativePath]["crc"]:
                    different.append(relativePath)
        else:
            a_only.append(relativePath)
    for relativePath in info_b:
        if relativePath not in info_a:
            b_only.append(relativePath)
    return a_only, b_only, different

def dirStats(path):
    # used to check if the test run matches the solution
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

def getTestTime(test_zip):
    shutil.rmtree("test_dir", ignore_errors=True)
    shutil.unpack_archive(test_zip, "test_dir")
    with zipfile.ZipFile(test_zip, "r") as z:
        for f in z.infolist():
            file_name = os.path.join("test_dir", f.filename)
            date_time = time.mktime(f.date_time + (0, 0, -1))
            os.utime(file_name, (date_time, date_time))
    writeJson(test_zip + ".json", dirInfo("test_dir", False))

def setupTestDir(test_name, test_zip):
    shutil.rmtree(test_name, ignore_errors=True)
    shutil.unpack_archive(test_zip, test_name)
    test_time = readJson(test_zip + ".json")
    with zipfile.ZipFile(test_zip, "r") as z:
        for f in z.infolist():
            file_name = os.path.join(test_name, f.filename)
            relativePath = f.filename.replace("/", "\\")
            date_time = test_time[relativePath]["mtime"]
            os.utime(file_name, (date_time, date_time))

def cleanupTestDir(test_name):
    shutil.rmtree(test_name)

def runTest(test_name, config, set=0, rewrite_log=True, rewrite_sep=True, compare=True, setup=True, cleanup=True, write_solution=False):
    # init dirs
    if setup:
        print("####### TEST: " + test_name + " #######")
        setupTestDir(test_name, "tests/test_dir_set%s.zip" %(str(set)))
    if set == 1:
        dir_A = "dir A set 1"
        dir_B = "dir B set 1"
    else:
        dir_A = "dir A"
        dir_B = "dir B"
    dir_A_path = os.path.join(test_name, dir_A)
    dir_B_path = os.path.join(test_name, dir_B)
    sol_path = os.path.join("tests", "test_solutions", test_name)
    dir_A_sol_path = os.path.join(sol_path, dir_A)
    dir_B_sol_path = os.path.join(sol_path, dir_B)
    # fix separators for running tests on linux
    if os.name != "nt" and rewrite_sep:
        if "config_dir" in config:
            db_dir = config["config_dir"]
        else:
            db_dir = ".backupy"
        prerewriteDb(os.path.join(dir_A_path, db_dir, "database.json"))
        prerewriteDb(os.path.join(dir_B_path, db_dir, "database.json"))
    # run backup
    config["source"] = dir_A_path
    config["dest"] = dir_B_path
    backup_man = backupy.BackupManager(config)
    backup_man.backup()
    # fix separators and line endings again, and remove absolute paths
    if rewrite_log:
        if "log_dir" in config:
            log_dir = config["log_dir"]
        else:
            log_dir = ".backupy/Logs"
        rewriteLog(os.path.join(dir_A_path, log_dir, "log-000000-0000.csv"))
        if rewrite_sep:
            rewriteSep(os.path.join(dir_A_path, log_dir, "log-000000-0000.csv"))
    if "config_dir" in config:
        db_dir = config["config_dir"]
    else:
        db_dir = ".backupy"
    if rewrite_sep:
        rewriteDb(os.path.join(dir_A_path, db_dir, "database.json"))
        rewriteDb(os.path.join(dir_B_path, db_dir, "database.json"))
        rewriteDb(os.path.join(dir_A_path, db_dir, "database.tmp.json"))
        rewriteDb(os.path.join(dir_B_path, db_dir, "database.tmp.json"))
    else:
        rewriteLineEndings(os.path.join(dir_A_path, db_dir, "database.json"))
        rewriteLineEndings(os.path.join(dir_B_path, db_dir, "database.json"))
        rewriteLineEndings(os.path.join(dir_A_path, db_dir, "database.tmp.json"))
        rewriteLineEndings(os.path.join(dir_B_path, db_dir, "database.tmp.json"))
    # save solution info for updating or creating new tests, CAREFULLY INSPECT THE CHANGES AFTERWARDS
    if write_solution:
        shutil.rmtree(dir_A_sol_path, ignore_errors=True)
        shutil.rmtree(dir_B_sol_path, ignore_errors=True)
        shutil.move(dir_A_path, dir_A_sol_path)
        shutil.move(dir_B_path, dir_B_sol_path)
        writeJson(os.path.join(sol_path, "dir_A_stats.json"), dirStats(dir_A_sol_path))
        writeJson(os.path.join(sol_path, "dir_B_stats.json"), dirStats(dir_B_sol_path))
        writeJson(os.path.join(sol_path, "dir_A_info.json"), dirInfo(dir_A_sol_path))
        writeJson(os.path.join(sol_path, "dir_B_info.json"), dirInfo(dir_B_sol_path))
    # compare current run to solution
    if compare:
        dirA_stats = dirStats(dir_A_path)
        dirB_stats = dirStats(dir_B_path)
        dirAsol_stats = readJson(os.path.join(sol_path, "dir_A_stats.json"))
        dirBsol_stats = readJson(os.path.join(sol_path, "dir_B_stats.json"))
        a_test, a_sol, a_diff = dirCompare(dirInfo(dir_A_path), readJson(os.path.join(sol_path, "dir_A_info.json")))
        b_test, b_sol, b_diff = dirCompare(dirInfo(dir_B_path), readJson(os.path.join(sol_path, "dir_B_info.json")))
        compDict = {"a_test_only": a_test, "a_sol_only": a_sol, "a_diff": a_diff, "b_test_only": b_test, "b_sol_only": b_sol, "b_diff": b_diff}
        if os.name != "nt":
            _ = dirA_stats.pop("total_folder_size")
            _ = dirB_stats.pop("total_folder_size")
            _ = dirAsol_stats.pop("total_folder_size")
            _ = dirBsol_stats.pop("total_folder_size")
    # helps to leave this for debugging when tests fail, or creating new test solutions
    if cleanup:
        cleanupTestDir(test_name)
    if compare:
        return dirA_stats, dirB_stats, dirAsol_stats, dirBsol_stats, compDict

class TestBackupy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass
        # shutil.rmtree("test_solutions", ignore_errors=True)
        # shutil.unpack_archive("tests/test_solutions.zip", "test_solutions")
        # shutil.unpack_archive("tests/test_solutions_set1.zip", "test_solutions")

    @classmethod
    def tearDownClass(cls):
        pass
        # shutil.rmtree("test_solutions")

    def test_mirror_new(self):
        test_name = "mirror-new"
        config = {"main_mode": "mirror", "select_mode": "new", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source(self):
        test_name = "mirror-source"
        config = {"main_mode": "mirror", "select_mode": "source", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_dest(self):
        test_name = "mirror-dest"
        config = {"main_mode": "mirror", "select_mode": "dest", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_no(self):
        test_name = "mirror-no"
        config = {"main_mode": "mirror", "select_mode": "no", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_backup_new(self):
        test_name = "backup-new"
        config = {"main_mode": "backup", "select_mode": "new", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_backup_source(self):
        test_name = "backup-source"
        config = {"main_mode": "backup", "select_mode": "source", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_backup_dest(self):
        test_name = "backup-dest"
        config = {"main_mode": "backup", "select_mode": "dest", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_backup_no(self):
        test_name = "backup-no"
        config = {"main_mode": "backup", "select_mode": "no", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_new(self):
        test_name = "sync-new"
        config = {"main_mode": "sync", "select_mode": "new", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_source(self):
        test_name = "sync-source"
        config = {"main_mode": "sync", "select_mode": "source", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_dest(self):
        test_name = "sync-dest"
        config = {"main_mode": "sync", "select_mode": "dest", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_no(self):
        test_name = "sync-no"
        config = {"main_mode": "sync", "select_mode": "no", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_new_archive(self):
        test_name = "mirror-new-archive"
        config = {"main_mode": "mirror", "select_mode": "new", "nomoves": True, "noprompt": True, "nolog": True, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_backup_new_moved(self):
        test_name = "backup-new-moved"
        config = {"main_mode": "backup", "select_mode": "new", "nomoves": False, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_backup_new_moved_match(self):
        test_name = "backup-new-moved-match"
        config = {"main_mode": "backup", "select_mode": "new", "compare_mode": "crc", "nomoves": False, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_backup_new_moved_all(self):
        test_name = "backup-new-moved-all"
        config = {"main_mode": "backup", "select_mode": "new", "compare_mode": "crc", "nomoves": False, "noprompt": True, "nolog": True, "noarchive": True}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_new_moved_archive(self):
        test_name = "mirror-new-moved-archive"
        config = {"main_mode": "mirror", "select_mode": "new", "nomoves": False, "noprompt": True, "nolog": True, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_new_log(self):
        test_name = "sync-new-log"
        config = {"main_mode": "sync", "select_mode": "new", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_new_log_set1(self):
        test_name = "sync-new-log-set1"
        config = {"main_mode": "sync", "select_mode": "new", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=1)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_new_log_dry_run_set1(self):
        test_name = "sync-new-log-dry_run-set1"
        config = {"main_mode": "sync", "select_mode": "new", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "dry_run": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=1)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_new_nolog_dry_run_set1(self):
        test_name = "sync-new-nolog-dry_run-set1"
        config = {"main_mode": "sync", "select_mode": "new", "nomoves": False, "noprompt": True, "nolog": True, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "dry_run": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=False, rewrite_sep=False, set=1)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_log_set1(self):
        test_name = "mirror-source-log-set1"
        config = {"main_mode": "mirror", "select_mode": "source", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=1)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_log_dir_set1(self):
        test_name = "mirror-source-log-dir-set1"
        config = {"main_mode": "mirror", "select_mode": "source", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy/Config", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=1)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_log_dir_set0(self):
        test_name = "mirror-source-log-dir-set0"
        config = {"main_mode": "mirror", "select_mode": "source", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy/Config", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=0)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_twice_nochanges(self):
        test_name = "sync-twice-nochanges-set1"
        config = {"main_mode": "sync", "select_mode": "new", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy", "config_dir": ".backupy", "log_dir": ".backupy", "trash_dir": ".backupy/Deleted", "backup_time_override": "000000-0000"}
        runTest(test_name, config, rewrite_log=True, set=1, compare=False, setup=True, cleanup=False, write_solution=False)
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=1, setup=False)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_filter(self):
        test_name = "mirror-source-filter"
        config = {"main_mode": "mirror", "select_mode": "source", "filter_list": ["modified"], "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy/Config", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=0)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_filter_false(self):
        test_name = "mirror-source-filter-false"
        config = {"main_mode": "mirror", "select_mode": "source", "filter_exclude_list": ["modified"], "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy/Config", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=0)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_set2(self):
        test_name = "mirror-source-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_attrplus_set2(self):
        test_name = "mirror-source-attrplus-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "attr+", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_crc_set2(self):
        test_name = "mirror-source-crc-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "crc", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_posix(self):
        test_name = "mirror-source-posix"
        config = {"main_mode": "mirror", "select_mode": "source", "force_posix_path_sep": True, "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": True, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, rewrite_sep=False, set=0)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_aliaslog_set2(self):
        test_name = "mirror-source-aliaslog-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": True, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_source_attrplus_set2(self):
        test_name = "sync-source-attrplus-set2"
        config = {"main_mode": "sync", "select_mode": "source", "compare_mode": "attr+", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_sync_source_crc_set2(self):
        test_name = "sync-source-crc-set2"
        config = {"main_mode": "sync", "select_mode": "source", "compare_mode": "crc", "nomoves": False, "noprompt": True, "nolog": False, "root_alias_log": False, "noarchive": False, "archive_dir": ".backupy/Archive", "config_dir": ".backupy", "log_dir": ".backupy/Logs", "trash_dir": ".backupy/Trash", "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_verifycopy_set2(self):
        test_name = "mirror-source-verifycopy-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "attr", "verify_copy": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_verifycopyplus_set2(self):
        test_name = "mirror-source-verifycopyplus-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "attr+", "verify_copy": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_verifycopycrc_set2(self):
        test_name = "mirror-source-verifycopycrc-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "crc", "verify_copy": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_scanonly_set2(self):
        test_name = "mirror-source-scanonly-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "attr+", "scan_only": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_scanonlycrc_set2(self):
        test_name = "mirror-source-scanonlycrc-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "crc", "scan_only": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_qconflicts_set2(self):
        test_name = "mirror-source-qconflicts-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "quit_on_db_conflict": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_qconflictscrc_set2(self):
        test_name = "mirror-source-qconflictscrc-set2"
        config = {"main_mode": "mirror", "select_mode": "source", "compare_mode": "crc", "quit_on_db_conflict": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=2)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_qconflicts_set1(self):
        test_name = "mirror-source-qconflicts-set1"
        config = {"main_mode": "mirror", "select_mode": "source", "quit_on_db_conflict": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=1)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

    def test_mirror_source_qconflicts_set0(self):
        test_name = "mirror-source-qconflicts-set0"
        config = {"main_mode": "mirror", "select_mode": "source", "quit_on_db_conflict": True, "noprompt": True, "backup_time_override": "000000-0000"}
        dirA, dirB, dirAsol, dirBsol, compDict = runTest(test_name, config, rewrite_log=True, set=0)
        self.assertEqual(dirA, dirAsol, str(compDict))
        self.assertEqual(dirB, dirBsol, str(compDict))

if __name__ == '__main__':
    unittest.main()
