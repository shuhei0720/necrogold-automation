"""TEST047 packed C orientation contracts; device throughput is measured later."""
import ctypes as C
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'


def reference(raw, width, height, orientation):
    """Compose row reversal and transpose, independent of C's coordinate maps."""
    pixels = [tuple(raw[i:i+3])+(255,) for i in range(0, len(raw), 4)]
    rows = [pixels[y*width:(y+1)*width] for y in range(height)]
    transposed = list(map(list, zip(*rows)))
    variants = [rows, [row[::-1] for row in rows], [row[::-1] for row in rows[::-1]],
                rows[::-1], transposed, [row[::-1] for row in transposed],
                [row[::-1] for row in transposed[::-1]], transposed[::-1]]
    return bytes(channel for row in variants[orientation-1] for pixel in row for channel in pixel)


class NativeRasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='ngg2-raster-c-')
        for attribute, optimization in (('native', '-O2'), ('unoptimized', '-O0')):
            library = Path(cls.directory.name) / (attribute+'.so')
            subprocess.run(['cc', '-std=c99', optimization, '-Wall', '-Wextra', '-Werror', '-pedantic',
                            '-fPIC', '-shared', str(CORE/'NG2Perception.c'), '-lm', '-o', str(library)],
                           check=True)
            native = C.CDLL(str(library))
            native.ng2_orient_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_int32, C.c_int32,
                                             C.c_int32, C.c_void_p, C.c_size_t]
            native.ng2_orient_rgba.restype = C.c_size_t
            setattr(cls, attribute, native)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_portrait_orientation8_copies_expected_pixels(self):
        original = bytes(value for red in range(1, 7) for value in (red*20, red, 255-red, red*31))
        source = (C.c_uint8*len(original)).from_buffer_copy(original)
        output = (C.c_uint8*len(original))()
        copied = self.native.ng2_orient_rgba(source, len(original), 3, 2, 8, output, len(output))
        self.assertEqual(copied, 6)
        expected = bytes(value for red in (3, 6, 2, 5, 1, 4) for value in (red*20, red, 255-red, 255))
        self.assertEqual(bytes(output), expected)
        self.assertEqual(bytes(source), original)

    def check_guarded(self, raw, width, height, orientation, native=None):
        native = self.native if native is None else native
        source = (C.c_uint8*(len(raw)+2)).from_buffer_copy(b'\xd3'+raw+b'\xe7')
        destination = (C.c_uint8*(len(raw)+2))(*([0xa5]*(len(raw)+2)))
        copied = native.ng2_orient_rgba(C.byref(source, 1), len(raw), width, height, orientation,
                                       C.byref(destination, 1), len(raw))
        self.assertEqual(copied, width*height)
        self.assertEqual(C.string_at(C.byref(destination, 1), len(raw)), reference(raw,width,height,orientation))
        self.assertEqual((destination[0], destination[-1]), (0xa5,0xa5))
        self.assertEqual(bytes(source), b'\xd3'+raw+b'\xe7')

    def test_all_eight_asymmetric_independent_sentinels(self):
        raw = bytes(value for red in range(1,7) for value in (red, red+20, red+40, red*31))
        expected = [(1,2,3,4,5,6), (3,2,1,6,5,4), (6,5,4,3,2,1), (4,5,6,1,2,3),
                    (1,4,2,5,3,6), (4,1,5,2,6,3), (6,3,5,2,4,1), (3,6,2,5,1,4)]
        for orientation, reds in enumerate(expected, 1):
            with self.subTest(orientation=orientation):
                self.assertEqual(reference(raw,3,2,orientation)[::4], bytes(reds))
                self.check_guarded(raw,3,2,orientation)

    def test_nonsquare_degenerate_and_dimension_boundary_canaries(self):
        for width,height in ((1,1),(1,7),(7,1),(2,3),(3,2),(9,17),(17,9),(1,4096),(4096,1)):
            raw = bytes((i*37+11)%256 for i in range(width*height*4))
            for orientation in range(1,9):
                with self.subTest(width=width,height=height,orientation=orientation):
                    self.check_guarded(raw,width,height,orientation)

    def test_unoptimized_c_preserves_all_maps(self):
        raw = bytes((i*29+91)%256 for i in range(17*9*4))
        for orientation in range(1,9):
            with self.subTest(orientation=orientation):
                self.check_guarded(raw,17,9,orientation,self.unoptimized)

    def assert_rejected(self, width=3, height=2, orientation=8,
                        source_length=24, destination_length=24, null_source=False,
                        null_destination=False, overflow_source=False, overflow_destination=False):
        source = (C.c_uint8*64)(*range(64))
        destination = (C.c_uint8*64)(*([0xa5]*64))
        first, second = C.byref(source,8), C.byref(destination,8)
        if null_source: first = None
        if null_destination: second = None
        maximum = 2**(C.sizeof(C.c_void_p)*8)-1
        if overflow_source: first = C.c_void_p(maximum-11)
        if overflow_destination: second = C.c_void_p(maximum-11)
        before_source, before_destination = bytes(source), bytes(destination)
        self.assertEqual(self.native.ng2_orient_rgba(first,source_length,width,height,orientation,
                                                   second,destination_length),0)
        self.assertEqual(bytes(source),before_source)
        self.assertEqual(bytes(destination),before_destination)

    def test_invalid_dimensions_or_orientation_leave_both_buffers_untouched(self):
        dimensions = ((0,2),(-1,2),(3,0),(3,-1),(4097,1),(1,4097),
                      (2**31-1,2),(-2**31,2),(4000,2001),(4096,4096))
        for width,height in dimensions:
            with self.subTest(width=width,height=height):self.assert_rejected(width=width,height=height)
        for orientation in (-2**31,-1,0,9,2**31-1):
            with self.subTest(orientation=orientation):self.assert_rejected(orientation=orientation)

    def test_exact_packed_lengths_required_before_access(self):
        maximum = 2**(C.sizeof(C.c_size_t)*8)-1
        for length in (0,1,23,25,28,2**63,maximum):
            with self.subTest(source_length=length):self.assert_rejected(source_length=length)
            with self.subTest(destination_length=length):self.assert_rejected(destination_length=length)

    def test_null_arguments_leave_other_buffer_untouched(self):
        self.assert_rejected(null_source=True)
        self.assert_rejected(null_destination=True)
        self.assert_rejected(null_source=True,null_destination=True)

    def test_uintptr_range_overflow_rejected_before_access(self):
        self.assert_rejected(overflow_source=True)
        self.assert_rejected(overflow_destination=True)
        self.assert_rejected(overflow_source=True,overflow_destination=True)

    def test_overlap_same_pointer_and_one_byte_edges_reject_without_writes(self):
        for source_offset,destination_offset in ((8,8),(8,9),(9,8),(8,31),(31,8)):
            with self.subTest(source_offset=source_offset,destination_offset=destination_offset):
                buffer = (C.c_uint8*80)(*range(80))
                before = bytes(buffer)
                self.assertEqual(self.native.ng2_orient_rgba(C.byref(buffer,source_offset),24,3,2,8,
                                                           C.byref(buffer,destination_offset),24),0)
                self.assertEqual(bytes(buffer),before)

    def test_adjacent_ranges_are_disjoint_in_both_address_orders(self):
        for source_offset,destination_offset in ((8,32),(32,8)):
            with self.subTest(source_offset=source_offset,destination_offset=destination_offset):
                buffer = (C.c_uint8*64)(*range(64))
                before = bytes(buffer);source = before[source_offset:source_offset+24]
                self.assertEqual(self.native.ng2_orient_rgba(C.byref(buffer,source_offset),24,3,2,8,
                                                           C.byref(buffer,destination_offset),24),6)
                expected = before[:destination_offset]+reference(source,3,2,8)+before[destination_offset+24:]
                self.assertEqual(bytes(buffer),expected)

    def test_eight_million_pixel_limit_is_inclusive(self):
        pixels = 8_000_000;length = pixels*4
        source = (C.c_uint8*(length+2))()
        destination = (C.c_uint8*(length+2))()
        C.memset(source,42,C.sizeof(source));destination[0]=destination[-1]=0xa5
        self.assertEqual(self.native.ng2_orient_rgba(C.byref(source,1),length,4000,2000,8,
                                                   C.byref(destination,1),length),pixels)
        self.assertEqual(C.string_at(C.byref(destination,1),length),bytes((42,42,42,255))*pixels)
        self.assertEqual((destination[0],destination[-1]),(0xa5,0xa5))
        self.assertEqual(C.string_at(source,C.sizeof(source)),b'\x2a'*(length+2))

    def test_address_and_undefined_sanitizers_for_orientation_and_rejection(self):
        harness = r'''#include "NG2Core.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    const size_t pixels=828u*1792u, length=pixels*4u;
    unsigned char *source=(unsigned char*)malloc(length+2), *destination=(unsigned char*)malloc(length+2);
    unsigned char *snapshot=(unsigned char*)malloc(length+2);
    int orientation;
    if(!source||!destination||!snapshot)return 20;
    memset(source,42,length+2);memset(destination,165,length+2);
    for(orientation=1;orientation<=8;++orientation){
        if(ng2_orient_rgba(source+1,length,828,1792,orientation,destination+1,length)!=pixels)return 21;
        if(destination[0]!=165||destination[length+1]!=165||source[0]!=42||source[length+1]!=42)return 22;
        if(destination[1]!=42||destination[4]!=255||destination[length]!=255)return 23;
    }
    memcpy(snapshot,destination,length+2);
    if(ng2_orient_rgba(NULL,length,828,1792,8,destination+1,length))return 24;
    if(ng2_orient_rgba(source+1,length,828,1792,8,NULL,length))return 25;
    if(ng2_orient_rgba(source+1,length-1,828,1792,8,destination+1,length))return 26;
    if(ng2_orient_rgba(source+1,length,828,1792,8,destination+1,length+1))return 27;
    if(ng2_orient_rgba(source+1,length,828,1792,9,destination+1,length))return 28;
    if(ng2_orient_rgba(source+1,length,4096,4096,8,destination+1,length))return 29;
    if(ng2_orient_rgba(source+1,length,828,1792,8,source+2,length))return 30;
    if(ng2_orient_rgba(source+2,length,828,1792,8,source+1,length))return 31;
    if(ng2_orient_rgba((const unsigned char*)(UINTPTR_MAX-7),length,828,1792,8,destination+1,length))return 32;
    if(ng2_orient_rgba(source+1,length,828,1792,8,(unsigned char*)(UINTPTR_MAX-7),length))return 33;
    if(memcmp(snapshot,destination,length+2))return 34;
    for(size_t i=0;i<length+2;++i)if(source[i]!=42)return 35;
    free(snapshot);free(destination);free(source);
    puts("PASS sanitized orientation maps and rejected ranges");return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='ngg2-raster-sanitized-') as directory:
            directory = Path(directory);source=directory/'harness.c';executable=directory/'harness'
            source.write_text(harness)
            subprocess.run(['cc','-std=c99','-O1','-g','-Wall','-Wextra','-Werror','-pedantic',
                            '-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie',
                            '-I',str(CORE),str(source),str(CORE/'NG2Perception.c'),'-lm','-o',str(executable)],check=True)
            result = subprocess.run([str(executable)],capture_output=True,text=True,timeout=60,
                                    env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1',
                                         'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'})
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(result.stdout.strip(),'PASS sanitized orientation maps and rejected ranges')
            self.assertEqual(result.stderr,'')


if __name__ == '__main__':
    unittest.main()
