# Mini-FAT File System

A lightweight, modular implementation of a File System based on the FAT (File Allocation Table) architecture, developed as a core Operating Systems project.

## Project Overview
This project simulates a functional file system structure on a virtual disk. It manages file allocation, directory structures, and data persistence through a custom-built API.

## Key Features
* **Virtual Disk Management:** Handles raw binary read/write operations on a virtual disk file.
* **FAT Architecture:** Implements a File Allocation Table to track cluster chains and free space.
* **Directory Management:** Supports hierarchical file and directory creation, listing, and metadata tracking.
* **Persistent Storage:** Data is persisted to a binary file, maintaining state across executions.
* **Robust Error Handling:** Includes cycle detection and disk integrity checks.

## Architecture


## Technologies Used
* **Language:** Python
* **Concepts:** Operating Systems, Data Structures, Binary File I/O
* **Tools:** Git, VS Code

## Project Structure
* `FileSystem.py`: The orchestrator managing system-wide operations.
* `fat_table_manager.py`: Handles allocation logic and FAT chain management.
* `directory_manager.py`: Manages directory entries and file metadata.
* `virtual_disk.py`: Low-level interface for binary disk interaction.
* `main.py`: Test suite and project entry point.

## Usage
1. Ensure Python is installed.
2. Clone the repository.
3. Run the test scenario:
   ```bash
   python main.py


## Disk Layout

**Total size: 1 MB** (1024 clusters × 1024 bytes)

| Region | Clusters | Purpose |
|--------|----------|---------|
| Superblock | 0 | File system metadata |
| FAT Table | 1 – 4 | Cluster chain map |
| Root Directory | 5 | Top-level directory entries |
| Data | 6 – 1023 | File and subdirectory content |

Each FAT entry is a 4-byte signed integer: `0` = free, `-1` = end of chain, `N` = next cluster.  
Each directory entry is 32 bytes and uses the classic 8.3 filename format.

---



## Key Design Decisions

- **Immediate persistence** — every write is flushed with `os.fsync`. No write buffering; the disk is always consistent.
- **Dynamic directories** — a directory cluster chain grows automatically when its entries exceed capacity.
- **8.3 filenames** — names are uppercased and truncated to `FILENAME.EXT` format on write, with a warning printed if truncation occurs.
- **Chain integrity** — `FollowChain` detects cycles at runtime and raises a `RuntimeError` on corruption.

---

## Configuration

```python
# fs_constants.py
CLUSTER_SIZE  = 1024   # bytes per cluster
CLUSTER_COUNT = 1024   # number of clusters  →  1 MB disk

SUPERBLOCK_CLUSTER     = 0
FAT_START_CLUSTER      = 1
FAT_END_CLUSTER        = 4
ROOT_DIR_FIRST_CLUSTER = 5
CONTENT_START_CLUSTER  = 6
```

To scale the disk, increase `CLUSTER_COUNT` and extend `FAT_END_CLUSTER` so the FAT region fits `CLUSTER_COUNT × 4` bytes.

---
