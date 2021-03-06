import os
import re

# Import function
def getImportCandidates(client, currentFile, symbol):
    """
    Used by the :TSImport command to find files where the given symbol
    is defined.

    :param client: an instance of the nvim-typescript tsserver client
    :param currentFile: the file currently focused in vim
    :param symbol: the symbol we're trying to import
    :returns: a list of absolute file paths in which the symbol is defined
    """
    matchingSymbols = client.getWorkspaceSymbols(currentFile, symbol)

    def filterSymbols(x):
        return x['matchKind'] == "exact" and \
            ('kindModifiers' in x) and \
            ('export' in x['kindModifiers'] or 'declare' in x['kindModifiers']) and \
            x['name'] == symbol  # tsserver `exact` matchKind is not case sensitive

    filtered = filter(filterSymbols, matchingSymbols)
    files = list(map(lambda x: x["file"], filtered))
    return files

def getRelativeImportPath(destinationFile, importFromFile):
    """
    Given two file paths, find out the relative path of the file in which the
    desired symbol is defined.
    For symbols defined in `node_modules`, the name of the module is used for the
    import. As this symbol is most likely defined via the @types system.

    :param destinationFile: the currently edited file in vim
    :param importFromFile: the file in which the desired symbol is defined
    :returns: The relative path of import
    """
    destinationFileDir = os.path.dirname(os.path.abspath(destinationFile))
    importFromFileDir = os.path.dirname(os.path.abspath(importFromFile))
    symbolFile = os.path.basename(importFromFile)

    # If the found symbol is in node_modules, the typings are probably handled
    # globally.
    if 'node_modules' in importFromFile:
        return _shaveNodeModulesPath(importFromFileDir)

    def getRelativePath():
        relPath = os.path.relpath(importFromFileDir, destinationFileDir)
        if not relPath.startswith('.') and not relPath.startswith('./'):
            relPath = './%s' % relPath
        return relPath

    relativePathFromDestinationFile = getRelativePath()

    if symbolFile == "index.ts" or symbolFile == 'index.d.ts':
        return "{}".format(relativePathFromDestinationFile)
    else:
        symbolFileWithoutExtenion = symbolFile[:-3]  # Remove the .ts part
        return "{}/{}".format(relativePathFromDestinationFile, symbolFileWithoutExtenion)

def createImportBlock(symbol, importPath, template):
    """
    Format the import statement to be included in the file

    :param symbol: the imported symbol
    :param importPath: the relative import path of the file in which the symbol is defined
    :param template: the user-configurable template string for the import style
    :returns: the import statement as a string
    """
    return template % (symbol, importPath)

def getCurrentImports(client, inspectedFile):
    """
    Lists the existing import statements in a given file

    :param client: a instance of the nvim-typescript tsserver client
    :param inspectedFile: the file from which we should list the import statements
    :returns: a tuple, car: the import statements,
                       cdr: the last line number of the import statements
    """
    imports = [x for x in client.getDocumentSymbols(inspectedFile)["childItems"]
               if x["kind"] == "alias"]

    importLineLocations = sorted(list(map(lambda x: x["spans"][0]["end"]["line"], imports)))
    lastImportLine = 0

    if len(importLineLocations) > 0:
        lastImportLine = importLineLocations[-1]

    return list(map(lambda x: x["text"], imports), lastImportLine)

def _shaveNodeModulesPath(candidate):
    return re.sub(r'^.*node_modules/([^/]+)(?:/.*$)?', r'\1', candidate)


def getKind(vim, kind):
    if kind in vim.vars["nvim_typescript#kind_symbols"].keys():
        return vim.vars["nvim_typescript#kind_symbols"][kind]
    else:
        return kind
