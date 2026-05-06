import struct
from fs_constants import FsConstants
from fat_table_manager import FatTableManager


class DirectoryEntry:
    def __init__(self, name, attr, first_cluster, file_size):
        self.name = name
        self.attr = attr
        self.first_cluster = first_cluster
        self.file_size = file_size


class DirectoryManager:

    ENTRY_SIZE = 32

    def __init__(self, vd, fat_manager: FatTableManager):
        self.vd = vd
        self.fat = fat_manager

    # ---------------- Name Helpers ---------------- #

    def FormatNameTo8Dot3(self, name):
        original = name
        name = name.upper()
        parts = name.split(".")

        truncated = False
        fname = parts[0][:8]
        if len(parts[0]) > 8:
            truncated = True

        ext = ""
        if len(parts) > 1:
            ext = parts[1][:3]
            if len(parts[1]) > 3:
                truncated = True

        if truncated:
            print(f"Warning: File name '{original}' is too long. " f"It was saved as '{fname}.{ext}'")

        return (fname.ljust(8) + ext.ljust(3)).encode()

    def Parse8Dot3Name(self, raw):
        raw = raw.decode().rstrip("\x00")
        return raw[:8].strip() + ("." + raw[8:].strip() if raw[8:].strip() else "")

    # ---------------- Directory Read ---------------- #

    def ReadDirectory(self, start_cluster):
        entries = []
        chain = self.fat.FollowChain(start_cluster)

        for cluster in chain:
            data = self.vd.ReadCluster(cluster)
            for i in range(0, FsConstants.CLUSTER_SIZE, self.ENTRY_SIZE):
                chunk = data[i : i + self.ENTRY_SIZE]
                if chunk[0] == 0x00:
                    continue

                name = self.Parse8Dot3Name(chunk[0:11])
                attr = chunk[11]
                first_cluster = struct.unpack("<i", chunk[12:16])[0]
                file_size = struct.unpack("<i", chunk[16:20])[0]

                entries.append(DirectoryEntry(name, attr, first_cluster, file_size))

        return entries

    def FindDirectoryEntry(self, start_cluster, name):
        name = name.upper()
        for entry in self.ReadDirectory(start_cluster):
            if entry.name.upper() == name:
                return entry
        return None

    # ---------------- Add / Update ---------------- #

    def AddDirectoryEntry(self, start_cluster, entry: DirectoryEntry):
        raw = bytearray(self.ENTRY_SIZE)

        name = entry.name
        parts = name.split(".")

        if len(parts[0]) > 8 or (len(parts) > 1 and len(parts[1]) > 3):
            print(f"Warning: File name '{name}' is too long. " f"It will be truncated to 8.3 format.")

        formatted_name_bytes = self.FormatNameTo8Dot3(name)
        raw[0:11] = formatted_name_bytes
        raw[11] = entry.attr
        raw[12:16] = struct.pack("<i", entry.first_cluster)
        raw[16:20] = struct.pack("<i", entry.file_size)

        formatted_name = self.Parse8Dot3Name(formatted_name_bytes)

        chain = self.fat.FollowChain(start_cluster)

        for cluster in chain:
            data = bytearray(self.vd.ReadCluster(cluster))

            for i in range(0, FsConstants.CLUSTER_SIZE, self.ENTRY_SIZE):

                if data[i] == 0x00:
                    data[i : i + self.ENTRY_SIZE] = raw
                    self.vd.WriteCluster(cluster, data)
                    return

                existing = self.Parse8Dot3Name(data[i : i + 11])

                if existing.upper() == formatted_name.upper():
                    data[i : i + self.ENTRY_SIZE] = raw
                    self.vd.WriteCluster(cluster, data)
                    return

        new_cluster = self.fat.AllocateChain(1)
        empty = bytearray(FsConstants.CLUSTER_SIZE)
        empty[0 : self.ENTRY_SIZE] = raw
        self.vd.WriteCluster(new_cluster, empty)


    def RemoveDirectoryEntry(self, start_cluster, name):
        chain = self.fat.FollowChain(start_cluster)

        for cluster in chain:
            data = bytearray(self.vd.ReadCluster(cluster))
            for i in range(0, FsConstants.CLUSTER_SIZE, self.ENTRY_SIZE):
                if data[i] == 0x00:
                    continue

                existing = self.Parse8Dot3Name(data[i : i + 11])
                if existing.upper() == name.upper():
                    data[i : i + self.ENTRY_SIZE] = bytes(self.ENTRY_SIZE)
                    self.vd.WriteCluster(cluster, data)
                    return True

        return False
