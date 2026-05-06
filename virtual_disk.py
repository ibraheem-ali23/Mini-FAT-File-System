import os
from fs_constants import FsConstants


class VirtualDisk:

    CLUSTER_SIZE = FsConstants.CLUSTER_SIZE
    CLUSTERS_NUMBER = FsConstants.CLUSTER_COUNT

    def __init__(self):
        self.disk_path = None
        self.disk_file = None
        self.is_open = False
        self.disk_size = 0

    def Initialize(self, path, createIfMissing=True):

        if self.is_open:
            raise RuntimeError("Disk is already initialized")

        self.disk_path = path
        self.disk_size = self.CLUSTERS_NUMBER * self.CLUSTER_SIZE

        try:
            if not os.path.exists(self.disk_path):
                if createIfMissing:
                    print("Creating new virtual disk...")
                    self._create_empty_disk(self.disk_path)
                else:
                    raise FileNotFoundError("Disk file not found and creation disabled")

            self.disk_file = open(self.disk_path, "r+b")
            self.is_open = True

        except Exception as ex:
            self.is_open = False
            raise IOError(f"Failed to initialize disk: {ex}") from ex

    def _create_empty_disk(self, path):

        try:
            with open(path, "wb") as f:
                zero_cluster = bytes(self.CLUSTER_SIZE)
                for _ in range(self.CLUSTERS_NUMBER):
                    f.write(zero_cluster)
                f.flush()
                os.fsync(f.fileno())

        except Exception as ex:
            raise IOError(f"Failed to create disk file '{path}': {ex}") from ex

    def ReadCluster(self, clusterNumber):

        if not self.is_open or self.disk_file is None:
            raise IOError("Disk is not initialized or open")

        if not isinstance(clusterNumber, int):
            raise ValueError("Cluster number must be an integer")
        if clusterNumber < 0 or clusterNumber >= self.CLUSTERS_NUMBER:
            raise ValueError("Cluster number out of range")

        offset = clusterNumber * self.CLUSTER_SIZE

        try:
            self.disk_file.seek(offset)
            data = self.disk_file.read(self.CLUSTER_SIZE)
            if not data or len(data) != self.CLUSTER_SIZE:
                raise IOError(f"Short read: expected {self.CLUSTER_SIZE} bytes, got {len(data) if data else 0} bytes")
            return data

        except Exception as ex:
            raise IOError(f"Failed to read cluster {clusterNumber}: {ex}") from ex

    def WriteCluster(self, clusterNumber, data):

        if not self.is_open or self.disk_file is None:
            raise IOError("Disk is not initialized or open")

        if not isinstance(clusterNumber, int):
            raise ValueError("Cluster number must be an integer")
        if clusterNumber < 0 or clusterNumber >= self.CLUSTERS_NUMBER:
            raise ValueError("Cluster number out of range")

        if not isinstance(data, (bytes, bytearray)):
            raise ValueError("Data must be bytes or bytearray")
        if len(data) != self.CLUSTER_SIZE:
            raise ValueError(f"Data must be exactly {self.CLUSTER_SIZE} bytes")

        offset = clusterNumber * self.CLUSTER_SIZE

        try:
            self.disk_file.seek(offset)
            written = self.disk_file.write(data)
            if written != self.CLUSTER_SIZE:
                raise IOError(f"Short write: expected {self.CLUSTER_SIZE} bytes, wrote {written} bytes")
            self.disk_file.flush()
            os.fsync(self.disk_file.fileno())

        except Exception as ex:
            raise IOError(f"Failed to write cluster {clusterNumber}: {ex}") from ex

    def GetDiskSize(self):

        return self.disk_size

    def CloseDisk(self):

        if self.disk_file is not None:
            try:
                self.disk_file.flush()
                os.fsync(self.disk_file.fileno())
            except Exception:
                pass
            finally:
                try:
                    self.disk_file.close()
                except Exception:
                    pass
                self.disk_file = None
        self.is_open = False
