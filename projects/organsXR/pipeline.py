import os
import sys
from pipe import pipe
import pipeTools
import generalUtils
import bed
from glob import glob
import argparse
import argument
sys.path.append('..')
from referenceGenomePath import referenceGenomePath

class myPipe(pipe):
    def __init__(self, input, args = argument.args()):
        pipe.__init__(self, input, args)
        OUTPUT_DIR = '0220'
        SAMPLE_STAT_FILE = 'samples.csv'    
        self.input = os.path.join(os.path.curdir, 'dataDir', 'raw', self.input)
        # self.execM = self.execMwm
        self.outputDir = os.path.realpath(os.path.join(os.path.dirname(self.input), '..', OUTPUT_DIR))
        os.system('mkdir -p ' + self.outputDir)
        sampleDictionary = generalUtils.table2dictionary(SAMPLE_STAT_FILE, 'sample')[input][0]
        self = pipeTools.assignProperty(self, sampleDictionary)
        self.attributes = sorted(sampleDictionary.keys())
        # self.treatment = sampleDictionary['treatment_title']
        # self.group = sampleDictionary['group']
        self.saveInput([self.input])
        self.defaultWmParams = {
            '--mem=': 32000,
            '-n ': 1,
            '-t ': '24:00:00',
            '--job-name=': 'XR-seq',
            '-o ': 'log_' + self.treatment + '.txt',
            '-e ': 'err_' + self.treatment + '.txt',
        }
        self.wmParams = self.defaultWmParams
        
        self.paths = referenceGenomePath()


        # self.mm10 = {
        #     "name": "",
        #     "bowtie": "/proj/seq/data/MM10_UCSC/Sequence/BowtieIndex/genome",
        #     "fasta": "/proj/seq/data/MM10_UCSC/Sequence/WholeGenomeFasta/genome.fa",
        #     "limits": "/proj/seq/data/MM10_UCSC/Sequence/WholeGenomeFasta/genome.fa.fai",
        #     "genes": "/proj/sancarlb/users/ogun/seq/mm10/geneList_yy_6.bed",
        #     "chmm": {
        #         "liver": "NA",
        #         "spleen": "NA",
        #         "kidney": "NA",
        #         "testes": "NA"
        #     }
        # }
        # self.mm9 = {
        #     "name": "_mm9",
        #     "bowtie": "/proj/seq/data/MM9_UCSC/Sequence/BowtieIndex/genome",
        #     "fasta": "/proj/seq/data/MM9_UCSC/Sequence/WholeGenomeFasta/genome.fa",
        #     "limits": "/proj/seq/data/MM9_UCSC/Sequence/WholeGenomeFasta/genome.fa.fai",
        #     "genes": "NA",
        #     "chmm": {
        #         "liver": "/nas/longleaf/home/adebali/ogun/seq/mm9/chromatin_states_chromHMM_mm9/liver_cStates_HMM",
        #         "spleen": "/nas/longleaf/home/adebali/ogun/seq/mm9/chromatin_states_chromHMM_mm9/spleen_cStates_HMM",
        #         "kidney": "/nas/longleaf/home/adebali/ogun/seq/mm9/chromatin_states_chromHMM_mm9/kidney_cStates_HMM",
        #         "testes": "/nas/longleaf/home/adebali/ogun/seq/mm9/chromatin_states_chromHMM_mm9/testes_cStates_HMM"
        #     }
        # }


    def catFiles(self, wildcard, headers, output):
        code = "echo -e '" + '\t'.join(headers) + "' >" + output + " & " + "cat " + wildcard + " | grep -v '^==' | grep -v -e '^$' >>" + output
        print(code)
        os.system(code)

    def fullPath2wildcard(self, fullPath):
        basename = os.path.basename(fullPath)
        directory = os.path.dirname(fullPath)
        wildcard = ".".join(["*"] + basename.split(".")[1:])
        fullWildcard = os.path.join(directory, wildcard)
        return fullWildcard

    def mergeNucleotideFrequencies(self):
        wildcard = self.fullPath2wildcard(self.input[0])
        headers = ['position', 'sequence', 'value'] + sorted(self.attributes)
        output = os.path.join(self.outputDir, '..', 'merged_NucleotideFrequencies.txt')
        self.catFiles(wildcard, headers, output)
        return self

    def cutadapt_fastq2fastq(self):
        output = pipeTools.listOperation(pipeTools.changeDir, self.output, self.outputDir)
        self.saveOutput(output)
        # adapter = 'TGGAATTCTCGGGTGCCAAGGAACTCCAGTCACATCACGATCTCGTATGCCGTCTTCTGCTTG'
        adapter = 'TGGAATTCTCGGGTGCCAAGGAACTCCAGTNNNNNNACGATCTCGTATGCCGTCTTCTGCTTG'
        codeList = [
            'cutadapt',
            '-a', adapter,
            '-o', output,
            self.input
        ]
        self.execM(codeList)
        return self


    def bowtie_fastq2sam(self, reference):
        self.reference = self.paths.get(reference)
        noCpus = 4
        self.mutateWmParams({'-n ': str(noCpus)})
        output = [self.output[0]]
        codeList = [
            'bowtie',
            '-t', self.reference['bowtie'],
            '-q', # FASTAQ input (default)
            '--nomaqround', # Do NOT round MAC
            '--phred33-quals', # Depends on the sequencing platform
            '-S', # Output in SAM format
            '-n', 2, # No more than 2 mismatches
            '-e', 70, # The sum of the Phred quality values at all mismatched positions (not just in the seed) may not exceed E 
            '-m 4', # Do not report the reads that are mapped on to more than 4 genomic locations
            '-p', noCpus,
            '--seed 123', # Randomization parameter in bowtie,
            self.input,
            self.output
        ]
        self.execM(codeList)
        return self
   
    def convertToBam_sam2bam(self):
        codeList = [
            'samtools',
            'view',
            '-Sb'
            '-o',
            self.output,
            self.input
        ]
        self.execM(codeList)
        return self
   
    def convertToBed_bam2bed(self):
        codeList = [
            'bedtools',
            'bamtobed',
            '-i', self.input,
            '>', self.output
        ]
        self.execM(codeList)
        return self

    def uniqueSort_bed2bed(self):
        codeList = [
            'sort',
            '-u',
            '-k1,1',
            '-k2,2n',
            '-k3,3n',
            self.input,
            '>', self.output
        ]
        self.finalBed = self.output[0]
        self.execM(codeList)
        return self

    def splitByStrand_bed2bed(self):
        strand = ['+', '-']
        output = [
            self.addExtraWord(self.output[0], '_Plus'), 
            self.addExtraWord(self.output[0], '_Minus')
        ]
        self.saveOutput(output)
        self.saveOutput(self.prettyOutput())
        codeList = [
            'grep',
            strand,
            self.input[0],
            '>',
            self.output
        ]
        self.execM(codeList)
        return self

    def convertToBedGraph_bed2bdg(self):
        if self.runFlag and self.runMode:
            scaleFactor = float(1000000)/self.internalRun(bed.bed(self.input[0]).getHitNum, [], self.runFlag, 'get hit number')
        else:
            scaleFactor = 1
        codeList = [
            'bedtools',
            'genomecov',
            '-i', self.input,
            '-g', self.reference['limits'],
            '-bg',
            '-scale', scaleFactor,
            '>', self.output
        ]
        self.execM(codeList)
        return self

    def toBigWig_bdg2bw(self):
        codeList = [
            'bedGraphToBigWig',
            self.input,
            self.reference['limits'],
            self.output
        ]
        self.execM(codeList)
        return self

    def convertBedToFasta_bed2fa(self):
        codeList = [
            'bedtools',
            'getfasta',
            '-fi', self.reference['fasta'],
            '-bed', self.input,
            '-fo', self.output,
            '-s' # Force strandedness. If the feature occupies the antisense strand, the sequence will be reverse complemented
        ]
        self.execM(codeList)
        return self

    def getNucleotideAbundanceTable_fa2csv(self):
        codeList = [
            'fa2kmerAbundanceMeltedData.py',
            '-i', self.input,
            '-o', self.output,
            '--percentage'
        ]
        self.execM(codeList)
        return self

    def plotNucleotideAbundance_csv2pdf(self):
        codeList = [
            'plotNucleotideAbundance.r',
            self.input,
            self.treatment
        ]
        self.execM(codeList)
        return self

    def lengthDistribution_bed2csv(self):
        codeList = [
            'bed2lengthDistribution.py',
            '-i', self.input,
            '>', self.output
        ]
        self.execM(codeList)
        return self

    def get26mer_bed2bed(self):
        codeList = [
            'bed2getCertainIntervalLengths.py',
            '-i', self.input,
            '-o', self.output,
            '-l', 27
        ]
        self.execM(codeList)
        return self

    def plotLengthDistribution_csv2pdf(self):
        codeList = [
            'plotLengthDistribution.R',
            self.input,
            self.treatment
        ]
        self.execM(codeList)
        return self

    def addTreatment_csv2csv(self, *nargs):
        columns = self.list2attributes(self.attributes) + list(nargs)
        codeList = [
            'addColumns.py',
            '-i', self.input,
            '-o', self.output,
            '-c', ' '.join(columns)
        ]
        self.execM(codeList)
        columnHeaders = self.attributes
        return self
   
    def geneStrandMap_bed2txt(self):
        newOutput = [self.addExtraWord(self.output[0], '_TS'), self.addExtraWord(self.output[0], '_NTS')]
        self.saveOutput(newOutput)
        strandParameters = ['-S', '-s'] #[different strand, same strand]
        self.input = [self.input[0], self.input[0]]
        codeList = [
            'bedtools',
            'intersect',
            # '-a', self.reference["genes"],
            '-a', self.reference["genesNR"],
            '-b', self.input,
            '-wa',
            '-c',
            strandParameters,
            '-F', 0.50,
            '>', self.output
        ]
        self.execM(codeList)
        return self

    def normalizeCounts_txt2txt(self):
        print(self.output)
        if self.runFlag and self.runMode:
            self.scaleFactor = float(1000000)/self.internalRun(bed.bed(self.finalBed).getHitNum, [], self.runFlag, 'get hit number')
        else:
            self.scaleFactor = 1
        codeList = [
            'bedCount2normalizedCount.py',
            '-i', self.input,
            '-c', 7,
            '-m', self.scaleFactor,
            '-l', 1000,
            # '--bypassLength',
            '-o', self.output
        ]
        self.execM(codeList)
        return self

    def addTreatmentAndStrand_txt2txt(self):
        columns = self.list2attributes(self.attributes)
        columnStringList = [' '.join(columns + ['TS']), ' '.join(columns + ['NTS'])]
        codeList = [
            'addColumns.py',
            '-i', self.input,
            '-o', self.output,
            '-c', columnStringList
        ]
        self.execM(codeList)
        return self

    def mergeGeneCounts(self, extraWord = ""):
        wildcard = self.fullPath2wildcard(self.input[0]).replace("_TS", "_*S")
        headers = ['chr', 'start', 'end', 'name', 'score', 'strand', 'count'] + self.attributes + ['TSNTS']
        output = os.path.join(self.outputDir, '..', 'merged_geneCounts' + extraWord + '.txt')
        self.catFiles(wildcard, headers, output)
        dcast_output = os.path.join(self.outputDir, '..', 'merged_geneCounts' + extraWord + '_dcasted.txt')
        code = "Rscript dcast.r " + output + " " + dcast_output
        parameters = {
            "--job-name=": "dcast",
            "-n ": 1,
            "--mem=": 4000,
            "--time=": "1-00:00:00",
            "--output=": "./log/%A_%a.out",
            "--error=": "./log/%A_%a.err",
            "--array=": 1,
            "--mail-type=": "END,FAIL",      # notifications for job done & fail
            "--mail-user=": "oadebali@gmail.com" # send-to address
        }
        import slurm
        job = slurm.Slurm(code)
        job.assignParams(parameters)
        job.printScript()
        jobId = job.run()
        return self

    def prettyOutput(self):
        newOutputs = []
        for o in self.output:
            if 'Plus' in o:
                extraWord = '_Plus'
            elif 'Minus' in o:
                extraWord = '_Minus'
            else:
                extraWord = ''
            extension = pipeTools.getExtension(o)
            newOutputs.append(os.path.join(os.path.dirname(o),self.treatment_title + extraWord + '.' + extension))
        return newOutputs
   
    def addTreatment_csv2txt(self):
        columns = self.list2attributes(self.attributes)
        columnStringList = ' '.join(columns)
        codeList = [
            'addColumns.py',
            '-i', self.input,
            '-o', self.output,
            '-c', columnStringList
        ]
        self.execM(codeList)
        return self

    def mergeNucleotideAbundance(self, extraWord = ""):
        wildcard = self.fullPath2wildcard(self.input[0])
        headers = ['position', 'sequence', 'value'] + self.attributes
        output = os.path.join(self.outputDir, '..', 'merged_nucAbu' + extraWord + '.txt')
        self.catFiles(wildcard, headers, output)
        return self

    def getDimerAbundanceTable_fa2csv(self):
        codeList = [
            'fa2kmerAbundanceMeltedData.py',
            '-i', self.input,
            '-o', self.output,
            '-k', 2,
            '--percentage'
        ]
        self.execM(codeList)
        return self

  

def getArgs():
    parser = argparse.ArgumentParser(description='XR-seq Mouse Organs Pipeline', prog="pipeline.py")
    parser.add_argument('--outputCheck', required= False, default=False, action='store_true', help='checkOutput flag')
    
    subparsers = parser.add_subparsers(help='pipeline help', dest="subprogram")

    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument('-n', required= True, help='input index')
    parser_run.add_argument('--mock', required= False, default=False, action='store_true', help='mock flag')
    parser_run.add_argument('--noPrint', required= False, default=False, action='store_true', help='prints no code when stated')

    parser_cat = subparsers.add_parser('cat', help='cat help')
    parser_cat.add_argument('-n', required= False, default="1", help='input index')
    parser_cat.add_argument('--mock', required= False, default=True, action='store_true', help='mock flag')
    parser_cat.add_argument('--noPrint', required= False, default=True, action='store_true', help='prints no code when stated')

    args = parser.parse_args()
    return argument.args(args)

def sampleIO(fileName, in_, by_, out_):
    d1 = generalUtils.table2dictionary(generalUtils.file(fileName), by_)
    d2 = d1[in_][0]
    return d2[out_]

def getInputFromIndex(n):
    SAMPLE_STAT_FILE = 'samples.csv'
    return sampleIO(SAMPLE_STAT_FILE, n, 'no', 'sample')


args = getArgs()
inputIndex = args.get("n")
input = getInputFromIndex(inputIndex)

###########################################################
#  Pipeline
###########################################################
p = myPipe(input, args)
(p
    .run(p.cutadapt_fastq2fastq, False)
    .run(p.bowtie_fastq2sam, False, 'mm10')
    .run(p.convertToBam_sam2bam, False)
    .run(p.convertToBed_bam2bed, False)
    .run(p.uniqueSort_bed2bed, False)
    
    .branch(False)
        .run(p.splitByStrand_bed2bed, True)
        
        .branch(True)
            .run(p.convertToBedGraph_bed2bdg, True)
            .run(p.toBigWig_bdg2bw, True)
        .stop()
    .stop()

    .branch(False)
        .run(p.lengthDistribution_bed2csv, True)
        .run(p.plotLengthDistribution_csv2pdf, True)
    .stop()

    .branch(False)
        .run(p.get26mer_bed2bed, True)
        .run(p.convertBedToFasta_bed2fa, True)
        .branch(True) # Plot nucleotide abundance
            .run(p.getNucleotideAbundanceTable_fa2csv, True)
            .run(p.addTreatment_csv2txt, True)
            .cat(p.mergeNucleotideAbundance, True)
        .stop()

        .branch(True) # Plot dinucleotide abundance
            .run(p.getDimerAbundanceTable_fa2csv, True)
            .run(p.addTreatment_csv2txt, True)
            .cat(p.mergeNucleotideAbundance, True, '_diNuc')
        .stop()
    .stop()
   
    .branch(True)
        .run(p.geneStrandMap_bed2txt, True)

        .branch(True)
            .run(p.addTreatmentAndStrand_txt2txt, True)
            .cat(p.mergeGeneCounts, True, '_noNorm')
        .stop()

        .branch(True)
            .run(p.normalizeCounts_txt2txt, True)
            .run(p.addTreatmentAndStrand_txt2txt, True)
            .cat(p.mergeGeneCounts, True)
        .stop()
    .stop()    
)
