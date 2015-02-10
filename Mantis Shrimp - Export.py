#Copyright(c) 2014, Konrad K Sobon
#@arch_laboratory, http://archi-lab.net

"""
This component exports serialized geometry to specified location. Thank you to Mostapha Sadeghipour Roudsari
for providing invaluable help with this project. 

    Args:
        _geometry: any GH/or rhino referenced geometry
        _filePath: A local folder with file name and extension ex. C:\test.geo
        _export: Set Boolean to True to export geometry to destination folder
"""

ghenv.Component.Name = "Mantis Shrimp - Export"
ghenv.Component.NickName = 'exportMantisShrimp'
ghenv.Component.Category = "Mantis Shrimp"

import sys
import os
appDataPath = os.getenv('APPDATA')
msPath = appDataPath + r"\Dynamo\0.7\packages\Mantis Shrimp\extra"
if msPath not in sys.path:
    sys.path.append(msPath)
from mantisshrimp import *

import Rhino as rc
import cPickle as pickle
import Grasshopper.Kernel as gh
import scriptcontext as sc
from Grasshopper import DataTree
from Grasshopper.Kernel.Data import GH_Path

class SerializeObjects(object):
    
    def __init__(self, filePath, data = None):
        
        # create directory if it is not created
        folder, fileName = os.path.split(filePath)
        if not os.path.isdir(folder):
            os.mkdir(folder)
        
        self.filePath = filePath
        self.data = data
        
    def saveToFile(self):
        with open(self.filePath, 'wb') as outf:
            pickle.dump(self.data, outf)
            
    def readFromFile(self):
        with open(self.filePath, 'rb') as inf:
            self.data = pickle.load(inf)

# written by Giulio Piacentino, giulio@mcneel.com
def TreeToList(input, RetrieveBase = lambda x: x[0]):
    """Returns a list representation of a Grasshopper DataTree"""
    def extend_at(path, index, simple_input, rest_list):
        target = path[index]
        if len(rest_list) <= target: rest_list.extend([None]*(target-len(rest_list)+1))
        if index == path.Length - 1:
            rest_list[target] = list(simple_input)
        else:
            if rest_list[target] is None: rest_list[target] = []
            extend_at(path, index+1, simple_input, rest_list[target])
    all = []
    for i in range(input.BranchCount):
        path = input.Path(i)
        extend_at(path, 0, input.Branch(path), all)
    return RetrieveBase(all)

def process_list(_func, _list):
    return map( lambda x: process_list(_func, x) if type(x)==list else _func(x), _list )

def rhLineCurveToMSLine(item):
    if type(item) == rc.Geometry.LineCurve:
        item = item.Line
    msStartPt = MSPoint(item.FromX, item.FromY, item.FromZ)
    msEndPt = MSPoint(item.ToX, item.ToY, item.ToZ)
    return MSLine(msStartPt, msEndPt)

def rhPolyLineToMSPolyLine(item):
    if type(item) == rc.Geometry.PolylineCurve:
        if item.IsPolyline():
            item = item.TryGetPolyline()[1]
    segments = []
    for i in range(0, item.SegmentCount,1):
        line = item.SegmentAt(i)
        segments.append(rhLineCurveToMSLine(line))
    return MSPolyLine(segments)

def rhArcCurveToMSArc(item):
    if type(item) == rc.Geometry.ArcCurve:
        item = item.Arc
    startPoint = MSPoint(item.StartPoint.X, item.StartPoint.Y, item.StartPoint.Z)
    centerPoint = MSPoint(item.Center.X, item.Center.Y, item.Center.Z)
    endPoint = MSPoint(item.EndPoint.X, item.EndPoint.Y, item.EndPoint.Z)
    return MSArc(startPoint, centerPoint, endPoint)

def rhNurbsCurveToMSNurbsCurve(item):
    msControlPoints = []
    for pt in item.Points:
        msControlPoints.append(MSPoint4d(pt.Location.X, pt.Location.Y, pt.Location.Z, pt.Weight))
    knots = []
    for i in range(0, item.Knots.Count, 1):
        knots.append(item.Knots[i])
    # weights information is stored in control points
    weights = None
    return MSNurbsCurve(msControlPoints, weights, knots, item.Degree)

def rhMultiSpanNurbsCurveToMSNurbsCurve(item):
    rhSubCurve = []
    msCurves = []
    for i in range(0, item.SpanCount, 1):
        rhCurveSubdomain = item.SpanDomain(i)
        rhSubCurve.append(item.ToNurbsCurve(rhCurveSubdomain))
    for curve in rhSubCurve:
        msCurves.append(rhNurbsCurveToMSNurbsCurve(curve))
    return MSMultiSpanNurbsCurve(msCurves)

def rhPointToMSPoint(item):
    if type(item) == rc.Geometry.Point:
        return MSPoint(item.Location.X, item.Location.Y, item.Location.Z)
    elif type(item) == rc.Geometry.Point3d:
        return MSPoint(item.X, item.Y, item.Z)

def rhEllipseToMSEllipse(item):
    msVector = MSVector(item.Plane.Normal.X,item.Plane.Normal.Y, item.Plane.Normal.Z) 
    msOrigin = MSPoint(item.Plane.Origin.X, item.Plane.Origin.Y, item.Plane.Origin.Z)
    msPlane = MSPlane(msOrigin, msVector)
    return MSEllipse(msPlane, item.Radius1, item.Radius2)

def rhCircleToMSCircle(item):
    msVector = MSVector(item.Normal.X,item.Normal.Y, item.Normal.Z)
    msOrigin = MSPoint(item.Center.X, item.Center.Y, item.Center.Z)
    msPlane = MSPlane(msOrigin, msVector)
    return MSCircle(msPlane, item.Radius)

def rhPolyCurveToMSPolyCurve(item):
    msSubCurves = []
    segmentCount = item.SegmentCount
    for i in range(0, segmentCount):
        curve = item.SegmentCurve(i)
        if type(curve) == rc.Geometry.LineCurve or type(curve) == rc.Geometry.Line:
            msSubCurves.append(rhLineCurveToMSLine(curve))
        elif type(curve) == rc.Geometry.Arc:
            msSubCurves.append(rhArcCurveToMSArc(curve))
        elif type(curve) == rc.Geometry.ArcCurve and curve.IsArc() == True:
            msSubCurves.append(rhArcCurveToMSArc(curve))
        elif type(curve) == rc.Geometry.PolylineCurve or type(curve) == rc.Geometry.Polyline:
            msSubCurves.append(rhPolyLineToMSPolyLine(curve))
        elif type(curve) == rc.Geometry.NurbsCurve:
            msSubCurves.append(rhNurbsCurveToMSNurbsCurve(curve))
    msPolyCurve = MSPolyCurve(msSubCurves)
    return msPolyCurve

def rhMeshToMSMesh(item):
    msFaces = []
    for i in range(0, item.Faces.Count):
        face = item.Faces.Item[i]
        if face.IsQuad:
            msFaces.append(MSMeshFace(face.A, face.B, face.C, face.D))
        else:
            msFaces.append(MSMeshFace(face.A, face.B, face.C))
        msPoints = []
        for i in range(0, item.Vertices.Count, 1):
            msPoints.append(MSPoint(item.Vertices.Item[i].X, item.Vertices.Item[i].Y, item.Vertices.Item[i].Z))
    return MSMesh(msPoints, msFaces)

def rhNurbsSurfaceToMSNurbsSurface(item):
    msControlPoints = []
    for pt in item.Points:
        msControlPoints.append(MSPoint4d(pt.Location.X, pt.Location.Y, pt.Location.Z, pt.Weight))
        # since weights in Rhino are stored in points 
        # they will be extracted from MSPoint4d
    weights = None
    knotsU = []
    for i in range(0, item.KnotsU.Count, 1):
        knotsU.append(item.KnotsU[i])
    knotsV = []
    for i in range(0, item.KnotsV.Count, 1):
        knotsV.append(item.KnotsV[i])
    return MSNurbsSurface(msControlPoints, weights, knotsU, knotsV, item.OrderU, item.OrderV, item.SpanCount(0), item.SpanCount(1), item.IsRational)



def rhBrepToMSPolySurface(item):
    msSurfaces = []
    brepFaces = item.Faces
    for i in range(0, brepFaces.Count, 1):
        rhSurface = brepFaces.Item[i].UnderlyingSurface()
        if type(rhSurface) == rc.Geometry.NurbsSurface:
            msSurfaces.append(rhNurbsSurfaceToMSNurbsSurface(rhSurface))
    return MSPolySurface(msSurfaces)

def tryExplode(item):
    try:
        return list(item.Explode())
    except:
        return [item]

def rhBrepToMsBrep(item):
    msFaces = []
    faces = item.Faces
    joinedCurves = [[] for i in range(faces.Count)]
    for index, face in enumerate(faces):
        if face.IsSurface:
            msFaces.append(rhNurbsSurfaceToMSNurbsSurface(face.ToNurbsSurface()))
        else:
            msFaces.append(rhNurbsSurfaceToMSNurbsSurface(face.UnderlyingSurface().ToNurbsSurface()))
            faceLoops = face.Loops
            for loop in faceLoops:
                trims = loop.Trims
                trimLoop = []
                for trim in trims:
                    if trim.TrimType != rc.Geometry.BrepTrimType.Seam:
                        edgeIndex = trim.Edge.EdgeIndex
                        edge = item.Edges.Item[edgeIndex]
                        trimLoop.append(edge.DuplicateCurve())
                joinedCurves[index].extend(rc.Geometry.Curve.JoinCurves(trimLoop))
    explodedCrvs = process_list(tryExplode, joinedCurves)
    msTrimCurves = process_list(toMSObject, explodedCrvs)
    msBrep = MSBrep(msFaces,msTrimCurves)
    print(msFaces)
    return msBrep

def toMSObject(item):
    if type(item) == rc.Geometry.Point3d or type(item) == rc.Geometry.Point:
        return rhPointToMSPoint(item)
    elif type(item) == rc.Geometry.LineCurve:
        return rhLineCurveToMSLine(item)
    elif type(item) == rc.Geometry.PolyCurve and item.IsPolyline() == True:
        return rhPolyLineToMSPolyLine(item)
    elif type(item) == rc.Geometry.Polyline:
        return rhPolyLineToMSPolyLine(item)
    elif type(item) == rc.Geometry.NurbsCurve and item.IsClosed == True:
        if item.IsEllipse() == True:
            item = item.TryGetEllipse()[1]
            return rhEllipseToMSEllipse(item)
        elif item.IsCircle() == True:
            item = item.TryGetCircle()[1]
            return rhCircleToMSCircle(item)
        else:
            pass
    if type(item) == rc.Geometry.ArcCurve and item.IsCircle() == True:
        item = item.TryGetCircle()[1]
        return rhCircleToMSCircle(item)
    elif type(item) == rc.Geometry.ArcCurve and item.IsArc() == True:
        item = item.TryGetArc()[1]
        return rhArcCurveToMSArc(item)
    elif type(item) == rc.Geometry.NurbsCurve and item.SpanCount == 1:
        return rhNurbsCurveToMSNurbsCurve(item)
    elif type(item) == rc.Geometry.NurbsCurve and item.SpanCount > 1:
        return rhMultiSpanNurbsCurveToMSNurbsCurve(item)
    elif type(item) == rc.Geometry.PolyCurve:
        return rhPolyCurveToMSPolyCurve(item)
    elif type(item) == rc.Geometry.Mesh:
        return rhMeshToMSMesh(item)
    #elif type(item) == rc.Geometry.Brep:
        #if tryGetPolySurface(item) == True:
            #return rhBrepToMSPolySurface(item)
        #else:
            #pass
    if type(item) == rc.Geometry.Brep:
        return rhBrepToMsBrep(item)
    elif type(item) == rc.Geometry.Brep and item.IsSurface == True:
        item = item.Faces[0].ToNurbsSurface()
        return rhNurbsSurfaceToMSNurbsSurface(item)
    else:
        return MSData(item)


def tryGetPolySurface(item):
    isSurface = []
    brepFaces = item.Faces
    for i in range(0, brepFaces.Count, 1):
        if brepFaces.Item[i].IsSurface == True:
            isSurface.append(True)
        else:
            isSurface.append(False)
    if all(x == True for x in isSurface):
        return True
    else:
        return None

"""Transforms nestings of lists or tuples to a Grasshopper DataTree"""
"""Big thanks to Giulio Piacentino for this function"""
def list_to_tree(input, none_and_holes=False, source=[0]):
    def proc(input,tree,track):
        path = GH_Path(Array[int](track))
        if len(input) == 0 and none_and_holes: tree.EnsurePath(path); return
        for i,item in enumerate(input):
            if hasattr(item, '__iter__'): #if list or tuple
                track.append(i); proc(item,tree,track); track.pop()
            else:
                if none_and_holes: tree.Insert(item,path,i)
                elif item is not None: tree.Add(item,path)
    if input is not None: t=DataTree[object]();proc(input,t,source[:]);return t

geometryList = TreeToList(_geometry)

if _export:
    #geometryOut = process_list(rhBrepToMsBrep, geometryList)
    geometryOut = process_list(toMSObject, geometryList)
    print(geometryOut)
    geometryOut.insert(0, MSData(sc.doc.ModelUnitSystem.ToString()))
    try:
        serializer = SerializeObjects(_filePath, geometryOut)
        serializer.saveToFile()
        warnType = gh.GH_RuntimeMessageLevel.Remark
        msg = "File is exported to " + _filePath + "Now you can use Dynamo to import the file."
    except Exception, e:
        warnType = gh.GH_RuntimeMessageLevel.Warning
        msg = "Failed to export: \n" + `e`
else:
    msg = "Export set to false."

ghenv.Component.AddRuntimeMessage(warnType, msg)


#geometryOut = process_list(rhBrepToMsBrep, geometryList)
#a = list_to_tree(geometryOut)
