#!/usr/bin/env python
import os
import sys
from pipe import pipe
import pipeTools
import generalUtils
import argparse
import argument
sys.path.append('../..')
from referenceGenomePath import referenceGenomePath

class myPipe(pipe):
    def __init__(self, input, args = argument.args()):
        SAMPLE_STAT_FILE = 'samples.csv'    
        OUTPUT_DIR = '1102'
        RAW_DATA_DIR = '/proj/sancarlb/users/wentao/20171031NT2RNAseq/rawdata'
        pipe.__init__(self, input, args)
        self.input = os.path.join(RAW_DATA_DIR, input)
        self.outputDir = os.path.realpath(os.path.join(os.path.curdir, 'dataDir', OUTPUT_DIR))
        os.system('mkdir -p ' + self.outputDir)
        sampleDictionary = generalUtils.table2dictionary(SAMPLE_STAT_FILE, 'sample')[input][0]
        self.attributes = sorted(sampleDictionary.keys())
        self = pipeTools.assignProperty(self, sampleDictionary)
        input = os.path.realpath(os.path.join('dataDir', 'raw', input))
        self.saveInput([self.input, self.input.replace("_1.fq.gz", "_2.fq.gz")])
        self.paths = referenceGenomePath()
        self.reference = self.paths.get('hg19')
        
    def catFiles(self, wildcard, headers, output):
        code = "echo -e '" + '\t'.join(headers) + "' >" + output + " & " + "cat " + wildcard + " | grep -v '^==' | grep -v -e '^$' >>" + output
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

    def salmon_gz2txt(self):
        output = pipeTools.listOperation(pipeTools.changeDir, self.output, self.outputDir)
        noCpus = 8
        self.saveOutput([output[0].replace('.txt', '')])
        self.output = self.prettyOutput()
        self.saveOutput(self.output)
        codeList = [
            'salmon quant',
            '-i', self.reference['salmon_quasi'],
            '-l', 'A',
            '--gcBias',
            '-p', noCpus,
            '-1', self.input[0],
            '-2', self.input[1],
            '-o', self.output[0]
        ]
        self.execM(codeList)

        return self
    def removeVersion_sa2txt(self):
        self.saveInput([os.path.join(self.input[0], 'quant.sf')])
        self.saveOutput([self.output[0].replace('.txt', '_quant.sf')])
        codeList = [
            'python',
            'removeTxVersion.py',
            self.input,
            '>', self.output
        ]
        self.execM(codeList)
        return self

    def moveQuant_sa2sf(self):
        self.output = self.prettyOutput()
        codeList = [
            'cp',
            os.path.join(self.input[0], 'quant.sf'),
            self.output[0].replace('.sf', '') + '_quant.sf'
        ]
        self.execM(codeList)
        return self

    def zipDir(self):
        wildcard = self.fullPath2wildcard(self.input[0])
        os.system('tar czvf dataDir/salmon.tar.gz ' + wildcard)


def getArgs():
    parser = argparse.ArgumentParser(description='Diffentiation RNA-seq Pipeline', prog="pipeline.py")
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
    .run(p.salmon_gz2txt, False)
    .run(p.removeVersion_sa2txt, True)
    .cat(p.zipDir, True)
)
