#Copyright 2012 Kevin Murray
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pyNGSQC
import sys
from tempfile import NamedTemporaryFile as namedtmp
import os


class Collapser(pyNGSQC.NGSQC):
    #MAX_FILE_SIZE = 2 << 30  # 2GB

    def __init__(
                 self,
                 in_file_name,
                 out_file_name,
                 key_length=6,
                 tmp_dir=None,
                 compression=pyNGSQC.GUESS_COMPRESSION,
                 verbose=False
                ):
        self.in_file_name = in_file_name
        self.out_file_name = out_file_name
        self.reader = pyNGSQC.FastqReader(
            self.in_file_name,
            compression=compression
            )
        self.tmp_dir = tmp_dir
        self.verbose = verbose
        self.key_length = key_length
        self.keys = []
        self.num_reads = 0L
        self.num_non_unique_reads = 0
        self.num_unique_reads = 0
        self.tmp_file_names = {}

    def _split_files(self):
        file_sizes = {}
        sub_file_handles = {}
        for read in self.reader:
            key = read[1][:self.key_length]
            # None means guess tmp dir
            if key not in self.keys:
                self.keys.append(key)
                # If in keys, file handle should exist
                sub_file_handles[key] = namedtmp(
                    mode="wb",
                    dir=self.tmp_dir,
                    prefix=key + "_",
                    delete=False
                    )
                file_name = sub_file_handles[key].name
                self.tmp_file_names[key] = file_name
            read_str = "\n".join(read)
            sub_file_handles[key].write(read_str + "\n")

        # get file size
        for key in self.keys:
            sub_file_handles[key].seek(0, 2)
            this_file_size = sub_file_handles[key].tell()
            file_sizes[key] = this_file_size
            sub_file_handles[key].close

    def _read_to_tuple(self, read):
        return (read[1], read[0], read[3], read[2])

    def _tuple_to_read(self, read_tuple):
        read = []
        read.append(read_tuple[1])
        read.append(read_tuple[0])
        read.append(read_tuple[3])
        read.append(read_tuple[2])
        return read

    def _sort(self):
        sorted_writer = pyNGSQC.FastqWriter(self.out_file_name)
        for key in sorted(self.keys):
            these_reads = []
            file_name = self.tmp_file_names[key]

            reader = pyNGSQC.FastqReader(file_name)
            for read in reader:
                these_reads.append(self._read_to_tuple(read))
            these_reads.sort()
            self.num_reads += reader.num_reads
            reader.close()

            last_read_seq = ""
            for read_tuple in these_reads:

                if read_tuple[0] != last_read_seq:
                    last_read_seq = read_tuple[0]
                    self.num_unique_reads += 1
                    sorted_writer.write(self._tuple_to_read(read_tuple))
                else:
                    self.num_non_unique_reads += 1
        for filename in self.tmp_file_names:
            os.remove(filename)

    def print_summary(self):
        sys.stderr.write("Collapser finished\n")
        sys.stderr.write("\tAnalysed %i reads\n" % self.num_reads)
        sys.stderr.write("\tFound %i unique reads\n" % self.num_unique_reads)
        sys.stderr.write("\tRemoved %i non-unique reads\n" % \
         self.num_non_unique_reads)

    def run(self):
        self._split_files()
        self._sort()
        self.print_summary()
        return True
