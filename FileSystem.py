from virtual_disk import VirtualDisk
from fat_table_manager import FatTableManager
from directory_manager import DirectoryManager, DirectoryEntry
from Converter import Converter
from fs_constants import FsConstants


class FileSystem:
    def __init__(self, virtual_disk: VirtualDisk, fat_table: FatTableManager, dir_manager: DirectoryManager):
        self.disk = virtual_disk
        self.fat = fat_table
        self.dir = dir_manager

    # ---------------- File Operations ---------------- #

    def create_file(self, parent_cluster: int, file_name: str):
        formatted = self.dir.Parse8Dot3Name(self.dir.FormatNameTo8Dot3(file_name))

        if self.dir.FindDirectoryEntry(parent_cluster, formatted):
            raise FileExistsError(f"File '{file_name}' already exists as '{formatted}'.")

        entry = DirectoryEntry(name=file_name, attr=0, first_cluster=-1, file_size=0)
        self.dir.AddDirectoryEntry(parent_cluster, entry)

    def write_file(self, parent_cluster: int, file_name: str, content: str):
        entry = self.dir.FindDirectoryEntry(parent_cluster, file_name)
        if entry is None:
            raise FileNotFoundError(f"File '{file_name}' not found.")

        # directory check (file_size == 0 AND has cluster)
        if entry.file_size == 0 and entry.first_cluster != -1:
            raise IsADirectoryError(f"Cannot write to directory '{file_name}'.")

        data = Converter.StringToBytes(content)
        clusters_needed = (len(data) + FsConstants.CLUSTER_SIZE - 1) // FsConstants.CLUSTER_SIZE

        # free old data
        if entry.first_cluster > 0:
            self.fat.FreeChain(entry.first_cluster)
            entry.first_cluster = -1

        if clusters_needed > 0:
            start_cluster = self.fat.AllocateChain(clusters_needed)
            entry.first_cluster = start_cluster

            chain = self.fat.FollowChain(start_cluster)
            offset = 0

            for cluster in chain:
                chunk = data[offset : offset + FsConstants.CLUSTER_SIZE]
                buffer = bytearray(FsConstants.CLUSTER_SIZE)
                buffer[: len(chunk)] = chunk
                self.disk.WriteCluster(cluster, buffer)
                offset += FsConstants.CLUSTER_SIZE

        entry.file_size = len(data)
        self.dir.AddDirectoryEntry(parent_cluster, entry)

    def read_file(self, parent_cluster: int, file_name: str) -> str:
        entry = self.dir.FindDirectoryEntry(parent_cluster, file_name)
        if entry is None:
            raise FileNotFoundError(f"File '{file_name}' not found.")

        if entry.file_size == 0 and entry.first_cluster != -1:
            raise IsADirectoryError(f"Cannot read directory '{file_name}'.")

        if entry.first_cluster == -1 or entry.file_size == 0:
            return ""

        chain = self.fat.FollowChain(entry.first_cluster)
        data = bytearray(entry.file_size)
        offset = 0

        for cluster in chain:
            cluster_data = self.disk.ReadCluster(cluster)
            n = min(len(cluster_data), entry.file_size - offset)
            data[offset : offset + n] = cluster_data[:n]
            offset += n
            if offset >= entry.file_size:
                break

        return Converter.BytesToString(data)

    def delete_file(self, parent_cluster: int, file_name: str):
        entry = self.dir.FindDirectoryEntry(parent_cluster, file_name)
        if entry is None:
            raise FileNotFoundError(f"File '{file_name}' not found.")

        if entry.file_size == 0 and entry.first_cluster != -1:
            raise IsADirectoryError(f"Use remove_directory to delete '{file_name}'.")

        if entry.first_cluster > 0:
            self.fat.FreeChain(entry.first_cluster)

        self.dir.RemoveDirectoryEntry(parent_cluster, file_name)

    def rename_entry(self, parent_cluster: int, old_name: str, new_name: str):
        entry = self.dir.FindDirectoryEntry(parent_cluster, old_name)
        if entry is None:
            raise FileNotFoundError(f"Entry '{old_name}' not found.")

        if self.dir.FindDirectoryEntry(parent_cluster, new_name):
            raise FileExistsError(f"Entry '{new_name}' already exists.")

        self.dir.RemoveDirectoryEntry(parent_cluster, old_name)
        entry.name = new_name
        self.dir.AddDirectoryEntry(parent_cluster, entry)

    # ---------------- File Copy / Move ---------------- #

    def copy_file(self, parent_cluster: int, src_name: str, dest_parent_cluster: int, dest_name: str):
        content = self.read_file(parent_cluster, src_name)
        self.create_file(dest_parent_cluster, dest_name)
        self.write_file(dest_parent_cluster, dest_name, content)

    def move_file(self, parent_cluster: int, src_name: str, dest_parent_cluster: int, dest_name: str):
        self.copy_file(parent_cluster, src_name, dest_parent_cluster, dest_name)
        self.delete_file(parent_cluster, src_name)

    # ---------------- Directory Operations ---------------- #

    def create_directory(self, parent_cluster: int, dir_name: str):
        if self.dir.FindDirectoryEntry(parent_cluster, dir_name):
            raise FileExistsError(f"Directory '{dir_name}' already exists.")

        start_cluster = self.fat.AllocateChain(1)
        self.disk.WriteCluster(start_cluster, bytes(FsConstants.CLUSTER_SIZE))

        entry = DirectoryEntry(name=dir_name, attr=0, first_cluster=start_cluster, file_size=0)
        self.dir.AddDirectoryEntry(parent_cluster, entry)

    def remove_directory(self, parent_cluster: int, dir_name: str):
        entry = self.dir.FindDirectoryEntry(parent_cluster, dir_name)
        if entry is None:
            raise FileNotFoundError(f"Directory '{dir_name}' not found.")

        if entry.file_size != 0 or entry.first_cluster == -1:
            raise NotADirectoryError(f"'{dir_name}' is not a directory.")

        if self.dir.ReadDirectory(entry.first_cluster):
            raise OSError(f"Directory '{dir_name}' is not empty.")

        if entry.first_cluster > 0:
            self.fat.FreeChain(entry.first_cluster)

        self.dir.RemoveDirectoryEntry(parent_cluster, dir_name)
