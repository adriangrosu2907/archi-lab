# Copyright(c) 2015, Konrad K Sobon
# @arch_laboratory, http://archi-lab.net

# Import Element wrapper extension methods
import clr
clr.AddReference("RevitNodes")
import Revit
clr.ImportExtensions(Revit.Elements)

# Import RevitAPI
clr.AddReference("RevitAPI")
import Autodesk
from Autodesk.Revit.DB import *

# Import DocumentManager and TransactionManager
clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
doc = DocumentManager.Instance.CurrentDBDocument

#The inputs to this node will be stored as a list in the IN variables.
dataEnteringNode = IN

def ProcessList(_func, _list):
	return map(lambda x: ProcessList(_func, x) if type(x)==list else _func(x), _list)

def TryGetAssetId(mat):
	doc = DocumentManager.Instance.CurrentDBDocument
	appearanceId = mat.AppearanceAssetId
	if appearanceId != ElementId.InvalidElementId:
		appearanceElemn = doc.GetElement(appearanceId)
		return appearanceElemn
	else:
		return ElementId.InvalidElementId

def Unwrap(item):
	return UnwrapElement(item)

if isinstance(IN[0], list):
	elements = ProcessList(Unwrap, IN[0])
else:
	elements = [Unwrap(IN[0])]
	
#Assign your output to the OUT variable.
OUT = ProcessList(TryGetAssetId, elements)
