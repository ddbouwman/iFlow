"""
Class Program
Directs the running of an iFlow program given an input file.
The input file path should be provided when instantiating Program. It will then direct reading the input, instantiating
the requested modules and running these modules.


Date: 02-11-15
Authors: Y.M. Dijkstra, R.L. Brouwer
"""
import logging
from DataContainer import DataContainer
from RegistryChecker import RegistryChecker
from ModuleList import ModuleList
from nifty import toList
from Reader import Reader
from src.util import importModulePackages
import matplotlib as mpl
mpl.use('TkAgg')


class Program:
    # Variables
    logger = logging.getLogger(__name__)

    # Methods
    def __init__(self, cwd, inputFilePath):
        """create utilities required by the program,
        i.e. a registry checker, reader and module list
        """
        self.cwd = cwd
        self.inputFilePath = inputFilePath

        self._registryChecker = RegistryChecker()
        self._inputReader = Reader()
        self.moduleList = ModuleList()

        self.__prepModuleResult = DataContainer()
        return
    
    def run(self):
        """Run the program and time the overall calculation time.
        Main steps: read input, build call stack, call modules according to call stack.
        """

        # read input, build call stack and retrieve data required
        self.__readInput()
        self.__buildCallStack()

        # run call stack
        self.__runCallStack()
        return

    def __runCallStack(self):
        """Run all calculation modules in the call stack.
        This requires the input to be loaded and processed into a call stack in the class variable self.moduleList
        """
        self.moduleList.runCallStack()
        return

    def __readInput(self):
        """call other methods to read input file and initiate the requested modules.
        """
        # open file
        self._inputReader.open(self.inputFilePath)

        # load imports
        imports = self._inputReader.readline('import')
        importModulePackages(self.cwd, imports)

        # load output settings
        outputReq = self.__loadOutput()

        # load other modules specified in input file
        self.__loadModule(outputReq)

        # close file
        self._inputReader.close()

        return

    def __loadOutput(self):
        """Read output requirements under 'requirements' keyword

        Returns:
            DataContainer containing output requirements
        """
        # read data from config and input file (NB. input file data may overwrite config data)
        outputData = self._inputReader.read('requirements')

        # check if a block of output requirements was found
        # if nothing is specified, do require output
        # if more than one block is found, take the last one
        if len(outputData) > 0:
            outputData = outputData[-1]
        else:
            outputData = DataContainer()

        return outputData


    def __loadModule(self, outputReq):
        """Read data of modules from input file
        For all found modules, it reads the data from input, loads its registry record and instantiates it.
        Registry records containing placeholder '@' will be refactored here before instantiating a module.

        Parameters:
            outputReq - (DataContainer) with output requirements as read from input
        """
        # read data from config and input file (NB. input file data may overwrite config data)
        configData = self.__loadConfig()
        inputData = self._inputReader.read('module')
        for dataContainer in inputData:
            # for each tag 'module' in input:
            #   iterate over all module types specified
            moduleList = toList(dataContainer.v('module'))

            for moduleName in moduleList:
                # make a new copy of the data container so that each module has a unique data container
                data = DataContainer()
                data.merge(configData)
                data.merge(dataContainer)       # input data may overwrite config data
                data.addData('module', moduleName)

                # load their registry
                registerData = self._registryChecker.readRegistryEntry(moduleName)
                self._registryChecker.refactorRegistry(data, registerData, output=outputReq)

                # check if the module is a visualisation module. If so, set alwaysRun to True
                alwaysRun = False
                outputModule = False
                if registerData.v('visualisationModule') == 'True':
                    alwaysRun = True
                if registerData.v('outputModule') == 'True':
                    outputModule = True
                    # do not include config data for output module
                    data = DataContainer()
                    data.merge(dataContainer)
                    data.addData('module', moduleName)
                    data.addData('inputFile', self.inputFilePath)       # output needs the input file, add this to its data

                # make the module
                self.moduleList.addModule(data, registerData, outputReq, alwaysRun=alwaysRun, outputModule=outputModule)
        return

    def __buildCallStack(self):
        self.moduleList.buildCallStack()
        return

    def __loadConfig(self):
        import config
        configvars = [var for var in dir(config) if not var.startswith('__')]
        d = {}
        for var in configvars:
            exec('d[var] = config.'+var)
        return DataContainer(d)