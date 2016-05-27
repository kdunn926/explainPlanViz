# For Flask bits
from flask import Flask, render_template, request, jsonify

# For explain plan parsing
import re
from collections import defaultdict
from math import ceil

# For graph representation
import pygraphviz as pgv
import base64
import tempfile 
import sys

# For Cloud Foundry
import os 

app = Flask(__name__, static_path='/static')


# PyGraphViz API
graph = pgv.AGraph(strict=False, directed=True)


def assignLevel(l):  
    return (len(l) - len(l.lstrip(' ')))


operationMetaInfoOne = re.compile("(cost=[0-9.]+)\W(rows=[0-9]+)\W(width=[0-9]+)")
operationMetaInfoTwo = re.compile("slice([0-9]+); segments: ([0-9]+)")
operationMetaInfoThree = re.compile("\W+([^:]+):(.*)$")
operationMetaInfoThreeB = re.compile("Avg ([\d.]+) rows x (\d+) workers")
operationMetaInfoFour = re.compile("\W+\(([^)]+)\)\W+(.*)$")


def parseMetadata(string):
    infoDict = {}
    
    info = operationMetaInfoOne.match(string)
    if info is not None:
        for g in info.groups():
            key, value = g.split("=")
            if key == "width":
                key = "dataWidth"
            infoDict[key] = value.strip()
        return infoDict
        
    info = operationMetaInfoTwo.match(string)
    if info is not None:
        # set slice = rank
        infoDict['slice'] = info.group(1)
        infoDict['segments'] = info.group(2)
        return infoDict
                                    
    info = operationMetaInfoThree.match(string)
    if info is not None:
        key = info.group(1).strip().replace(" ", "-")
        value = info.group(2).strip()
        analyzeInfo = operationMetaInfoThreeB.match(value)
        if analyzeInfo is not None:
            rows = float(analyzeInfo.group(1))
            workers = int(analyzeInfo.group(2))
            infoDict["analyzeRows"] = str(rows*workers)
        infoDict[key] = value
        return infoDict
    
    info = operationMetaInfoFour.match(string)
    if info is not None:
        key = info.group(1).strip()
        value = info.group(2).strip()
        infoDict[key] = value
        return infoDict
    
    return infoDict


# Parent/child operation tracking
levelParentList = []
levelParentLut = {}


def getParentFor(op):
    level = operationLevelLut[op]
    parentListIndex = levelParentList.index(level) - 1
    parentId = levelParentList[parentListIndex]
    return levelOperationLut[parentId]


def clean(string):
    return string.replace('<', '&lt;').replace('>', '&gt;')

def makeTableLabel(thisOp, attrs):
    global graph

    if "table" in attrs['label']:
        # Been there, done that
        return

    # http://web.mit.edu/spin_v4.2.5/share/graphviz/doc/html/info/colors.html
    colors = ["coral", "cornflowerblue", "cornsilk4", "cyan3", "darkgoldenrod3", 
              "darkolivegreen1", "darkorchid1", "darkseagreen", "darkslateblue", 
              "crimson", "plum", "midnightblue", "chartreuse", "olivedrab4", 
              "lightslateblue"]
    
    attrs['style'] = 'filled'
    attrs['fillcolor'] = "grey100"
    try:
        attrs['color'] = colors[int(attrs['slice']) - 1]
    except IndexError:
        attrs['color'] = "black"
    
    # Open with a table tag
    labelString = '<<table border="1" cellspacing="0" >\n'
    
    # Make sure Label is first
    labelString += '\t<tr><td border="2" colspan="2"><b>{}</b></td></tr>\n'.format(attrs['label'])
    
    # Build a table using all key-val pairs of set attributes
    for k, v in attrs.iteritems():
        # Ignore the label key, it was set as first row
        if k in ['label', 'color', 'fillcolor', 'style']:
            continue
        
        val = v
        rowTemplate = '\t<tr><td>{}</td><td>{}</td></tr>\n'
        
        if len(v) > 64:
            labelString += "".join([rowTemplate.format(k, clean(v[i:i+64])) for i in xrange(0, len(val), 64)])
        
        else:
            labelString += rowTemplate.format(k, val)
        
        # How to color things?
        # bgcolor="red"
        
    # Close the table
    labelString += '</table>>'
    
    # Set shape to none and apply the HTML
    # for GraphViz to render correctly
    attrs['shape'] = 'none'
    attrs['label'] = labelString
    
    n = graph.get_node(thisOp)
    for k, v in attrs.iteritems():
        n.attr[k] = attrs[k]

    
def pushEdgeFor(currentOperation, attrs, rowList):
    global graph

    parentOperation = getParentFor(currentOperation)
    
    if "slice" not in attrs[currentOperation]:
        attrs[currentOperation]['slice'] = attrs[parentOperation]['slice']
    
    makeTableLabel(parentOperation, attrs[parentOperation])

    if "analyzeRows" in attrs[currentOperation]:
        incomingRows = float(attrs[currentOperation]['analyzeRows'])
    elif "rows" in attrs[currentOperation]:
        incomingRows = int(attrs[currentOperation]['rows'])
    else:
        incomingRows = 1
        
    penWidth = ceil(8*incomingRows/float(max(rowList)))
    
    graph.add_edge(currentOperation, parentOperation, weight=incomingRows, penwidth=penWidth)
    makeTableLabel(currentOperation, attrs[currentOperation])


# Forward and reverse lookup tables
operationLevelLut = {}
levelOperationLut = {}


def textToDot(theExplain):
    global graph

    sliceList = re.findall("slice([0-9]+)", theExplain)


    rowList = re.findall("rows=([0-9]+)", theExplain)
    analyzeRowList = re.findall("Avg ([\d.]+) rows x (\d+) workers", theExplain)
    rowList = map(float, rowList) + map(lambda d: float(d[0])*int(d[1]), analyzeRowList)

    currentSlice = None
    currentOperation = None
    isFirst = True
    attrDict = defaultdict()
    operationLineInfo = re.compile("(?:->)?\W*([^(]+)\W*\(([^\)]+)\)\W*(?:\(([^\)]+)\))?")
    for n, l in enumerate(theExplain.splitlines()):
        if isFirst or "->" in l:
            isFirst = False

            # Wait until we have at least one parent/child pair
            if len(levelParentList) > 1: 
                pushEdgeFor(currentOperation, attrDict, rowList)
                
            currentLevel = assignLevel(l)
            info = operationLineInfo.match(l)

            # Only look at lines we have a matching format for
            if (info is None) and (len(parseMetadata(l).keys()) == 0):
                isFirst = True
                continue

            # Op Name
            newOperation = "{0}-{1}".format(info.group(1).strip(), n)
            
            operationLevelLut[newOperation] = currentLevel
            levelOperationLut[currentLevel] = newOperation
            
            # Track any unseen levels
            if currentLevel not in levelParentList:
                levelParentList.append(currentLevel)
            
            if currentLevel not in levelParentLut:
                # Store the parent of this operation
                levelParentLut[currentLevel] = getParentFor(newOperation)
            
            attrDict[newOperation] = dict()
            
            # Op metadata on same line as name
            for g in range(2, len(info.groups())):
                attrDict[newOperation].update(parseMetadata(info.group(g)))
            
            attrDict[newOperation]['label'] = newOperation.split("-")[0]
            
            graph.add_node(newOperation, **attrDict[newOperation])
            
            currentOperation = newOperation
            
        else:
            metadata = parseMetadata(l)
            
            if len(metadata.keys()) > 0:
                # Op metadata on line(s) following the name
                attrDict[currentOperation].update(metadata)
            
            
    # Add the final child operation and edge to parent
    pushEdgeFor(currentOperation, attrDict, rowList)

    theTempfile = tempfile.NamedTemporaryFile()

    graph.draw(theTempfile.name, prog='dot', format='svg')

    with open(theTempfile.name, "rb") as theImage:
        encoded_string = base64.b64encode(theImage.read())

    return encoded_string
    #return graph.to_string()


@app.route('/process', methods=['POST'])
def process():
    global levelParentList 
    global levelParentLut
    global operationLevelLut
    global levelOperationLut
    global graph

    # Reinitialize dirty globals
    levelParentList = []
    levelParentLut = {}
    operationLevelLut = {}
    levelOperationLut = {}

    graph = pgv.AGraph(strict=False,
                       directed=True)
    
    content = request.get_json(silent=True)

    return jsonify(png=textToDot(content['plan']))
    #return jsonify(dot=textToDot(content['plan']))


@app.route('/')
def index():
    return render_template('index.html')

port = os.getenv("PORT")
if port is None:
    port = 5000

if __name__ == '__main__':
    app.debug = True

    sys.path.append("/home/vcap/app/.heroku/vendor/bin")
    os.environ['PATH'] = os.environ['PATH'] + ":/home/vcap/app/.heroku/vendor/bin"

    print os.path.isfile("/home/vcap/app/.heroku/vendor/bin/dot")

    app.run(host='0.0.0.0', port=int(port))
