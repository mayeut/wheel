"""
This module contains function to analyse dynamic library
headers to extract system information

Currently only for MacOSX

Library file on macosx system starts with Mach-O or Fat field.
This can be distinguish by first 32 bites and it is called magic number.
Proper value of magic number is with suffix _MAGIC. Suffix _CIGAM means
reversed bytes order.
Both fields can occur in two types: 32 and 64 bytes.

FAT field inform that this library contains few version of library
(typically for different types version). It contains
information where Mach-O headers starts.

Each section started with Mach-O header contains one library
(So if file starts with this field it contains only one version).

After filed Mach-O there are section fields.
Each of them starts with two fields:
cmd - magic number for this command
cmdsize - total size occupied by this section information.

In this case only sections LC_VERSION_MIN_MACOSX (for macosx 10.13 and earlier)
and LC_BUILD_VERSION (for macosx 10.14 and newer) are interesting,
because them contains information about minimal system version.

Important remarks:
- For fat files this implementation looks for maximum number version.
  It not check if it is 32 or 64 and do not compare it with currently builded package.
  So it is possible to false report higher version that needed.
- All structures signatures are taken form macosx header files.
- I think that binary format will be more stable than `otool` output.
  and if apple introduce some changes both implementation will need to be updated.
"""

import ctypes
import sys

"""here the needed const and struct from mach-o header files"""

FAT_MAGIC = 0xcafebabe
FAT_CIGAM = 0xbebafeca
FAT_MAGIC_64 = 0xcafebabf
FAT_CIGAM_64 = 0xbfbafeca
MH_MAGIC = 0xfeedface
MH_CIGAM = 0xcefaedfe
MH_MAGIC_64 = 0xfeedfacf
MH_CIGAM_64 = 0xcffaedfe

LC_VERSION_MIN_MACOSX = 0x24
LC_BUILD_VERSION = 0x32


mach_header_fields = _fields_ = [
        ("magic", ctypes.c_uint32), ("cputype", ctypes.c_int),
        ("cpusubtype", ctypes.c_int), ("filetype", ctypes.c_uint32),
        ("ncmds", ctypes.c_uint32), ("sizeofcmds", ctypes.c_uint32),
        ("flags", ctypes.c_uint32)
    ]
"""
struct mach_header {
    uint32_t	magic;		/* mach magic number identifier */
    cpu_type_t	cputype;	/* cpu specifier */
    cpu_subtype_t	cpusubtype;	/* machine specifier */
    uint32_t	filetype;	/* type of file */
    uint32_t	ncmds;		/* number of load commands */
    uint32_t	sizeofcmds;	/* the size of all the load commands */
    uint32_t	flags;		/* flags */
};
typedef integer_t cpu_type_t;
typedef integer_t cpu_subtype_t;
"""

mach_header_fields_64 = mach_header_fields + [("reserved", ctypes.c_uint32)]
"""
struct mach_header_64 {
    uint32_t	magic;		/* mach magic number identifier */
    cpu_type_t	cputype;	/* cpu specifier */
    cpu_subtype_t	cpusubtype;	/* machine specifier */
    uint32_t	filetype;	/* type of file */
    uint32_t	ncmds;		/* number of load commands */
    uint32_t	sizeofcmds;	/* the size of all the load commands */
    uint32_t	flags;		/* flags */
    uint32_t	reserved;	/* reserved */
};
"""

fat_header_fields = [("magic", ctypes.c_uint32), ("nfat_arch", ctypes.c_uint32)]
"""
struct fat_header {
    uint32_t	magic;		/* FAT_MAGIC or FAT_MAGIC_64 */
    uint32_t	nfat_arch;	/* number of structs that follow */
};
"""

fat_arch_fields = [
    ("cputype", ctypes.c_int), ("cpusubtype", ctypes.c_int),
    ("offset", ctypes.c_uint32), ("size", ctypes.c_uint32),
    ("align", ctypes.c_uint32)
]
"""
struct fat_arch {
    cpu_type_t	cputype;	/* cpu specifier (int) */
    cpu_subtype_t	cpusubtype;	/* machine specifier (int) */
    uint32_t	offset;		/* file offset to this object file */
    uint32_t	size;		/* size of this object file */
    uint32_t	align;		/* alignment as a power of 2 */
};
"""

fat_arch_64_fields = [
    ("cputype", ctypes.c_int), ("cpusubtype", ctypes.c_int),
    ("offset", ctypes.c_uint64), ("size", ctypes.c_uint64),
    ("align", ctypes.c_uint32), ("reserved", ctypes.c_uint32)
]
"""
struct fat_arch_64 {
    cpu_type_t	cputype;	/* cpu specifier (int) */
    cpu_subtype_t	cpusubtype;	/* machine specifier (int) */
    uint64_t	offset;		/* file offset to this object file */
    uint64_t	size;		/* size of this object file */
    uint32_t	align;		/* alignment as a power of 2 */
    uint32_t	reserved;	/* reserved */
};
"""

segment_base_fields = [("cmd", ctypes.c_uint32), ("cmdsize", ctypes.c_uint32)]
"""base for reading segment info"""

segment_command_fields = [
    ("cmd", ctypes.c_uint32), ("cmdsize", ctypes.c_uint32),
    ("segname", ctypes.c_char * 16), ("vmaddr", ctypes.c_uint32),
    ("vmsize", ctypes.c_uint32), ("fileoff", ctypes.c_uint32),
    ("filesize", ctypes.c_uint32), ("maxprot", ctypes.c_int),
    ("initprot", ctypes.c_int), ("nsects", ctypes.c_uint32),
    ("flags", ctypes.c_uint32),
    ]
"""
struct segment_command { /* for 32-bit architectures */
    uint32_t	cmd;		/* LC_SEGMENT */
    uint32_t	cmdsize;	/* includes sizeof section structs */
    char		segname[16];	/* segment name */
    uint32_t	vmaddr;		/* memory address of this segment */
    uint32_t	vmsize;		/* memory size of this segment */
    uint32_t	fileoff;	/* file offset of this segment */
    uint32_t	filesize;	/* amount to map from the file */
    vm_prot_t	maxprot;	/* maximum VM protection */
    vm_prot_t	initprot;	/* initial VM protection */
    uint32_t	nsects;		/* number of sections in segment */
    uint32_t	flags;		/* flags */
};
typedef int vm_prot_t;
"""

segment_command_fields_64 = [
    ("cmd", ctypes.c_uint32), ("cmdsize", ctypes.c_uint32),
    ("segname", ctypes.c_char * 16), ("vmaddr", ctypes.c_uint64),
    ("vmsize", ctypes.c_uint64), ("fileoff", ctypes.c_uint64),
    ("filesize", ctypes.c_uint64), ("maxprot", ctypes.c_int),
    ("initprot", ctypes.c_int), ("nsects", ctypes.c_uint32),
    ("flags", ctypes.c_uint32),
    ]
"""
struct segment_command_64 { /* for 64-bit architectures */
    uint32_t	cmd;		/* LC_SEGMENT_64 */
    uint32_t	cmdsize;	/* includes sizeof section_64 structs */
    char		segname[16];	/* segment name */
    uint64_t	vmaddr;		/* memory address of this segment */
    uint64_t	vmsize;		/* memory size of this segment */
    uint64_t	fileoff;	/* file offset of this segment */
    uint64_t	filesize;	/* amount to map from the file */
    vm_prot_t	maxprot;	/* maximum VM protection */
    vm_prot_t	initprot;	/* initial VM protection */
    uint32_t	nsects;		/* number of sections in segment */
    uint32_t	flags;		/* flags */
};
"""

version_min_command_fields = segment_base_fields + \
    [("version", ctypes.c_uint32), ("sdk", ctypes.c_uint32)]
"""
struct version_min_command {
    uint32_t	cmd;		/* LC_VERSION_MIN_MACOSX or
                               LC_VERSION_MIN_IPHONEOS or
                               LC_VERSION_MIN_WATCHOS or
                               LC_VERSION_MIN_TVOS */
    uint32_t	cmdsize;	/* sizeof(struct min_version_command) */
    uint32_t	version;	/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
    uint32_t	sdk;		/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
};
"""

build_version_command_fields = segment_base_fields + \
    [("platform", ctypes.c_uint32), ("minos", ctypes.c_uint32),
     ("sdk", ctypes.c_uint32), ("ntools", ctypes.c_uint32)]
"""
struct build_version_command {
    uint32_t	cmd;		/* LC_BUILD_VERSION */
    uint32_t	cmdsize;	/* sizeof(struct build_version_command) plus */
                                /* ntools * sizeof(struct build_tool_version) */
    uint32_t	platform;	/* platform */
    uint32_t	minos;		/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
    uint32_t	sdk;		/* X.Y.Z is encoded in nibbles xxxx.yy.zz */
    uint32_t	ntools;		/* number of tool entries following this */
};
"""


def swap32(x):
    return (((x << 24) & 0xFF000000) |
            ((x << 8) & 0x00FF0000) |
            ((x >> 8) & 0x0000FF00) |
            ((x >> 24) & 0x000000FF))


def get_base_class_and_magic_number(lib_file, seek=None):
    if seek is None:
        seek = lib_file.tell()
    else:
        lib_file.seek(seek)
    magic_number = ctypes.c_uint32.from_buffer_copy(
        lib_file.read(ctypes.sizeof(ctypes.c_uint32))).value

    # Handle wrong byte order
    if magic_number in [FAT_CIGAM, FAT_CIGAM_64, MH_CIGAM, MH_CIGAM_64]:
        if sys.byteorder == "little":
            BaseClass = ctypes.BigEndianStructure
        else:
            BaseClass = ctypes.LittleEndianStructure

        magic_number = swap32(magic_number)
    else:
        BaseClass = ctypes.Structure

    lib_file.seek(seek)
    return BaseClass, magic_number


def read_data(struct_class, lib_file):
    return struct_class.from_buffer_copy(lib_file.read(
                        ctypes.sizeof(struct_class)))


def extract_macosx_min_system_version(path_to_lib):
    with open(path_to_lib, "rb") as lib_file:
        BaseClass, magic_number = get_base_class_and_magic_number(lib_file, 0)
        if magic_number not in [FAT_MAGIC, FAT_MAGIC_64, MH_MAGIC, MH_MAGIC_64]:
            return

        if magic_number in [FAT_MAGIC, FAT_CIGAM_64]:
            class FatHeader(BaseClass):
                _fields_ = fat_header_fields

            fat_header = read_data(FatHeader, lib_file)
            if magic_number == FAT_MAGIC:

                class FatArch(BaseClass):
                    _fields_ = fat_arch_fields
            else:

                class FatArch(BaseClass):
                    _fields_ = fat_arch_64_fields

            fat_arch_list = [read_data(FatArch, lib_file) for _ in range(fat_header.nfat_arch)]

            class SegmentBase(BaseClass):
                _fields_ = segment_base_fields

            versions_list = []
            for el in fat_arch_list:
                try:
                    version = read_mach_header(lib_file, el.offset)
                    if version is not None:
                        versions_list.append(version)
                except ValueError:
                    pass

            if len(versions_list) > 0:
                return max(versions_list)
            else:
                return None

        else:
            try:
                return read_mach_header(lib_file, 0)
            except ValueError:
                """when some error during read library files"""
                return None


def read_mach_header(lib_file, seek=None):
    """
    This funcition parse mach-O header and extract
    information about minimal system version

    :param lib_file: reference to opened library file with pointer
    """
    if seek is not None:
        lib_file.seek(seek)
    base_class, magic_number = get_base_class_and_magic_number(lib_file)
    arch = "32" if magic_number == MH_MAGIC else "64"

    class SegmentBase(base_class):
        _fields_ = segment_base_fields
    if arch == "32":

        class MachHeader(base_class):
            _fields_ = mach_header_fields

        class SegmentCommand(base_class):
            _fields_ = segment_command_fields

    else:

        class MachHeader(base_class):
            _fields_ = mach_header_fields_64

        class SegmentCommand(base_class):
            _fields_ = segment_command_fields_64

    mach_header = read_data(MachHeader, lib_file)
    for _i in range(mach_header.ncmds):
        pos = lib_file.tell()
        segment_base = read_data(SegmentBase, lib_file)
        lib_file.seek(pos)
        if segment_base.cmd == LC_VERSION_MIN_MACOSX:
            class VersionMinCommand(base_class):
                _fields_ = version_min_command_fields

            version_info = read_data(VersionMinCommand, lib_file)
            return parse_version(version_info.version)
        elif segment_base.cmd == LC_BUILD_VERSION:
            class VersionBuild(base_class):
                _fields_ = build_version_command_fields

            version_info = read_data(VersionBuild, lib_file)
            return parse_version(version_info.minos)
        else:
            lib_file.seek(pos + segment_base.cmdsize)
            continue


def parse_version(version):
    zz = version & 2**9-1
    version >>= 8
    yy = version & 2**9-1
    version >>= 8
    return version, yy, zz