import struct
from fs_constants import FsConstants

class FatTableManager:

    def __init__(self, virtual_disk):
        self.vd = virtual_disk

        # FAT table in memory
        self.fat = [0] * FsConstants.CLUSTER_COUNT

        # Reserved clusters (superblock + FAT itself + root)
        self.reserved_clusters = set(range(0, FsConstants.FAT_END_CLUSTER + 1))
        self.reserved_clusters.add(FsConstants.ROOT_DIR_FIRST_CLUSTER)

    def GetFatEntry(self, index):
        return self.fat[index]

    def SetFatEntry(self, index, value):
        self.fat[index] = value

    def ReadAllFat(self):
        return self.fat.copy()

    def WriteAllFat(self, entries):
        if len(entries) != FsConstants.CLUSTER_COUNT:
            raise ValueError("Invalid FAT array size")
        self.fat = entries.copy()
        self.FlushFatToDisk()

    # -------------------------------------------------
    # LOAD / SAVE FAT
    # -------------------------------------------------
    def LoadFatFromDisk(self):
        fat_entries = []

        for cluster in range(FsConstants.FAT_START_CLUSTER, FsConstants.FAT_END_CLUSTER + 1):
            data = self.vd.ReadCluster(cluster)

            for i in range(0, FsConstants.CLUSTER_SIZE, 4):
                entry = struct.unpack("<i", data[i : i + 4])[0]
                fat_entries.append(entry)

        self.fat = fat_entries[: FsConstants.CLUSTER_COUNT]

    def FlushFatToDisk(self):
        entries_per_cluster = FsConstants.CLUSTER_SIZE // 4

        for i, cluster in enumerate(range(FsConstants.FAT_START_CLUSTER, FsConstants.FAT_END_CLUSTER + 1)):
            start = i * entries_per_cluster
            end = start + entries_per_cluster
            chunk = self.fat[start:end]

            data = b"".join(struct.pack("<i", e) for e in chunk)
            self.vd.WriteCluster(cluster, data)

    # -------------------------------------------------
    # FAT CHAIN OPERATIONS
    # -------------------------------------------------
    def FollowChain(self, start_cluster):
        if start_cluster < 0 or start_cluster >= FsConstants.CLUSTER_COUNT:
            raise ValueError("Invalid start cluster")

        chain = []
        current = start_cluster
        visited = set()

        while current != -1:
            if current in visited:
                raise RuntimeError("Cycle detected in FAT")

            visited.add(current)
            chain.append(current)
            current = self.fat[current]

        return chain

    def AllocateChain(self, required_clusters):
        free_clusters = [i for i in range(FsConstants.CONTENT_START_CLUSTER, FsConstants.CLUSTER_COUNT) if self.fat[i] == 0]

        if len(free_clusters) < required_clusters:
            raise RuntimeError("Not enough free clusters")

        allocated = free_clusters[:required_clusters]

        for i in range(required_clusters - 1):
            self.fat[allocated[i]] = allocated[i + 1]

        self.fat[allocated[-1]] = -1

        self.FlushFatToDisk()

        return allocated[0]

    def FreeChain(self, start_cluster):
        for cluster in self.FollowChain(start_cluster):
            if cluster in self.reserved_clusters:
                continue
            self.fat[cluster] = 0

        self.FlushFatToDisk()