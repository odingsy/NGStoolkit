#!/usr/bin/env python
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
import tempfile

class myPipe(pipe):
    def __init__(self, input, args = argument.args()):
        SAMPLE_STAT_FILE = 'samples.csv'    
        OUTPUT_DIR = "0512"
        pipe.__init__(self, input, args)
        self.input = os.path.realpath(os.path.join(os.path.curdir, 'dataDir', 'raw', input))
        self.outputDir = os.path.realpath(os.path.join(os.path.dirname(self.input), '..', OUTPUT_DIR))
        os.system('mkdir -p ' + self.outputDir)
        sampleDictionary = generalUtils.table2dictionary(SAMPLE_STAT_FILE, 'sample')[input][0]
        self.attributes = sorted(sampleDictionary.keys())
        self = pipeTools.assignProperty(self, sampleDictionary)
        input = generalUtils.file(os.path.realpath(os.path.join('dataDir', 'raw', input)))
        self.saveInput([self.input])
        self.paths = referenceGenomePath()


        self.readNumber = 1000000

    def catFiles(self, wildcard, headers, output):
        code = "echo -e '" + '\t'.join(headers) + "' >" + output + " & " + "tail --lines=+2 " + wildcard + " | grep -v '^==' | grep -v -e '^$' >>" + output
        os.system(code)


    def fullPath2wildcard(self, fullPath):
        basename = os.path.basename(fullPath)
        directory = os.path.dirname(fullPath)
        wildcard = ".".join(["*"] + basename.split(".")[1:])
        fullWildcard = os.path.join(directory, wildcard)
        return fullWildcard

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


    def bowtie_fastq2sam(self, referenceGenome = 'mm10'):
        self.reference = self.paths.get(referenceGenome)
        output = pipeTools.listOperation(pipeTools.changeDir, self.output, self.outputDir)
        self.saveOutput([self.addExtraWord(output[0], self.reference["name"])])
        noCpus = 1
        self.mutateWmParams({'-n ': str(noCpus)})
        output = [self.output[0]]
        codeList = [
            'bowtie',
            '-t', self.reference["bowtie"],
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

    def countGene_bed2txt(self):
        newOutput = [self.addExtraWord(self.output[0], '_TS'), self.addExtraWord(self.output[0], '_NTS')]
        self.saveOutput(newOutput)
        strandParameters = ['-S', '-s'] #[different strand, same strand]
        self.input = [self.input[0], self.input[0]]
        codeList = [
            'bedtools',
            'intersect',
            '-a', self.reference["genes"],
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

    def mergeGeneCounts(self):
        wildcard = self.fullPath2wildcard(self.input[0]).replace("_TS", "_*S")
        headers = ['chr', 'start', 'end', 'name', 'score', 'strand', 'count'] + self.attributes + ['TSNTS']
        output = os.path.join(self.outputDir, '..', 'merged_geneCounts.txt')
        self.catFiles(wildcard, headers, output)
        return self

    def countChmm_bed2bed(self):
        chmmFile = self.reference["chmm"][self.organ]
        codeList = [
            'bedtools',
            'intersect',
            '-a', chmmFile,
            '-b', self.input,
            '-c',
            '-F', 0.49,
            '|',
            'cut',
            '-f', '1-4,9-10',
            '>', self.output 
        ]
        self.execM(codeList)
        return self

    def tssTes_bed2txt(self, args={}):
        bedAfile = self.reference[args.get('bedA', 'genesNR')]

        random = args.get('random', False)
        if random:
            output = [
                self.addExtraWord(self.output[0], '_random'),
            ]
            self.saveOutput(output)

        averageLength = totalRecord = totalMappedReads = perNmappedReads= 1
        if self.runMode == True and self.runFlag == True:
            inputBed = bed.bed(self.input[0])
            totalMappedReads = inputBed.getHitNum()
            bedA = bed.bed(bedAfile)
            averageLength = bedA.getAverageLength()
            totalRecord = bedA.getHitNum()
            perNmappedReads = 1000000
        
        shuffleCode = [
            'bedtools',
            'shuffle',
            '-i', bedAfile,
            '-g', self.reference['limits'],
            '|',
            'sort',
            '-k1,1',
            '-k2,2n',
            '-k3,3n'
        ]


        codeList = [
            'cat',
            bedAfile
        ]

        codeList += [
            '|',
            'bedtools',
            'intersect',
            '-a', 'stdin',
            '-b', self.input,
            '-wa',
            '-wb',
            '-F', 0.50,
            '|',
            'bedIntersect2positionTxt.py',
            # '>', 'output.1.txt',
            # '&&',
            # 'cat', 'output.1.txt'
            '|',
            'bedIntersectPositionCount.py',
            '-count', 7,
            '-cat', 8,
            '-ends', 'remove',
            '-scale',
            1/float(totalRecord),
            100/float(averageLength),
            perNmappedReads/float(totalMappedReads),
            '-o', self.output
        ]
        self.execM(codeList)
        
        _temp, temp = tempfile.mkstemp()

        windowLength = 50
        oneSideFlankingLength = 5000

        # if random:
            # prepareAbedCodeList = list(shuffleCode)
        # else:
        prepareAbedCodeList = [
            'cat',
            bedAfile
        ]
        prepareAbedCodeList += [
            '|',
            'bed2updownstream.py',
            '--fixed',
            '-l', oneSideFlankingLength,
            '|',
            'bed2removeChromosomeEdges.py',
            '--fixed',
            '-l', oneSideFlankingLength,
            '-g', self.reference['limits'],
            '>', temp
        ]
        self.execM(prepareAbedCodeList)

        totalRecord = 1
        if self.runMode == True and self.runFlag == True:
            bedA = bed.bed(temp)
            totalRecord = bedA.getHitNum()/2

        flankingCodeList = [
            'bedtools',
            'intersect',
            # '-a', 'stdin',
            '-a', temp,
            '-b', self.input,
            '-wa',
            '-wb',
            '-F', 0.50,
            '|',
            'bedIntersect2positionTxt.py',
            '--flanking',
            '--fixed',
            '-w', windowLength,
            '|',
            'bedIntersectPositionCount.py',
            '-count', 7,
            '-cat', 4, 8,
            '-ends', 'remove',
            '-scale', 
            1/float(totalRecord), 
            1/float(windowLength),
            perNmappedReads/float(totalMappedReads),
            '>>', self.output,
            '&&',
            'rm', temp
        ]
        self.execM(flankingCodeList)
        return self

def getArgs():
    parser = argparse.ArgumentParser(description='XR-seq ZT Pipeline', prog="pipeline.py")
    parser.add_argument('--outputCheck', required= False, default=False, action='store_true', help='checkOutput flag')
    
    subparsers = parser.add_subparsers(help='pipeline help', dest="subprogram")

    parser_run = subparsers.add_parser('run', help='run help')
    parser_run.add_argument('-n', required= True, help='output')
    parser_run.add_argument('--mock', required= False, default=False, action='store_true', help='mock flag')
    parser_run.add_argument('--noPrint', required= False, default=False, action='store_true', help='prints no code when stated')

    parser_cat = subparsers.add_parser('cat', help='cat help')
    parser_cat.add_argument('-n', required= False, default="1", help='output')
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
    .run(p.bowtie_fastq2sam, False, 'mm10')
    .run(p.convertToBam_sam2bam, False)
    .run(p.convertToBed_bam2bed, False)
    .run(p.uniqueSort_bed2bed, False)

    .branch(True)
        .run(p.countGene_bed2txt, False)
        .run(p.normalizeCounts_txt2txt, False)
        
        .branch()
            .run(p.addTreatmentAndStrand_txt2txt, False)
            .cat(p.mergeGeneCounts, False)
        .stop()
    .stop()

    .branch(True)
        .run(p.tssTes_bed2txt, True)
    .stop()
)

# Chromatin State Analysis on MM9
p = myPipe(input, args)
(p
    .run(p.bowtie_fastq2sam, False, 'mm9')
    .run(p.convertToBam_sam2bam, False)
    .run(p.convertToBed_bam2bed, False)
    .run(p.uniqueSort_bed2bed, False)
    .run(p.countChmm_bed2bed, False)
)

# def f(x):
#     return (2e-17) * x**6 - (1e-13) * x**5 + (5e-10)*x**4 - (8e-07)*x**3 + (0.0008)*x**2 + (0.8324)*x + 20.877
# # y = 2E-17x6 - 1E-13x5 + 5E-10x4 - 8E-07x3 + 0.0008x2 + 0.8324x + 20.877
# y = 1.8501x - 542.29
# 240.49e0.0013x