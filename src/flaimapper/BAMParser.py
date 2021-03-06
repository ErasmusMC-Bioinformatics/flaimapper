#!/usr/bin/env python

"""FlaiMapper: computational annotation of small ncRNA derived fragments using RNA-seq high throughput data

 Here we present Fragment Location Annotation Identification mapper
 (FlaiMapper), a method that extracts and annotates the locations of
 sncRNA-derived RNAs (sncdRNAs). These sncdRNAs are often detected in
 sequencing data and observed as fragments of their  precursor sncRNA.
 Using small RNA-seq read alignments, FlaiMapper is able to annotate
 fragments primarily by peak-detection on the start and  end position
 densities followed by filtering and a reconstruction processes.
 Copyright (C) 2011-2014:
 - Youri Hoogstrate
 - Elena S. Martens-Uzunova
 - Guido Jenster
 
 
 [License: GPL3]
 
 This file is part of flaimapper.
 
 flaimapper is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.
 
 flaimapper is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program. If not, see <http://www.gnu.org/licenses/>.

 Documentation as defined by:
 <http://epydoc.sourceforge.net/manual-fields.html#fields-synonyms>
"""



import os,re,random,operator,argparse,sys,subprocess
import pysam


from flaimapper.Read import Read
from flaimapper.ncRNAfragment import ncRNAfragment
from flaimapper.MaskedRegion import MaskedRegion



class BAMParser(MaskedRegion):
	"""parseNcRNA is a class that parses the BAM alignment files using pysam.
	"""
	def parse_reads(self):
		
		# Check if a valid index exists by requesting the very first element
		# If it throw's an exception, run 'samtools index' to index.
		for bam_file in self.alignments:
			fh = pysam.Samfile(bam_file)
			
			if(self.name in fh.references):
				try:
					fh.fetch(self.name, 0, 0)
					fh.close()
				except:
					fh.close()
					try:
						print ' - Indexing BAM file with samtools: '+bam_file
						subprocess.call(["samtools", "index", bam_file])# Create index
					except:
						sys.stderr.write('Couldn\'t indexing BAM file with samtools: '+bam_file+'\nAre you sure samtools is installed?\n')
		
		for bam_file in self.alignments:
			fh = pysam.Samfile(bam_file)
			
			if(self.name in fh.references):
				for read in fh.fetch(self.name, self.start, self.stop):
					
					# First coordinate is given at 0 base, the second as 1
					# Therefore the second is converted with "-1"
					yield Read(read.blocks[0][0],read.blocks[-1][1]-1,read.qname,read.seq)
