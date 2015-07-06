import codecs 
import time
import datetime
import operator
import sys
import os
import codecs # for utf8
import string
import copy
import math
from latexTable import MakeLatexTable



total_word_count_in_parse 	= 0
g_encoding 			= "utf8"  
numberofcycles 			= 200
howmanycandidatesperiteration 	= 50
numberoflines 			=  20000



 

datadirectory 			= "../../data/french/"
corpusfile 			= "encarta_french_UTF8.txt"
shortoutname 			= "wordbreaker-encarta-" 

datadirectory 			= "../../data/spanish/"
corpusfile 			= "DonQuijoteutf8.txt"
shortoutname 			= "wordbreaker-donquijote-" 

datadirectory 			= "../../data/english/"
corpusfile 			= "browncorpus.txt"
shortoutname 			= "wordbreaker-brownC-" 


verboseflag = False

















# Jan 6: added precision and recall.


class LexiconEntry:
	def __init__(self, key = "", count = 0):
		self.m_Key = key
		self.m_Count = count
		self.m_Frequency= 0.0
		self.m_CountRegister = list()
		
		
	def ResetCounts(self, current_iteration):
		if len(self.m_CountRegister) > 0:
			last_count = self.m_CountRegister[-1][1]
			if self.m_Count != last_count:
				self.m_CountRegister.append((current_iteration-1, self.m_Count))
		else:
			self.m_CountRegister.append((current_iteration, self.m_Count))
		self.m_Count = 0
	def Display(self, outfile):
		print >>outfile, "%-20s" % self.m_Key
		for iteration_number, count in self.m_CountRegister:
			print >>outfile, "%6i %10s" % (iteration_number, "{:,}".format(count))
# ---------------------------------------------------------#
class Lexicon:
	def __init__(self):
		self.m_LetterDict=dict() 
		self.m_LetterPlog = dict()
		self.m_EntryDict = dict()
		self.m_TrueDictionary = dict()
		self.m_DictionaryLength = 0   #in bits! Check this is base 2, looks like default base in python
		self.m_Corpus 	= list()
		self.m_SizeOfLongestEntry = 0
		self.m_CorpusCost = 0.0
		self.m_ParsedCorpus = list()
		self.m_NumberOfHypothesizedRunningWords = 0
		self.m_NumberOfTrueRunningWords = 0
		self.m_BreakPointList = list()
		self.m_DeletionList = list()  # these are the words that were nominated and then not used in any line-parses *at all*.
		self.m_DeletionDict = dict()  # They never stop getting nominated.
		self.m_Break_based_RecallPrecisionHistory = list()
		self.m_Token_based_RecallPrecisionHistory = list()
		self.m_Type_based_RecallPrecisionHistory = list()
		self.m_DictionaryLengthHistory = list()
		self.m_CorpusCostHistory = list()
	# ---------------------------------------------------------#
	def AddEntry(self,key,count):
		this_entry = LexiconEntry(key,count)
		self.m_EntryDict[key] = this_entry
		if len(key) > self.m_SizeOfLongestEntry:
			self.m_SizeOfLongestEntry = len(key)
	# ---------------------------------------------------------#	
	# Found bug here July 5 2015: important, don't let it remove a singleton letter! John
	def FilterZeroCountEntries(self, iteration_number):
		TempDeletionList = dict()
		for key, entry in self.m_EntryDict.items():
			if len(key) == 1:
				entry.m_Count = 1
				continue
			if entry.m_Count == 0:
				print key, entry 
				self.m_DeletionList.append((key, iteration_number))
				self.m_DeletionDict[key] = 1
				TempDeletionList[key] = 1		
				print "Excluding this bad candidate: ", key
		for key in TempDeletionList:
			del self.m_EntryDict[key]
			
	# ---------------------------------------------------------#
	def ReadCorpus(self, infilename):
		print "Name of data file: ", infilename
		if not os.path.isfile(infilename):
			print "Warning: ", infilename, " does not exist."
		if g_encoding == "utf8":
			infile = codecs.open(infilename, encoding = 'utf-8')
		else:
			infile = open(infilename) 	 
		self.m_Corpus = infile.readlines() # bad code if the corpus is very large -- but then we won't use python.
		for line in self.m_Corpus:			 		 
			for letter in line:
				if letter not in self.m_EntryDict:
					this_lexicon_entry = LexiconEntry()
					this_lexicon_entry.m_Key = letter
					this_lexicon_entry.m_Count = 1
					self.m_EntryDict[letter] = this_lexicon_entry					 
				else:
					self.m_EntryDict[letter].m_Count += 1
		self.m_SizeOfLongestEntry = 1	
		self.ComputeDictFrequencies()
	# ---------------------------------------------------------#
	def ReadBrokenCorpus(self, infilename, numberoflines= 0):
		print "Name of data file: ", infilename
		if not os.path.isfile(infilename):
			print "Warning: ", infilename, " does not exist."
		if g_encoding == "utf8":
			infile = codecs.open(infilename, encoding = 'utf-8')
		else:
			infile = open(infilename) 	 
		 
		rawcorpus_list = infile.readlines() # bad code if the corpus is very large -- but then we won't use python.
		for line in rawcorpus_list:						 	 
			this_line = ""
			breakpoint_list = list()
			line = line.replace('.', ' .').replace('?', ' ?')
			line_list = line.split()
			if len(line_list) <=  1:
				continue			 	 
			for word in line_list:
				self.m_NumberOfTrueRunningWords += 1
				if word not in self.m_TrueDictionary:
					self.m_TrueDictionary[word] = 1
				else:
					self.m_TrueDictionary[word] += 1
				this_line += word
				breakpoint_list.append(len(this_line))	
			self. m_Corpus.append(this_line)			 		 
			for letter in line:
				if letter not in self.m_EntryDict:
					this_lexicon_entry = LexiconEntry()
					this_lexicon_entry.m_Key = letter
					this_lexicon_entry.m_Count = 1
					self.m_EntryDict[letter] = this_lexicon_entry					 
				else:
					self.m_EntryDict[letter].m_Count += 1	
				if letter not in self.m_LetterDict:
					self.m_LetterDict[letter] = 1
				else:
					self.m_LetterDict[letter] += 1		 
			if numberoflines > 0 and len(self.m_Corpus) > numberoflines:
				break		 
			self.m_BreakPointList.append(breakpoint_list)
		self.m_SizeOfLongestEntry = 1	
		self.ComputeDictFrequencies()



# ---------------------------------------------------------#
	def ComputeDictFrequencies(self):
		TotalCount = 0
		for (key, entry) in self.m_EntryDict.iteritems():
			TotalCount += entry.m_Count
		for (key, entry) in self.m_EntryDict.iteritems():
			entry.m_Frequency = entry.m_Count/float(TotalCount)
		TotalCount = 0
		for (letter, count) in self.m_LetterDict.iteritems():
			TotalCount += count
		for (letter, count) in self.m_LetterDict.iteritems():
			self.m_LetterDict[letter] = float(count)/float(TotalCount)
			self.m_LetterPlog[letter] = -1 * math.log(self.m_LetterDict[letter])
# ---------------------------------------------------------#
	# added july 2015 john
	def ComputeDictionaryLength(self):
		DictionaryLength = 0
		for word in self.m_EntryDict:
			wordlength = 0
			letters = list(word)
			for letter in letters:
				wordlength += self.m_LetterPlog[letter]
			DictionaryLength += wordlength
		self.m_DictionaryLength = DictionaryLength
		self.m_DictionaryLengthHistory.append(DictionaryLength)
			 
# ---------------------------------------------------------#
	def ParseCorpus(self, outfile, current_iteration):
		self.m_ParsedCorpus = list()
		self.m_CorpusCost = 0.0	
		self.m_NumberOfHypothesizedRunningWords = 0
		#total_word_count_in_parse = 0	 
		for word, lexicon_entry in self.m_EntryDict.iteritems():
			lexicon_entry.ResetCounts(current_iteration)
		for line in self.m_Corpus:	
			parsed_line,bit_cost = 	self.ParseWord(line, outfile)	 
			self.m_ParsedCorpus.append(parsed_line)
			self.m_CorpusCost += bit_cost
			for word in parsed_line:
				#if len(word) == 0:
				#	print "line 154, about to crash:", line, parsed_line
				self.m_EntryDict[word].m_Count +=1
				self.m_NumberOfHypothesizedRunningWords += 1
		self.FilterZeroCountEntries(current_iteration)
		self.ComputeDictFrequencies()
		self.ComputeDictionaryLength()
		print "\nCorpus     cost: ", "{:,}".format(int(self.m_CorpusCost))
		print   "Dictionary cost: ", "{:,}".format(int(self.m_DictionaryLength))
		sum = int(self.m_CorpusCost + self.m_DictionaryLength)
		print   "Total      cost: ", "{:,}".format(sum)
		print >>outfile, "\nCorpus cost: ", "{:,}".format(self.m_CorpusCost)
		print >>outfile, "\Dictionary cost: ", "{:,}".format(self.m_DictionaryLength)
		return  
# ---------------------------------------------------------#		 	 
	def PrintParsedCorpus(self,outfile):
		for line in self.m_ParsedCorpus:
			PrintList(line,outfile)		
# ---------------------------------------------------------#
	def ParseWord(self, word, outfile):
		wordlength = len(word)	 
		 
		Parse=dict()
		Piece = ""
		LastChunk = ""		 
		BestCompressedLength = dict()
		BestCompressedLength[0] = 0
		CompressedSizeFromInnerScanToOuterScan = 0.0
		LastChunkStartingPoint = 0
		# <------------------ outerscan -----------><------------------> #
		#                  ^---starting point
		# <----prefix?----><----innerscan---------->
		#                  <----Piece-------------->
		if verboseflag: print >>outfile, "\nOuter\tInner"
		if verboseflag: print >>outfile, "scan:\tscan:\tPiece\tFound?"
		for outerscan in range(1,wordlength+1):  
			Parse[outerscan] = list()
			MinimumCompressedSize= 0.0
			startingpoint = 0
			if outerscan > self.m_SizeOfLongestEntry:
				startingpoint = outerscan - self.m_SizeOfLongestEntry
			for innerscan in range(startingpoint, outerscan):
				if verboseflag: print >>outfile,  "\n %3s\t%3s  " %(outerscan, innerscan),				 
				Piece = word[innerscan: outerscan]	 
				if verboseflag: print >>outfile, " %5s"% Piece, 			 
				if Piece in self.m_EntryDict:		
					if verboseflag: print >>outfile,"   %5s" % "Yes.",		 
					CompressedSizeFromInnerScanToOuterScan = -1 * math.log( self.m_EntryDict[Piece].m_Frequency )				
					newvalue =  BestCompressedLength[innerscan]  + CompressedSizeFromInnerScanToOuterScan  
					if verboseflag: print >>outfile,  " %7.3f bits" % (newvalue), 
					if  MinimumCompressedSize == 0.0 or MinimumCompressedSize > newvalue:
						MinimumCompressedSize = newvalue
						LastChunk = Piece
						LastChunkStartingPoint = innerscan
						if verboseflag: print >>outfile,  " %7.3f bits" % (MinimumCompressedSize), 
				else:
					if verboseflag: print >>outfile,"   %5s" % "No. ",
			BestCompressedLength[outerscan] = MinimumCompressedSize
			if LastChunkStartingPoint > 0:
				Parse[outerscan] = list(Parse[LastChunkStartingPoint])
			else:
				Parse[outerscan] = list()
			if verboseflag: print >>outfile, "\n\t\t\t\t\t\t\t\tchosen:", LastChunk,
			Parse[outerscan].append(LastChunk)

			#if len(LastChunk) == 0:
			#	print >>outfile, "line 212", word, Parse[outerscan]		 
			#	print "line 212", word, "outerscan:", outerscan, "Last chunk:", LastChunk, Parse[outerscan]		

		if verboseflag: 
			PrintList(Parse[wordlength], outfile)
		bitcost = BestCompressedLength[outerscan]
		return (Parse[wordlength],bitcost)
# ---------------------------------------------------------#
	def GenerateCandidates(self, howmany, outfile):
		Nominees = dict()
		NomineeList = list()
		for parsed_line in self.m_ParsedCorpus:	 
			for wordno in range(len(parsed_line)-1):
				candidate = parsed_line[wordno] + parsed_line[wordno + 1]				 		 
				if candidate in self.m_EntryDict:					 
					continue										 
				if candidate in Nominees:
					Nominees[candidate] += 1
				else:
					Nominees[candidate] = 1					 
		EntireNomineeList = sorted(Nominees.iteritems(),key=operator.itemgetter(1),reverse=True)
		for nominee, count in EntireNomineeList:
			if nominee  in self.m_DeletionDict:				 
				continue
			else:				 
				NomineeList.append((nominee,count))
			if len(NomineeList) == howmany:
				break
		#print "Nominees:"
		latex_data= list()
		latex_data.append("piece   count   status")
		for nominee, count in NomineeList:
			self.AddEntry(nominee,count)
			print "%20s   %8i" %(nominee, count)
			latex_data.append(nominee +  "\t" + "{:,}".format(count) )
		MakeLatexTable(latex_data,outfile)
		self.ComputeDictFrequencies()
		return NomineeList

# ---------------------------------------------------------#
	def Expectation(self):
		self.m_NumberOfHypothesizedRunningWords = 0
		for this_line in self.m_Corpus:
			wordlength = len(this_line)
			ForwardProb = dict()
			BackwardProb = dict()
			Forward(this_line,ForwardProb)
			Backward(this_line,BackwardProb)
			this_word_prob = BackwardProb[0]
			
			if WordProb > 0:
				for nPos in range(wordlength):
					for End in range(nPos, wordlength-1):
						if End- nPos + 1 > self.m_SizeOfLongestEntry:
							continue
						if nPos == 0 and End == wordlength - 1:
							continue
						Piece = this_line[nPos, End+1]
						if Piece in self.m_EntryDict:
							this_entry = self.m_EntryDict[Piece]
							CurrentIncrement = ((ForwardProb[nPos] * BackwardProb[End+1])* this_entry.m_Frequency ) / WordProb
							this_entry.m_Count += CurrentIncrement
							self.m_NumberOfHypothesizedRunningWords += CurrentIncrement			



# ---------------------------------------------------------#
	def Maximization(self):
		for entry in self.m_EntryDict:
			entry.m_Frequency = entry.m_Count / self.m_NumberOfHypothesizedRunningWords

# ---------------------------------------------------------#
	def Forward (self, this_line,ForwardProb):
		ForwardProb[0]=1.0
		for Pos in range(1,Length+1):
			ForwardProb[Pos] = 0.0
			if (Pos - i > self.m_SizeOfLongestEntry):
				break
			Piece = this_line[i,Pos+1]
			if Piece in self.m_EntryDict:
				this_Entry = self.m_EntryDict[Piece]
				vlProduct = ForwardProb[i] * this_Entry.m_Frequency
				ForwardProb[Pos] = ForwardProb[Pos] + vlProduct
		return ForwardProb

# ---------------------------------------------------------#
	def Backward(self, this_line,BackwardProb):
		
		Last = len(this_line) -1
		BackwardProb[Last+1] = 1.0
		for Pos in range( Last, Pos >= 0,-1):
			BackwardProb[Pos] = 0
			for i in range(Pos, i <= Last,-1):
				if i-Pos +1 > m_SizeOfLongestEntry:
					Piece = this_line[Pos, i+1]
					if Piece in self.m_EntryDict[Piece]:
						this_Entry = self.m_EntryDict[Piece]
						if this_Entry.m_Frequency == 0.0:
							continue
						vlProduct = BackwardProb[i+1] * this_Entry.m_Frequency
						BackwardProb[Pos] += vlProduct
		return BackwardProb


# ---------------------------------------------------------#		
	def PrintLexicon(self, outfile):
		for key in sorted(self.m_EntryDict.iterkeys()):			 
			self.m_EntryDict[key].Display(outfile) 
		for iteration, key in self.m_DeletionList:
			print >>outfile, iteration, key

# ---------------------------------------------------------#
	def RecallPrecision(self, iteration_number, outfile,total_word_count_in_parse):
		 
		total_true_positive_for_break = 0
		total_number_of_hypothesized_words = 0
		total_number_of_true_words = 0
		for linenumber in range(len(self.m_BreakPointList)):		 
			truth = list(self.m_BreakPointList[linenumber])			 
			if len(truth) < 2:
				print >>outfile, "Skipping this line:", self.m_Corpus[linenumber]
				continue
			number_of_true_words = len(truth) -1				
			hypothesis = list()  					 
			hypothesis_line_length = 0
			accurate_word_discovery = 0
			true_positive_for_break = 0
			word_too_big = 0
			word_too_small = 0
			real_word_lag = 0
			hypothesis_word_lag = 0
			 
			for piece in self.m_ParsedCorpus[linenumber]:
				hypothesis_line_length += len(piece)
				hypothesis.append(hypothesis_line_length)
			number_of_hypothesized_words = len(hypothesis) 			 

			# state 0: at the last test, the two parses were in agreement
			# state 1: at the last test, truth was # and hypothesis was not
			# state 2: at the last test, hypothesis was # and truth was not
			pointer = 0
			state = 0
			while (len(truth) > 0 and len(hypothesis) > 0):
				 
				next_truth = truth[0]
				next_hypothesis  = hypothesis[0]
				if state == 0:
					real_word_lag = 0
					hypothesis_word_lag = 0					
									
					if next_truth == next_hypothesis:
						pointer = truth.pop(0)
						hypothesis.pop(0)
						true_positive_for_break += 1
						accurate_word_discovery += 1
						state = 0
					elif next_truth < next_hypothesis:						 
						pointer = truth.pop(0)
						real_word_lag += 1
						state = 1
					else: #next_hypothesis < next_truth:						 
						pointer = hypothesis.pop(0)
						hypothesis_word_lag = 1
						state = 2
				elif state == 1:
					if next_truth == next_hypothesis:
						pointer = truth.pop(0)
						hypothesis.pop(0)
						true_positive_for_break += 1
						word_too_big += 1						
						state = 0
					elif next_truth < next_hypothesis:
						pointer = truth.pop(0)
						real_word_lag += 1
						state = 1 #redundantly
					else: 
						pointer = hypothesis.pop(0)
						hypothesis_word_lag += 1
						state = 2
				else: #state = 2
					if next_truth == next_hypothesis:
						pointer = truth.pop(0)
						hypothesis.pop(0)
						true_positive_for_break += 1
						word_too_small +=1
						state = 0
					elif next_truth < next_hypothesis:
						pointer = truth.pop(0)
						real_word_lag += 1
						state = 1
					else:
						pointer = hypothesis.pop(0)
						hypothesis_word_lag += 1
						state =2 						
			 			 
 
	
					
			precision = float(true_positive_for_break) /  number_of_hypothesized_words 
			recall    = float(true_positive_for_break) /  number_of_true_words 			
			 		
			total_true_positive_for_break += true_positive_for_break
			total_number_of_hypothesized_words += number_of_hypothesized_words
			total_number_of_true_words += number_of_true_words


		 



		# the following calculations are precision and recall *for breaks* (not for morphemes)

		formatstring = "%30s %6.4f %12s %6.4f"
		total_break_precision = float(total_true_positive_for_break) /  total_number_of_hypothesized_words 
		total_break_recall    = float(total_true_positive_for_break) /  total_number_of_true_words 	
		self.m_CorpusCostHistory.append( self.m_CorpusCost)
		self.m_Break_based_RecallPrecisionHistory.append((iteration_number,  total_break_precision,total_break_recall))
		print            formatstring %( "Break based Word Precision", total_break_precision, "recall", total_break_recall)
		print >>outfile, formatstring %( "Break based Word Precision", total_break_precision, "recall", total_break_recall)
		
		# Token_based precision for word discovery:
		


		if (True):
			true_positives = 0
			for (word, this_words_entry) in self.m_EntryDict.iteritems():
				if word in self.m_TrueDictionary:
					true_count = self.m_TrueDictionary[word]
					these_true_positives = min(true_count, this_words_entry.m_Count)
				else:
					these_true_positives = 0
				true_positives += these_true_positives
			word_recall = float(true_positives) / self.m_NumberOfTrueRunningWords
			word_precision = float(true_positives) / self.m_NumberOfHypothesizedRunningWords
			self.m_Token_based_RecallPrecisionHistory.append((iteration_number,  word_precision,word_recall))

			print >>outfile, formatstring %( "Token_based Word Precision", word_precision, "recall", word_recall)
			print            formatstring %( "Token_based Word Precision", word_precision, "recall", word_recall)
 

		# Type_based precision for word discovery:
		if (True):
			true_positives = 0
			for (word, this_words_entry) in self.m_EntryDict.iteritems():
				if word in self.m_TrueDictionary:
					true_positives +=1
			word_recall = float(true_positives) / len(self.m_TrueDictionary)
			word_precision = float(true_positives) / len(self.m_EntryDict)
			self.m_Type_based_RecallPrecisionHistory.append((iteration_number,  word_precision,word_recall))
			
			#print >>outfile, "\n\n***\n"
#			print "Type_based Word Precision  %6.4f; Word Recall  %6.4f" %(word_precision ,word_recall)
			print >>outfile, formatstring %( "Type_based Word Precision", word_precision, "recall", word_recall)
			print            formatstring %( "Type_based Word Precision", word_precision, "recall", word_recall)

# ---------------------------------------------------------#
	def PrintRecallPrecision(self,outfile):	
		print >>outfile, "\t\t\tBreak\t\tToken-based\t\tType-based"
		print >>outfile, "\t\t\tprecision\trecall\tprecision\trecall\tprecision\trecall"
		for iterno in (range(numberofcycles-1)):
			print "printing iterno", iterno
			(iteration, p1,r1) = self.m_Break_based_RecallPrecisionHistory[iterno]
			(iteration, p2,r2) = self.m_Token_based_RecallPrecisionHistory[iterno]
			(iteration, p3,r3) = self.m_Type_based_RecallPrecisionHistory[iterno]
			cost1 = int(self.m_DictionaryLengthHistory[iterno])
			cost2 = int(self.m_CorpusCostHistory[iterno] )
			#print >>outfile,"%3i\t%8.3f\t%8.3f\t%8.3f\t%8.3f\t%8.3f\t%8.3f" %(iteration, r1,p1,r2,p2,r3,p3)
			print >>outfile, iteration,"\t",cost1, "\t", cost2, "\t", p1,"\t",r1,"\t",p2,"\t",r2,"\t",p3,"\t",r3
			

# ---------------------------------------------------------#
def PrintList(my_list, outfile):
	print >>outfile
	for item in my_list:
		print >>outfile, item,  



corpusfilename 			= datadirectory  + corpusfile
outdirectory 			= datadirectory + "wordbreaking/"
outfilename 			= outdirectory + shortoutname+ str(numberofcycles) + "i.txt" 	
outfile_corpus_name= outdirectory + shortoutname + str(numberofcycles) + "_brokencorpus.txt"
outfile_lexicon_name= outdirectory + shortoutname+ str(numberofcycles) + "_lexicon.txt"
outfile_RecallPrecision_name= outdirectory + shortoutname + str(numberofcycles) +  "_RecallPrecision.tsv"

if g_encoding == "utf8":
	outfile = codecs.open(outfilename, "w", encoding = 'utf-8')
	outfile_corpus = codecs.open(outfile_corpus_name, "w", encoding = 'utf-8')
	outfile_lexicon = codecs.open(outfile_lexicon_name, "w",encoding = 'utf-8')
	outfile_RecallPrecision = codecs.open(outfile_RecallPrecision_name, "w", encoding = 'utf-8')
else:
	outfile = open(outfilename, "w") 	
	outfile_corpus = open(outfile_corpus_name, "w")
	outfile_lexicon = open(outfile_lexicon_name, "w")
	outfile_RecallPrecision = open(outfile_RecallPrecision_name, "w")

print >>outfile, "#" + str(corpusfile)
print >>outfile, "#" + str(numberofcycles) + " cycles."
print >>outfile, "#" + str(numberoflines) + " lines in the original corpus."
print >>outfile, "#" + str(howmanycandidatesperiteration) + " candidates on each cycle."

current_iteration = 0	
this_lexicon = Lexicon()
this_lexicon.ReadBrokenCorpus (corpusfilename, numberoflines)
print >>outfile, "#" + str(len(this_lexicon.m_TrueDictionary)) + " distinct words in the original corpus."

this_lexicon.ParseCorpus (outfile, current_iteration)

for current_iteration in range(1, numberofcycles):
	print "\n Iteration number", current_iteration, "out of ", numberofcycles
	print >>outfile, "\n\n Iteration number", current_iteration
	this_lexicon.GenerateCandidates(howmanycandidatesperiteration, outfile)
	this_lexicon.ParseCorpus (outfile, current_iteration)
	this_lexicon.RecallPrecision(current_iteration, outfile,total_word_count_in_parse)
	
this_lexicon.PrintParsedCorpus(outfile_corpus)
this_lexicon.PrintLexicon(outfile_lexicon)
this_lexicon.PrintRecallPrecision(outfile_RecallPrecision) 	 
outfile.close()
outfile_corpus.close()
outfile_lexicon.close()
outfile_RecallPrecision.close()








