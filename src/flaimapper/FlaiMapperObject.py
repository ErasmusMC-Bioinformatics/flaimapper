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


import os,re,random,operator,argparse,sys


from flaimapper.BAMParser import BAMParser
from flaimapper.SSLMParser import SSLMParser
from flaimapper.FragmentContainer import FragmentContainer
from flaimapper.FragmentFinder import FragmentFinder


class FlaiMapperObject(FragmentContainer):
	def __init__(self,input_format,verbosity):
		self.verbosity = verbosity
		
		self.input_format = input_format
		self.alignments = []
		
		self.sequences = {}
		
		if(self.verbosity == "verbose"):
			print " - Initiated FlaiMapper Object"
	
	def add_alignment(self,alignment_file):
		self.alignments.append(alignment_file)
	
	def run(self,regions,fasta_file):
		if(self.verbosity == "verbose"):
			print " - Running fragment detection"
		
		self.fasta_file = fasta_file
		
		for region in regions:
			if(self.verbosity == "verbose"):
				print "   - Masked region: "+region[0]+":"+str(region[1])+"-"+str(region[2])
				print "     * Acquiring statistics"
			
			if(self.input_format == 'bam'):
				aligned_reads = BAMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			elif(self.input_format == 'sslm'):
				aligned_reads = SSLMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			
			aligned_reads.parse_stats()
			
			if(self.verbosity == "verbose"):
				print "     * Detecting fragments"
			
			predicted_fragments = FragmentFinder(region,aligned_reads)
			self.add_fragments(predicted_fragments,self.fasta_file)
	
	def count_reads_per_region_custom_table(self,regions,links,all_predicted_fragments,reference_offset=0):
		"""
		All sequences in our library of ncRNAs have been extended with 10 bases.
		"""
		
		stats_table = {}
		stats_table['experimental']     = {'error_5p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'error_3p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'predicted':0,'not_predicted_no_reads':0,'not_predicted_with_reads':0}
		stats_table['not_experimental'] = {'error_5p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'error_3p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'predicted':0,'not_predicted_no_reads':0,'not_predicted_with_reads':0}
		
		
		#a = c(1:10) mse_a = sum((a - mean(a)) ^ 2) / length(a)
		
		if(self.verbosity == "verbose"):
			print " - Running fragment detection"
		
		i = 0
		j = 0
		
		
		for ncRNA in all_predicted_fragments.keys():
			if(links.has_key(ncRNA)):
				if(self.verbosity == "verbose"):
					print "   - Analysing: "+ncRNA
				
				annotations = regions.index[links[ncRNA]]
				
				predicted_fragments = all_predicted_fragments[ncRNA].getResults()
				
				i += 1
				
				for annotation in annotations.fragments:
					closest = self.find_closest_overlapping_fragment(annotation,predicted_fragments,reference_offset)
					j += 1
					
					if(closest):
						errors = self.find_errors(annotation,closest)#@todo ,reference_offset
						err_5p = errors[0]
						err_3p = errors[1]
						
						if(err_5p > 5):
							err_5p = ">5"
						elif(err_5p < -5):
							err_5p = "<-5"
						
						if(err_3p > 5):
							err_3p = ">5"
						elif(err_3p < -5):
							err_3p = "<-5"
						
						if(annotation.evidence == "experimental"):
							stats_table['experimental']["predicted"] += 1
							stats_table['experimental']["error_5p"][err_5p] += 1
							stats_table['experimental']["error_3p"][err_3p] += 1
							
						else:
							stats_table['not_experimental']["predicted"] += 1
							stats_table['not_experimental']["error_5p"][err_5p] += 1
							stats_table['not_experimental']["error_3p"][err_3p] += 1
						
					else:
						if(annotation.evidence == "experimental"):
							if(annotation.get_supporting_reads() == 0):
								stats_table['experimental']["not_predicted_no_reads"] += 1
							else:
								stats_table['experimental']["not_predicted_with_reads"] += 1
						else:
							if(annotation.get_supporting_reads() == 0):
								stats_table['not_experimental']["not_predicted_no_reads"] += 1
							else:
								stats_table['not_experimental']["not_predicted_with_reads"] += 1
		
		print i,"annotated pre-miRNAs"
		print j,"annotated miRNAs"
		
		return stats_table
	
	def count_reads_per_region_custom_mse(self,regions,links,all_predicted_fragments,reference_offset=0):
		"""
		All sequences in our library of ncRNAs have been extended with 10 bases.
		"""
		
		
		err_5p = []
		err_3p = []
		
		
		if(self.verbosity == "verbose"):
			print " - Running fragment detection"
		
		i = 0
		j = 0
		
		import numpy
		
		for ncRNA in all_predicted_fragments.keys():
			if(links.has_key(ncRNA)):
				if(self.verbosity == "verbose"):
					print "   - Analysing: "+ncRNA
				
				match = re.search("chr[^:]+:([0-9]+)-([0-9]+):",ncRNA)
				seq_length = abs(int(match.group(1)) - int(match.group(2)))
				
				annotations = regions.index[links[ncRNA]]
				
				predicted_fragments = all_predicted_fragments[ncRNA].getResults()
				
				
				i += 1
				
				for annotation in annotations.fragments:
					closest = self.find_closest_overlapping_fragment(annotation,predicted_fragments,reference_offset)
					j += 1
					
					if(closest):
						errors = self.find_errors(annotation,closest)	#@todo ,reference_offset
						err_5p.append(errors[0])
						err_3p.append(errors[1])
						
					else:
						ann_length = abs(annotation.stop - annotation.start) * 2
						#err_5p.append(ann_length)# take missed miRNA length instead
						#err_3p.append(ann_length)# take missed miRNA length instead
						err_5p.append(seq_length)# take missed miRNA length instead
						err_3p.append(seq_length)# take missed miRNA length instead
		
		# Calc Root Mean Square Error (RMSQ)
		err_5p = numpy.sqrt(numpy.mean(numpy.array(err_5p)**2))
		err_3p = numpy.sqrt(numpy.mean(numpy.array(err_3p)**2))
		
		return [err_5p,err_3p]
	
	def count_reads_per_region(self,regions,links,masked_regions,reference_offset=0):
		"""
		All sequences in our library of ncRNAs have been extended with 10 bases.
		"""
		
		stats_table = {}
		stats_table['experimental']     = {'error_5p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'error_3p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'predicted':0,'not_predicted_no_reads':0,'not_predicted_with_reads':0}
		stats_table['not_experimental'] = {'error_5p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'error_3p':{"<-5":0,-5:0,-4:0,-3:0,-2:0,-1:0,0:0,1:0,2:0,3:0,4:0,5:0,">5":0},'predicted':0,'not_predicted_no_reads':0,'not_predicted_with_reads':0}
		
		if(self.verbosity == "verbose"):
			print " - Running fragment detection"
		
		i = 0
		j = 0
		
		#for ncRNA in self.alignment_directories_indexed.keys():
		for region in masked_regions:
			ncRNA = region[0]
			if(links.has_key(ncRNA)):
				if(self.verbosity == "verbose"):
					print "   - Analysing: "+ncRNA
				
				annotations = regions.index[links[ncRNA]]
				
				if(self.input_format == 'bam'):
					aligned_reads = BAMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
				elif(self.input_format == 'sslm'):
					aligned_reads = SSLMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
				
				aligned_reads.parse_stats()
				
				predicted_fragments_obj = FragmentFinder(ncRNA,aligned_reads)
				predicted_fragments_obj.run()
				
				predicted_fragments = predicted_fragments_obj.results
				
				i += 1
				
				for annotation in annotations.fragments:
					closest = self.find_closest_overlapping_fragment(annotation,predicted_fragments,reference_offset)
					j += 1
					
					if(closest):
						errors = self.find_errors(annotation,closest,reference_offset)
						err_5p = errors[0]
						err_3p = errors[1]
						
						if(err_5p > 5):
							err_5p = ">5"
						elif(err_5p < -5):
							err_5p = "<-5"
						
						if(err_3p > 5):
							err_3p = ">5"
						elif(err_3p < -5):
							err_3p = "<-5"
						
						if(annotation.evidence == "experimental"):
							stats_table['experimental']["predicted"] += 1
							stats_table['experimental']["error_5p"][err_5p] += 1
							stats_table['experimental']["error_3p"][err_3p] += 1
							
						else:
							stats_table['not_experimental']["predicted"] += 1
							stats_table['not_experimental']["error_5p"][err_5p] += 1
							stats_table['not_experimental']["error_3p"][err_3p] += 1
						
					else:
						if(annotation.evidence == "experimental"):
							if(annotation.get_supporting_reads() == 0):
								stats_table['experimental']["not_predicted_no_reads"] += 1
							else:
								stats_table['experimental']["not_predicted_with_reads"] += 1
						else:
							if(annotation.get_supporting_reads() == 0):
								stats_table['not_experimental']["not_predicted_no_reads"] += 1
							else:
								stats_table['not_experimental']["not_predicted_with_reads"] += 1
		
		print i,"annotated pre-miRNAs"
		print j,"annotated miRNAs"
		
		return stats_table
	
	def count_error_with_intensity(self,regions,links,masked_regions,reference_offset=0):
		"""
		All sequences in our library of ncRNAs have been extended with 10 bases.
		"""
		out = []
		
		if(self.verbosity == "verbose"):
			print " - Running fragment detection"
		
		
		
		for region in masked_regions:
			ncRNA = region[0]
			if(links.has_key(ncRNA)):
				if(self.verbosity == "verbose"):
					print "   - Analysing: "+ncRNA
				
				annotations = regions.index[links[ncRNA]]
				
				if(self.input_format == 'bam'):
					aligned_reads = BAMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
				elif(self.input_format == 'sslm'):
					aligned_reads = SSLMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
				
				aligned_reads.parse_stats()
				
				predicted_fragments_obj = FragmentFinder(ncRNA,aligned_reads)
				predicted_fragments_obj.run()
				predicted_fragments = predicted_fragments_obj.getResults()
				
				aligned_reads.count_reads_per_region(predicted_fragments_obj.getResults())
				
				for mirna_annotation in annotations.fragments:
					closest_fragment = self.find_closest_overlapping_fragment(mirna_annotation,predicted_fragments,reference_offset)
					
					if(closest_fragment):
						errors = self.find_errors(mirna_annotation,[(closest_fragment.start - reference_offset), (closest_fragment.stop - reference_offset)])#@todo ,reference_offset
						err_5p = errors[0]
						err_3p = errors[1]
						
						#out.append({'5p':[closest_fragment[2],err_5p],'3p':[closest_fragment[3],err_3p]})
						out.append({'5p':[closest_fragment.supporting_reads_start,err_5p],'3p':[closest_fragment.supporting_reads_stop,err_3p],'coverage':closest_fragment.supporting_reads})
		
		return out
	
	def find_closest_overlapping_fragment(self,annotated_fragment,predicted_fragments,reference_offset=0):
		closest = False
		closest_overlapping_bases = 0
		for predicted_fragment in predicted_fragments:
			#predicted = [(predicted_fragment["start"] - reference_offset), (predicted_fragment["stop"] - reference_offset),predicted_fragment.start_supporting_reads,predicted_fragment.stop_supporting_reads]
			overlap = self.find_overlapping_bases([annotated_fragment.start,annotated_fragment.stop],[(predicted_fragment["start"] - reference_offset), (predicted_fragment["stop"] - reference_offset)])
			if(overlap > 0 and overlap > closest_overlapping_bases):
				closest_overlapping_bases = overlap
				closest = predicted_fragment
		
		return closest
	
	def find_overlapping_bases(self,fragment_1,fragment_2):
		if(fragment_2[0] < fragment_1[0]):
			return self.find_overlapping_bases(fragment_2,fragment_1)
		else:
			return fragment_1[1] - fragment_2[0]
	
	def find_errors(self,annotated_fragment,predicted_fragment,reference_offset=0):
		"""
		Example:
			   [ miRNA ]
			[ fragment* ]
		
		mirna: 4,12
		fragment: 0,14
		
		error_5p = 0 - 4 = -4
		error_3p = 13 - 12 = 1
		
		"""
		
		error_5p = predicted_fragment.start - annotated_fragment.start - reference_offset
		error_3p = predicted_fragment.stop - annotated_fragment.stop - reference_offset
		
		return [error_5p,error_3p]
	
	def convert_to_bed(self,regions,output):
		if(self.verbosity == "verbose"):
			print "   - Converting to BED: "+output
		
		if(output == "-"):
			fh = sys.stdout
		else:
			fh = open(output,"w")
		
		i = 0
		
		for region in regions:
			if(self.verbosity == "verbose"):
				print "   - Masked region: "+region[0]+":"+str(region[1])+"-"+str(region[2])
			
			if(self.input_format == 'bam'):
				aligned_reads = BAMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			elif(self.input_format == 'sslm'):
				aligned_reads = SSLMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			
			for read_stacked in aligned_reads.parse_reads_stacked():
				read = read_stacked[0]
				numberofhits = read_stacked[1]
				
				if(read.name):
					fh.write(region[0]+"\t"+str(read.start)+"\t"+str(read.stop)+"\t"+read.name+"\t"+str(numberofhits)+"\t-\n")
				else:
					fh.write(region[0]+"\t"+str(read.start)+"\t"+str(read.stop)+"\tunknown_read_"+str(i)+"\t"+str(numberofhits)+"\t-\n")
					i += 1
		
		fh.close()
	
	def convert_to_sam(self,regions,output):
		if(self.verbosity == "verbose"):
			print "   - Converting to SAM: "+output
		
		if(output == "-"):
			fh = sys.stdout
		else:
			fh = open(output,"w")
		
		i = 0
		
		# 1: write header
		fh.write("@HD	VN:1.0	SO:unsorted\n")
		for region in regions:
			if(self.input_format == 'bam'):
				aligned_reads = BAMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			elif(self.input_format == 'sslm'):
				aligned_reads = SSLMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			
			iterator = aligned_reads.parse_reads()
			if(next(iterator,None)):
				fh.write("@SQ	SN:"+region[0]+"	LN:"+str(region[2] - region[1] + 1)+"\n")
			
			del(iterator,aligned_reads)
		fh.write("@PG	ID:0	PN:manual_conversion_script	VN:0.0\n")
		
		# 2: write alignment
		for region in regions:
			if(self.verbosity == "verbose"):
				print "   - Masked region: "+region[0]+":"+str(region[1])+"-"+str(region[2])
			
			if(self.input_format == 'bam'):
				aligned_reads = BAMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			elif(self.input_format == 'sslm'):
				aligned_reads = SSLMParser(region[0],region[1],region[2],self.alignments,self.verbosity)
			
			for read in aligned_reads.parse_reads():
				if(read.name):
					fh.write(read.name)
				else:
					fh.write("unknown_read_"+str(i))
					i += 1
				
				strand = "60"
				fh.write("\t0\t"+region[0]+"\t"+str(read.start+1)+"\t"+strand+"\t"+str(read.stop - read.start)+"M\t*\t0\t0\t"+read.sequence+"\t*\tNH:i:1\n")
		
		fh.close()
