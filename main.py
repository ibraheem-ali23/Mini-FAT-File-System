import os
from virtual_disk import VirtualDisk
from superblock_manager import SuperblockManager
from fat_table_manager import FatTableManager
from directory_manager import DirectoryManager
from FileSystem import FileSystem
from fs_constants import FsConstants

def hex_dump(file_path):
    
    print(f"\n--- Hex Dump of {file_path} (First 256 bytes) ---")
    with open(file_path, "rb") as f:
        data = f.read(256)
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            print(f"{i:08x}  {hex_part}")
    print("--------------------------------------------------\n")

def run_test_scenario():
    print("=== Starting OS File System Test ===\n")

    # 1. Initialize Virtual Disk
    print("[1] Initializing Virtual Disk...")
    vd = VirtualDisk() 
    vd.Initialize("minifat.bin") 

    # 2. Initialize Managers
    print("[2] Initializing Managers (Superblock, FAT, Directory)...")
    sm = SuperblockManager(vd, is_new=True) 
    fat = FatTableManager(vd)
    dir_manager = DirectoryManager(vd, fat)

    # 3. Initialize File System
    fs = FileSystem(vd, fat, dir_manager)

    # 4. Format System 
    print("[3] Formatting the System...")
    fs.format_system()

    # 5. Create Directory 
    print("\n[4] Creating a Directory named 'MYDIR'...")
    fs.create_directory(FsConstants.ROOT_DIR_FIRST_CLUSTER, "MYDIR")

    # 6. Create File 
    print("[5] Creating a File named 'TEST.TXT'...")
    fs.create_file(FsConstants.ROOT_DIR_FIRST_CLUSTER, "TEST.TXT")

    # 7. Write to File
    print("[6] Writing data to 'TEST.TXT'...")
    fs.write_file(FsConstants.ROOT_DIR_FIRST_CLUSTER, "TEST.TXT", "Hello World!")

    # 8. List Directory
    print("\n[7] Listing files in ROOT Directory:")
    print("-" * 50)
    entries = dir_manager.ReadDirectory(FsConstants.ROOT_DIR_FIRST_CLUSTER)
    for entry in entries:
        name = entry.name.strip()
        if entry.file_size == 0 and entry.first_cluster != -1:
            print(f"📁 [Folder] {name} | Starts at Cluster: {entry.first_cluster}")
        elif entry.file_size > 0 or entry.first_cluster == -1:
            print(f"📄 [File]   {name} | Starts at Cluster: {entry.first_cluster} | Size: {entry.file_size} Bytes")
    print("-" * 50)

    # 9. Read File
    print("\n[8] Reading 'TEST.TXT' content:")
    content = fs.read_file(FsConstants.ROOT_DIR_FIRST_CLUSTER, "TEST.TXT")
    print(f"Content -> {content}")

    # 10. Advanced Operations Test
    print("\n=== Advanced Operations Test ===")
    fs.copy_file(FsConstants.ROOT_DIR_FIRST_CLUSTER, "TEST.TXT", FsConstants.ROOT_DIR_FIRST_CLUSTER, "COPY.TXT")
    fs.rename_entry(FsConstants.ROOT_DIR_FIRST_CLUSTER, "COPY.TXT", "NEW.TXT")
    print("Done: Copy and Rename executed successfully.")

    
    hex_dump("minifat.bin")

    print("\n=== Test Completed Successfully ===")
    vd.CloseDisk()

if __name__ == "__main__":
    run_test_scenario()