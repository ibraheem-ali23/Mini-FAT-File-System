import os
import shlex
from FileSystem import FileSystem
from virtual_disk import VirtualDisk
from fat_table_manager import FatTableManager
from directory_manager import DirectoryManager
from superblock_manager import SuperblockManager
from fs_constants import FsConstants
from Converter import Converter


# -------------------- Helper -------------------- #


def clear_screen():
    print("\n" * 50)


def print_help():
    print(
        """
Available commands:
cd [dir]          - Change current directory
ls [dir]          - List contents
md <dir>       - Create directory
rd <dir>       - Remove empty directory
touch <file>      - Create file
rm <file>         - Delete file
mv <src> <dst>    - Rename / move file
cp <src> <dst>    - Copy file
cat <file>        - Show file contents
echo "text" <file> [--append]
cls             - Clear screen
help              - Show help
exit              - Exit shell
"""
    )


# -------------------- Shell -------------------- #


class MiniFATShell:

    def __init__(self):
        disk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "minifat.bin"))
        is_new_disk = not os.path.exists(disk_path)

        self.vd = VirtualDisk()
        self.vd.Initialize(disk_path, createIfMissing=True)

        self.fat = FatTableManager(self.vd)
        self.dir_manager = DirectoryManager(self.vd, self.fat)
        self.fs = FileSystem(self.vd, self.fat, self.dir_manager)

        if is_new_disk:
            sb = SuperblockManager(self.vd)
            sb.WriteSuperblock(bytes(FsConstants.CLUSTER_SIZE))

            # initialize FAT cleanly
            self.fat.fat = [0] * FsConstants.CLUSTER_COUNT
            for c in self.fat.reserved_clusters:
                self.fat.fat[c] = -1
            self.fat.FlushFatToDisk()

            # initialize root directory cluster
            self.vd.WriteCluster(FsConstants.ROOT_DIR_FIRST_CLUSTER, bytes(FsConstants.CLUSTER_SIZE))
        else:
            self.fat.LoadFatFromDisk()

        self.cwd_cluster = FsConstants.ROOT_DIR_FIRST_CLUSTER
        self.cwd_stack = []  # for cd ..
        self.cwd_path = "T:\\"

        print("MiniFAT Shell initialized!")
        print("Type 'help' to see commands.\n")

    # ---------------- Utility ---------------- #

    def is_directory(self, entry):
        return entry.file_size == 0 and entry.first_cluster != -1

    # ---------------- Shell Loop ---------------- #

    def run(self):
        while True:
            try:
                cmd_line = input(f"{self.cwd_path}> ").strip()
                if not cmd_line:
                    continue

                tokens = shlex.split(cmd_line)
                command = tokens[0].lower()
                args = tokens[1:]

                if command == "exit":
                    break
                elif command == "help":
                    print_help()
                elif command == "cls":
                    clear_screen()
                elif command == "cd":
                    self.cmd_cd(args)
                elif command == "ls":
                    self.cmd_ls(args)
                elif command == "md":
                    self.cmd_mkdir(args)
                elif command == "rd":
                    self.cmd_rmdir(args)
                elif command == "touch":
                    self.cmd_touch(args)
                elif command == "rm":
                    self.cmd_rm(args)
                elif command == "mv":
                    self.cmd_mv(args)
                elif command == "cp":
                    self.cmd_cp(args)
                elif command == "cat":
                    self.cmd_cat(args)
                elif command == "echo":
                    self.cmd_echo(args)
                else:
                    print(f"Unknown command: {command}")

            except Exception as e:
                print("Error:", e)

        self.vd.CloseDisk()
        print("Exiting shell.")

    # ---------------- Commands ---------------- #

    def cmd_cd(self, args):
        if not args:
            print(self.cwd_path)
            return

        if args[0] == "..":
            if self.cwd_stack:
                self.cwd_cluster = self.cwd_stack.pop()
                self.cwd_path = os.path.dirname(self.cwd_path.rstrip("\\"))
                if not self.cwd_path.endswith("\\"):
                    self.cwd_path += "\\"
            return

        entry = self.dir_manager.FindDirectoryEntry(self.cwd_cluster, args[0])
        if entry and self.is_directory(entry):
            self.cwd_stack.append(self.cwd_cluster)
            self.cwd_cluster = entry.first_cluster
            self.cwd_path = os.path.join(self.cwd_path, args[0]) + "\\"
        else:
            print(f"Directory '{args[0]}' not found")

    def cmd_ls(self, args):
        cluster = self.cwd_cluster
        if args:
            entry = self.dir_manager.FindDirectoryEntry(self.cwd_cluster, args[0])
            if not entry or not self.is_directory(entry):
                print(f"Directory '{args[0]}' not found")
                return
            cluster = entry.first_cluster

        entries = self.dir_manager.ReadDirectory(cluster)

        if not entries:
            print("<EMPTY Directory>")
            return

        for e in entries:
            t = "<DIR>" if self.is_directory(e) else "<FILE>"
            print(f"{t}\t{e.name}\t{e.file_size}")

    def cmd_mkdir(self, args):
        if not args:
            print("Usage: md <dir>")
            return
        self.fs.create_directory(self.cwd_cluster, args[0])
        print("Directory created.")

    def cmd_rmdir(self, args):
        if not args:
            print("Usage: rd <dir>")
            return
        self.fs.remove_directory(self.cwd_cluster, args[0])
        print("Directory removed.")

    def cmd_touch(self, args):
        if not args:
            print("Usage: touch <file>")
            return
        self.fs.create_file(self.cwd_cluster, args[0])
        print("File created.")

    def cmd_rm(self, args):
        if not args:
            print("Usage: rm <file>")
            return
        self.fs.delete_file(self.cwd_cluster, args[0])
        print("File deleted.")

    def cmd_mv(self, args):
        if len(args) != 2:
            print("Usage: mv <src> <dst>")
            return

        src = args[0]
        dst_path = args[1]

        # --- Check if source exists in current directory ---
        entries = self.dir_manager.ReadDirectory(self.cwd_cluster)
        src_entry = next((e for e in entries if e.name.upper() == src.upper()), None)
        if not src_entry:
            print(f"Error: File or directory '{src}' does not exist.")
            return

        # --- Split destination path ---
        if "/" in dst_path:
            parts = dst_path.split("/")
            dst_name = parts[-1]
            dst_dir_parts = parts[:-1]
        else:
            dst_name = None
            dst_dir_parts = [dst_path]

        # --- Resolve destination directory cluster ---
        dst_cluster = self.cwd_cluster
        for i, part in enumerate(dst_dir_parts):
            entries = self.dir_manager.ReadDirectory(dst_cluster)
            entry = next((e for e in entries if e.name.upper() == part.upper() and e.file_size == 0), None)

            # fallback to root for first part if not found
            if not entry and i == 0:
                entries = self.dir_manager.ReadDirectory(FsConstants.ROOT_DIR_FIRST_CLUSTER)
                entry = next((e for e in entries if e.name.upper() == part.upper() and e.file_size == 0), None)

            if not entry:
                # If it's the last part and no directory, treat as rename
                if i == len(dst_dir_parts) - 1:
                    dst_name = part
                    break
                print(f"Error: Destination directory '{'/'.join(dst_dir_parts)}' does not exist.")
                return

            dst_cluster = entry.first_cluster

        # --- If last part is a directory → move into it ---
        if dst_name is None:
            self.move(src_entry.name, dst_cluster, src_entry.name)
            return

        # --- Check if destination filename already exists ---
        entries = self.dir_manager.ReadDirectory(dst_cluster)
        if any(e.name.upper() == dst_name.upper() for e in entries):
            print(f"Error: File or directory '{dst_name}' already exists in destination.")
            return

        # --- Decide: rename or move ---
        if dst_cluster == self.cwd_cluster:
            self.rename(src_entry.name, dst_name)
        else:
            self.move(src_entry.name, dst_cluster, dst_name)

    def rename(self, src, dst):
        # Check if source file exists
        entry = self.dir_manager.FindDirectoryEntry(self.cwd_cluster, src)
        if not entry:
            print(f"Error: File '{src}' does not exist.")
            return

        # Check if destination already exists
        if self.dir_manager.FindDirectoryEntry(self.cwd_cluster, dst):
            print(f"Error: File '{dst}' already exists.")
            return

        # Perform rename using move_file inside the same directory
        self.fs.move_file(self.cwd_cluster, src, self.cwd_cluster, dst)
        print("Rename complete.")

    def move(self, src, dst_cluster, dst_name):
        # Check if source file exists
        entry = self.dir_manager.FindDirectoryEntry(self.cwd_cluster, src)
        if not entry:
            print(f"Error: File '{src}' does not exist.")
            return

        # Check if destination directory exists
        if dst_cluster is None:
            print(f"Error: Destination directory does not exist.")
            return

        # Check if destination file already exists in destination directory
        if self.dir_manager.FindDirectoryEntry(dst_cluster, dst_name):
            print(f"Error: File '{dst_name}' already exists in destination.")
            return

        # Perform move
        self.fs.move_file(self.cwd_cluster, src, dst_cluster, dst_name)
        print("Move complete.")

    def cmd_cp(self, args):
        if len(args) != 2:
            print("Usage: cp <src> <dst>")
            return

        src = args[0]
        dst = args[1]

        # Check if source exists
        src_entry = self.dir_manager.FindDirectoryEntry(self.cwd_cluster, src)
        if not src_entry:
            print(f"Error: Source file '{src}' does not exist.")
            return

        # Check if destination exists as a directory
        dst_entry = self.dir_manager.FindDirectoryEntry(self.cwd_cluster, dst)
        if dst_entry and dst_entry.file_size == 0:  # it's a directory
            dst_cluster = dst_entry.first_cluster
            dst_name = src_entry.name  # keep the same name
        else:
            dst_cluster = self.cwd_cluster
            dst_name = dst

            # Check if a file already exists with that name
            if self.dir_manager.FindDirectoryEntry(dst_cluster, dst_name):
                print(f"Error: File '{dst_name}' already exists.")
                return

        # Perform the copy
        self.fs.copy_file(self.cwd_cluster, src_entry.name, dst_cluster, dst_name)
        print("Copy complete.")

    def cmd_echo(self, args):
        if len(args) < 2:
            print('Usage: echo "text" <file> [--append]')
            return

        text = args[0]
        file_name = args[1]
        append = len(args) > 2 and args[2] == "--append"

        if append:
            try:
                text = self.fs.read_file(self.cwd_cluster, file_name) + text
            except FileNotFoundError:
                pass

        self.fs.write_file(self.cwd_cluster, file_name, text)
        print("Write complete.")

    def cmd_cat(self, args):
        if not args:
            print("Usage: cat <file>")
            return
        print(self.fs.read_file(self.cwd_cluster, args[0]))


# -------------------- Run -------------------- #

if __name__ == "__main__":
    MiniFATShell().run()
