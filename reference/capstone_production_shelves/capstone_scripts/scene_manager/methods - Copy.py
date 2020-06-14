from pymel.core import *
from pymel.util import *

from scene_manager.metaCore import *
from scene_manager.gui import *
import scene_manager.metaUtil as mu
import maya.mel as mel
import maya.cmds as mc
import random
import string


###################################################################
#                   META 
###################################################################



def addAnimAttr(obj):
    '''
        adds the .animNode attr to the object
        .animNode attribute will return the name of this node
        
        obj:
            the object to add the .animNode attribute to
    '''
    if not objExists(obj):
        printError("addAnimAttr: object %s doesn't exist"%obj)
    obj = PyNode(obj)
    
    """
    # Joint type restriction removed for greater flexibility of the AnimGroup meta node.
    if not obj.type() == 'joint':
        printError('addAnimAttr: anim Node, $s, has to be a joint'%s)
    """

    obj.addAttr('animNode', at='message')
    
def hasAnimAttr(obj):
    '''
        if obj has the .animNodeAttr return True 
        else false
        
        obj:
            node to test
    '''
    obj = PyNode(obj)
    if obj.hasAttr("animNode"):
        return 1
    return 0
    


    
    
###########################################################################
#                       ERRORS / WARNINGS / DEBUGGING
###########################################################################        

    
def printError(s):
    '''
    prints error with string as printed text
    '''
    raise Exception(str(s))


def printWarning(s):
    '''
    prints an error with the string as warning text
    '''
    import maya.mel as mel
    mel.eval('warning "%s" ;'%s)
    
    
    
    
    
###########################################################################
#                         Utilities
###########################################################################
def chainBetween(start, end):
    '''
    get all the nodes between start obj and end obj
    
    start:
    
    end:
    
    return:
        a list of all objects between start obj and end obj
        if end is not an ancestor of start, returns a list containing start    
    '''
    if not objExists(start):
        printError("chainBetween: object %s doesn't exist"%start)
    if not objExists(end):
        printError("chainBetween: object %s doesn't exist"%end)
    
    start = PyNode(start)
    end = PyNode(end)
    
    chainList = [start.longName()]
    
    if start.longName() == end.longName():
        return [start]
    
    path = start
    rest = end.longName().replace(start.longName(), '', 1)
    if rest == end.longName():
        printError("chainBetween: %s isn't an ancestor of %s"%(end.name(), start.name()) )
    objList = rest.split('|')
    for obj in objList:
        if obj:
            path = path + "|" + obj
            chainList.append(path)
            
    return chainList
    
def distanceBetween(node1, node2):    
    '''
    returns the distance between node1 and node2
    
    node1,node2:
        nodes to determine distance
    
    return:
        a float giving the distance
    '''
    if not objExists(node1):
        printError("distanceBetween: node %s doesn't exist"%node1)
    if not objExists(node2):
        printError("distanceBetween: node %s doesn't exist"%node2)
    
    t1 = xform(node1, q=1, ws=1, t=1)
    t2 = xform(node2, q=1, ws=1, t=1)
        
    distance = sqrt( pow(t2[0]-t1[0], 2) + pow(t2[1]-t1[1], 2) + pow(t2[2]-t1[2], 2) )
    return distance

def createTemplateLine(startNode, endNode):
    '''
    creates a templated line between startNode and endNode
    
    startNode, endNode:
        nodes which will control the ends of the templated line
        
    return:
        the node of the curve
    '''
    sel = ls(sl =1)

    pos1 = xform(startNode, q=1, ws=1, t=1)
    pos2 = xform(endNode, q=1, ws=1, t=1)    

    c = curve(d=1, p = ([pos1, pos2]), n = "createTemplateLine")
    c = PyNode(c)
    
    c.scalePivot.set(pos1)
    c.rotatePivot.set(pos1)

    c1buffer = cluster(c.name() + '.cv[0]', n = "createTemplateLineFirstCluster")
    c1Handle = c1buffer[1]
    parent(c1Handle, startNode)
    c1Handle.visibility.set(0)

    c2buffer = cluster(c.name() + '.cv[1]', n = "createTemplateLineSecondCluster")
    c2Handle = c2buffer[1]
    parent(c2Handle, endNode)
    c2Handle.visibility.set(0)
    
    c.overrideEnabled.set(1)
    c.overrideDisplayType.set(1)
    
    select(clear =1)
    if sel:    
        select(sel)
    return c;

def alignPointOrient(source, target, point, orient):    
    '''
    aligns the source object to the target obj by point and orient
    
    source:
        obj wishing to copy from
        
    target:
        obj wishing to copy to
        
    point:
        if true, will match translation
        
    orient:
        if true will match rotation
    '''    
    if not objExists(source):
        printError("alignPointOrient:  can't find source node %s:"%source)
    if not objExists(target):
        printError("alignPointOrient:  can't find target node %s:"%target)
    
    target = PyNode(target)
    source = PyNode(source)
        
    dup = duplicate(target, rc = 1)[0]
    
    axes = ["tx", "ty", "tz", "rx", "ry", "rz"]
    locked = []
    set = []
    
    for inc in xrange(len(axes)): 
        if target.attr(axes[inc]).isSettable():
            set.append('none')
            locked.append(0)
        else:
            set.append(axes[inc].replace('t','').replace('r',''))
            locked.append(1)

    if(point):
        parentConstraint(source, dup, st=(set[0],set[1],set[2]), sr=("x","y","z"), mo=0)
    if(orient): 
        parentConstraint(source, dup,sr=(set[3],set[4],set[5]),st=("x","y", "z"), mo=0)

    for inc in xrange(len(axes)):
        if not locked[inc]:
            value = dup.attr(axes[inc]).get()
            target.attr(axes[inc]).set(value)

    delete(dup)
    
def createCurveThroughObjects(objects, degree=None, offset=None):
    '''
    creates a curve the goes through all the objects in the list given from start to finish
    
    objects:
        List of objects to weave curve through, goes in order.
    
    degree:
        Degree of the output curve.
        
    offset:
        Offset in local space from each given object in which a CV should be created.
        
    return:
        The curve transform object created.
    '''
    for obj in objects:
        if not objExists(obj):
            printWarning("createCurveThroughObjects: object %s doesn't exist"%obj)
            return None
    objects = map(lambda x: PyNode(x), objects)
    
    if not degree:
        degree = len(objects)-1
    if degree <= 0:
        printWarning('createCurveThroughObjects: less than two objects given')
        return None
        
    points = []
    for obj in objects:
        if (offset == None):
            pnt = obj.getTranslation(space = 'world')
        else:
            pnt = mu.getWorldPositionVector(obj, offset)
        points.append(pnt)
        
    newCurve = curve(d=degree, p=points)

    return newCurve

def makeCurveUniform(curv):
    '''
    make curve have evenly spaced CVs and EPs 
    curv:
        curve to change
    '''
    curv = PyNode(curv)
    spans = curv.numSpans()
    degrees = curv.degree()
    rebuildCurve(curv, kep=1, end=0, ch=1, rt=0, kr=0, s = spans, d= degrees)
    
    
def attachToCurve(curv, obj, percent,point=1,orient=1):
    '''
    attaches the object to the curve at given percent, 
    locator on curve which aim constraints obj
    if orient, +x will point down curve
    curv:
        curve to attach to
    obj:
        object to be attached
    percent:
        where to connect by percent, values from 0.0 - 1.0
    return:
        [PointOnCurve , locator]
    '''
    if not objExists(curv):
        raise Exception("attachToCurve: curve given, %s , doesn't exist"%curv)
    curv = PyNode(curv)
    if not objExists(obj):
        raise Exception("attachToCurve: object given, %s, doesn't exists"%obj)
    obj = PyNode(obj)
    if percent > 1 or percent < 0:
        raise Exception("attachToCurve: percent given need to be between 0.0 - 1.0")
    
    #create point on curve Node    
    poc = pointOnCurve(curv, ch=1)
    poc = PyNode(poc)
    poc.turnOnPercentage.set(1)
    poc.parameter.set(percent)
    
    
    #attach obj
    
    
    axes = ["tx", "ty", "tz", "rx", "ry", "rz"]
    locked = []
    set = []
    
    for inc in xrange(len(axes)): 
        if obj.attr(axes[inc]).isSettable():
            set.append(1)
        else:
            set.append(0)

    #point
    if point:        
        if set[0]:
            poc.positionX >>  obj.translateX
        if set[1]:
            poc.positionY >>  obj.translateY
        if set[2]:
            poc.positionZ >>  obj.translateZ
    
    #orient
    locator = None
    if orient:
        locator = spaceLocator()
        add = createNode('plusMinusAverage')
        poc.position >> add.input3D[0]
        poc.normalizedTangent >> add.input3D[1]
        add.output3D >> locator.translate
        
        if set[3]:
            set[3] = 'none'
        else:
            set[3] = 'x'
        if set[4]:
            set[4] = 'none'
        else:
            set[4] = 'y'
        if set[5]:
            set[5] = 'none'
        else:
            set[5] = 'z'
            
            
        aimConstraint( locator, obj, mo= 0, offset= [0, 0, 0], weight= 1,skip=[set[3], set[4], set[5]],  aimVector =[ 1, 0, 0], upVector= [0, 1, 0], worldUpType= "vector", worldUpVector =[0, 1, 0]);
            
    return poc , locator
    
    
def allowSafeScale(startJoint, endJoint):
    '''
    will allow the joint chain to have stretchy by scaling without accidently scaling child joints.
    startJoint:
        the starting joint
    endJoint:
        the ending joint 
    return:
        None
    '''
    
    chain_joints = map(lambda x: PyNode(x), chainBetween(startJoint, endJoint))
    for cj in chain_joints:
        for child in cj.getChildren():
            if child.type() == 'joint':
                cj.scale >> child.inverseScale
    
def randomizeVerts(obj, rand = [1,1,1]):
    '''
    randomizes all the verts of an object
    obj:
        the object whose verts to randomize
    rand:
        the amount to randomize by: offest by amount eiher positive or negative directions
    return:
        None
    '''
    randAmountX = rand[0]
    randAmountY = rand[1]
    randAmountZ = rand[2]
    obj = PyNode(obj)
    numVerts = obj.numVertices()
    for inc in xrange(numVerts):
        posx,posy,posz = obj.vtx[inc].getPosition()
        randx = random.random()*randAmountX*2-randAmountX
        randy = random.random()*randAmountY*2-randAmountY
        randz = random.random()*randAmountZ*2-randAmountZ
        obj.vtx[inc].setPosition([posx+randx,posy+randy,posz+randz])
    
    
    
########################################################################################
#                            RIGGING
########################################################################################

def createJointsOnNurbs(nurbs, u = .5, v = .5):
    
    """
    creates a controler locator which will drive a joint connected to a nurbs surface
    
    nurbs:
        nurbs surface to attach joint
    
    u:    
        joints inital u parameter on the nurbs
    v:
        joints initial v parameter on the nurbs
        
    return:
        return[baseJoint,tipJoint,baseLoc,controlLoc,PointOnSurfaceInfo,
            pointOnSurfaceOutputGrp]    
    """
    
    #pointOnSurface
    surfacePoint = PyNode(pointOnSurface(nurbs,ch=1, u = u, v = v))
    
    #pointGrp
    pointGrp = group(em=1, n = 'translate_group')
    surfacePoint.position >> pointGrp.translate
    normalConstraint(nurbs, pointGrp, aim = [1,0,0], upVector = [0,1,0], worldUpObject = nurbs, worldUpType = 'objectRotation')

    #joints
    select(cl=1)
    baseJoint = joint( p = [0,0,0], n = 'base_control_joint')
    tipJoint = joint(p = [0,1,0], n = 'tip_control_joint')
    joint(baseJoint, e=1, zso=1, oj = 'xyz', sao = 'yup')
    pointConstraint(pointGrp, baseJoint, mo=0)
    orientConstraint(pointGrp, baseJoint, mo=0)
    
    #controls
    baseLoc = spaceLocator(p = [0,0,0], n = 'base_locator')
    controlLoc = spaceLocator(p = [0,0,0], n = "tip_locator")
    baseLoc | controlLoc
    
    baseLoc.getShape().overrideEnabled.set(1)
    baseLoc.getShape().overrideDisplayType.set(1)
    transformLimits(controlLoc, tx = [0,1], etx = [1,1], ty = [0,1], ety = [1,1],tz = [0,0], etz = [0,0])
    controlLoc.translate.set([.5,.5,0])
    lockAndHideAttrs(controlLoc, ['tz', 'rx', 'ry','rz', 'sx', 'sy','sz', 'v'])

    #connect To pointOnSurface
    controlLoc.tx >> surfacePoint.parameterU
    controlLoc.ty >> surfacePoint.parameterV
    
    return[baseJoint,tipJoint,baseLoc,controlLoc,surfacePoint,pointGrp]
    
    
def splitJoint(numSplits,startJoint, endJoint = None):
    """
    splits given joint into multiple joints along the same line
    numSplits:
        the number of new joints
    startJoints:
        the joint to be split
    endJoint:
        if startjoint has multiple children, specifies which child
    return:
        a list of all the joints in the chain including the start and end joint.
    """

    #error testing
    if (not endJoint == None) and (not objExists(endJoint)):
        raise Exception("splitJoint: endJoint, %s, doesn't exists"%endJoint)
    if not endJoint == None:
        endJoint = PyNode(endJoint)
    if not objExists(startJoint):
        raise Exception("splitJoint: obj given, %s, is doesn't exist."%(joint))
    
    base = PyNode(startJoint)
    if not base.type() == 'joint':
        raise Exception("splitJoint: obj given, %s, is not a joint."%(joint))
    
    #find child
    tip = None
    numChildJoint = 0
    tips = base.getChildren()
    for obj in tips:
        if obj.type() == 'joint':
            numChildJoint += 1
            tip = obj
        

    #error test endJoint
    if numChildJoint > 1 and endJoint == None:
        raise Exception('splitJoint: more than one child joint, please specify endJoint')
    elif (not endJoint == None)  and (not endJoint in tips):
        raise Exception('splitJoint: %s is not a child of %s'%(endJoint, joint))
    if (not endJoint == None) and not endJoint.type() == 'joint':
        raise Exception('splitJoint: endJoint, %s is not of type joint'%endJoint)    

    if not endJoint == None:
        tip = endJoint
    
    #error testing num
    if numSplits < 1:
        raise Exception('splitJoint: can not split joint less than 1 time')

    #find the vector between the joint and child
    base_pos = base.getTranslation(space = 'world')[0:3]
    tip_pos = tip.getTranslation(space = 'world')[0:3]
    vector = (tip_pos[0]- base_pos[0] , tip_pos[1]- base_pos[1] ,  tip_pos[2]- base_pos[2])
    divVector = map(lambda x: x/(numSplits+1), vector)
    curJoint = base
    newJoint = None
    allinChain = [base]
    for inc in xrange(numSplits):
        select(cl=1)
        inc = inc +1
        newPos = ((base_pos[0] + divVector[0]*inc), (base_pos[1] + divVector[1]*inc), (base_pos[2] + divVector[2]*inc))    
        newJoint = joint(p=newPos)
        parent(newJoint,curJoint)
        joint(curJoint, e=1, zso=1, oj= 'xyz', sao='yup')
        allinChain.append(newJoint)
        curJoint = newJoint    
    #finish parenting and orienting
    parent(tip, curJoint)
    joint(newJoint, e=1, zso=1, oj='xyz', sao='yup')
    allinChain.append(tip)
        
    return allinChain        
        

def createTemplateLine(startNode, endNode):
    '''
    creates a templated line between startNode and endNode
    
    startNode, endNode:
        nodes which will control the ends of the templated line
        
    return:
        the node of the curve
    '''
    sel = ls(sl =1)

    pos1 = xform(startNode, q=1, ws=1, t=1)
    pos2 = xform(endNode, q=1, ws=1, t=1)    

    c = curve(d=1, p = ([pos1, pos2]), n = "createTemplateLine")
    c = PyNode(c)
    
    c.scalePivot.set(pos1)
    c.rotatePivot.set(pos1)

    c1buffer = cluster(c.name() + '.cv[0]', n = "createTemplateLineFirstCluster")
    c1Handle = c1buffer[1]
    parent(c1Handle, startNode)
    c1Handle.visibility.set(0)

    c2buffer = cluster(c.name() + '.cv[1]', n = "createTemplateLineSecondCluster")
    c2Handle = c2buffer[1]
    parent(c2Handle, endNode)
    c2Handle.visibility.set(0)
    
    c.overrideEnabled.set(1)
    c.overrideDisplayType.set(1)
    
    select(clear =1)
    if sel:    
        select(sel)
    return c;
    
    

def addBoxToJoint(jointName, width =1):
    '''
    adds a shape node to the joint which matches the joints current size
    
    jointName:
        the joint which will get a shape node
        
    width:
        the width of the box to be added
        
    return:
        the name of the shape node, if no shape node added returns none
    '''
    if not objExists(jointName):
        printError("addBoxToJoint: joint node %s: doesn't exists"%jointName)
        
    jointNode = PyNode(jointName)
    
    if not jointNode.type() == 'joint':
        printError("addBoxToJoint: node, $s ,is not a joint"%jointName)
        
    child = jointNode.getChildren(type = 'joint')
    
    if not child:
        printWarning('addBoxToJoint: joint %s has no children'%jointName)
        return None
        
    child = child[0]
    cube = polyCube(n="%s_box"%jointNode.name(), w=1, d=width, h=width, ch=1)[0]
    alignPointOrient(jointNode, cube, 1,1)
    
    transX = child.translateX.get()
    
    appendShape(cube, jointNode)
    delete(cube)
    shapeNode = jointNode.getShape()
    scale(shapeNode.vtx[:], transX, 1,1, r=1)
    move(shapeNode.vtx[:], transX/2, 0,0, r=1, os=1)
    
    return shapeNode

    
def lockAndHideAttrs(obj, attrList):
    '''
    locks and hides attributes on an object,
    
    obj:
        object node which contains the attributes
        
    attrs:
        a list of attributes to lock and hide

    '''
    if not objExists(obj):
        printError("object $s doesn't exist"%obj)
    obj = PyNode(obj)
    
    for attr in attrList:
        if not obj.hasAttr(attr):
            printWarning('lockAndHideAttrs: object %s has not attribute %s'%(obj, attr))
        else:
            # Break apart compound attributes (e.g. translate, rotate, scale)
            if obj.attr(attr).isCompound():
                attrsToProcess = obj.attr(attr).getChildren()
            else:
                attrsToProcess = [obj.attr(attr)]
            
            # Lock and hide
            for attrObj in attrsToProcess:
                if not attrObj.isLocked():
                    attrObj.set(lock=1)
                if not attrObj.isHidden():
                    attrObj.set(keyable=0, cb=0)    
            

def resetAttrs(obj):
    '''
    resets the attrs of the obj which are in the Channel Box
    all dynamic attributes are set to their default value,
    scale and visibilities if present are set to 1
    all others are set to 0
    
    obj:
        the object whos attrs will be changed            
    '''
    if not objExists(obj):
        printError("resetAttrs: object, %s, doesn't exist"%obj)
        
    obj = PyNode(obj)
    attrs = obj.listAttr(keyable = 1)
    special  = {obj.sx:1, obj.sy:1, obj.sz:1, obj.v:1}
    
    for attr in attrs:
        if not attr.isLocked():
            if attr.isDynamic():
                dynValue = addAttr(attr, q=1, dv=1)
                attr.set(dynValue)
            elif attr in special.keys():
                attr.set(special[attr])
            else:
                attr.set(0)

def duplicateChain(startObj, endObj, searchFor = '', replaceWith = ''):
    """
    duplicates the chain from start to end and renames the new chain
    will rename all the objs with a unique name
    duplicates then renames obj, can search for and replace string in name
    keeps all shape nodes even if not in direct chain
    
    startObj
        start of the obj chain wishing to duplicate
    
    endObj
        end of the obj chain wishing to duplicate
        
    searchfor:
        tag in the name that will be replaces
        if searchFor == None then will add suffix "_duplicateObj"
        
    replaceWith:
        the tag to replace with 
        
    return:
        a list of the new Chain
        doesn't contain the shapes of the objs unless directly in the original chain
    """
    if not objExists(startObj):
        printError("duplicateChain: start object, %s, doesn't exist"%startObj)    
    if not objExists(endObj):
        printError("duplicateChain: end object, %s, doesn't exist"%endObj)    
    
        
    chain = chainBetween(startObj, endObj)
    newChain = []
    objParent = None
    newNames = []
    for x in chain:
        newNames.append(PyNode(x).name().replace(searchFor, replaceWith))
        
    for num in xrange(len(chain)):
        obj = PyNode(chain[num])
        newName = obj.name() + "_duplicateObj"
        if searchFor:
            newName= newNames[num]
        newObj = duplicate(obj, n= newName)[0]
        newChain.append(newObj)
        newChildren = newObj.getChildren()
        newShape = newObj.getShape()
        for child in newChildren:
            if not (child == newShape or child in chain):
                delete(child)
        if objParent:
            parent(newObj, objParent)
        objParent = newObj
            
    if newChain[0].getParent():
        parent(newChain[0], w=1)
    
    return newChain

def getJointLabels(joint):
    '''
    returns joint FKIK labeling for the joints
    
    joint:
        a joint with FKIK labels
        
    return:
        a list containing he side and type
        [side, type]
    '''

    if not objExists(joint):
        printError("getJointLabels: joint, %s , doesn't exists"%joint)
        
    joint = PyNode(joint)
    if not joint.type().lower() == 'joint':
        printError("getJointLabels: obj, %s, is not a joint"%joint)
        
    jointSideEnums = {    0:"Center",
                        1:"Left",
                        2:"Right",
                        3:"None"}
                    
    jointLabelEnums = {    0:"None",
                        1:"root",
                        2:"hip",
                        3:"knee",
                        4:"foot",
                        5:"toe",
                        6:"spine",
                        7:"neck",
                        8:"head",
                        9:"collar",
                        10:"shoulder",
                        11:"elbow",
                        12:"hand",
                        13:"finger",
                        14:"thumb",
                        15:"propA",
                        16:"propB",
                        17:"propC",
                        18:"other",
                        19:"index finger",
                        20:"middle finger",
                        21:"ring finger",
                        22:"pinky finger",
                        23:"extra finger",
                        24:"big toe",
                        25:"index toe",
                        26:"middle toe",
                        27:"ring toe",
                        28:"pinky toe",
                        29:"extra toe"}    
                        
    sideNum = joint.side.get()
    labelNum = joint.attr('type').get()
    if labelNum == 18:
        typeLabel = joint.otherType.get()
        return(jointSideEnums[sideNum], typeLabel) 
    return (jointSideEnums[sideNum],jointLabelEnums[labelNum])     

def appendShape(fromObj, toObj):
    '''
    copies the shape from one object to other
    
    fromObj:
        object to copy the shape from
        
    toObj:
        object to paste the shape to
        
    return:
        the new Shape
    '''    

    if not objExists(fromObj):
        printError("appendShape: object , %s , doesn't exist"%fromObj)
    if not objExists(toObj):
        printError("appendShape: object , %s , doesn't exist"%toObj)
        
    fromObj = PyNode(fromObj)
    toObj = PyNode(toObj)
    
    shape = fromObj.getShape()
    if shape:
        parent(shape, toObj, add=1, s=1)
        return toObj.getShape()
    else:
        return None
    
def createPVLocator(startJoint, midJoint, endJoint):
    '''
    creates and places/orients a locator where the poleVector object should be by defualt

    startJoint:
        the root of the chain
      
    midJoint:
        the center joint of the chain
      
    endJoint:
        the last joint in the ik chain  
  
    return:
        the locator created
  
    '''
    startJoint = PyNode(startJoint)
    midJoint = PyNode(midJoint)
    endJoint = PyNode(endJoint)

    startPos = startJoint.getTranslation(space= 'world')
    midPos = midJoint.getTranslation(space= 'world')
    endPos = endJoint.getTranslation(space= 'world')
      
    #find projection of start_mid vector onto start_end vector
    start_end_vector = endPos - startPos
    start_mid_vector = endPos - midPos
  
    q = start_end_vector
    u = start_mid_vector
  
    #projection(vector) = (u dot q)/||q|| * (q / ||q||)
    projection = (q.dot(u)/q.length()) * (q/q.length())
    midPoint = endPos - projection
  
    select(cl=1)
    projJoint = joint()
    projJoint.setTranslation(midPoint, ws=1)
    projJoint2 = joint()
    projJoint2.setTranslation(midPos, ws=1)

    projMag = (midPos - midPoint).length()      
    joint(projJoint, e=1, oj = 'xyz', sao ='xup')
    dist1 = distanceBetween(startJoint, midJoint)
    dist2 = distanceBetween(midJoint, endJoint)
    if round(projMag, 5):# vector from the proj to mid joint magnitude
        projJoint2.tx.set(max(dist1, dist2))
    else:
        projJoint2.tx.set(0)  

    loc = spaceLocator()
    loc.setTranslation(projJoint2.getTranslation(ws=1), ws=1)  

    delete(projJoint)
    return loc
        
def createZeroedOutGrp(obj):
    '''
    groups the object to itself, the new group will contain all the information so resetting attrs will bring the obj to its current position
    
    obj:
        obj wishing to zero out
        
    return:
        the new group created
    '''

    if not objExists(obj):
        printError("CreateZeroedOutGrp: object, %s , doesn't exist"%obj)
    obj = PyNode(obj)
    
    select(cl=1)
    grp = group(obj, n = obj.name() + "_zero_grp")

    trans = obj.getTranslation(space = 'world')
    rot = obj.rotate.get()
    sc = obj.scale.get()
    
    resetAttrs(obj)
    opiv = xform(obj,q=1, ws=1, piv=1)[0:3]
    xform(grp, ws=1, piv=opiv)
    
    grp.setTranslation(trans, space = 'world')
    grp.rotate.set(rot)
    grp.scale.set(sc)

    return grp

    
def findClosestVertex(point, polys):
    '''
    find the closest vertex on the polygon object to the point
    
    point:
        the point [x,y,z]
        
    polys:
        a single or multiple polygonal objects
        
    return:
        the vertex closest to the point
    '''    

    objType = type(polys)
    if not objType == 'list' or not objType == "tuple":
        polys = [polys]

    minDist = -1
    bestVert = None
    for poly in polys:
        poly = PyNode(poly)
        numVerts = poly.numVertices()
        for vert in xrange(numVerts):
            vertex = PyNode('%s.vtx[%i]'%(poly.name(), vert))
            vertPoint = vertex.getPosition(space = 'world')
            distance = sqrt(pow(point[0] - vertPoint[0],2) + pow(point[1] - vertPoint[1],2) + pow(point[2] - vertPoint[2],2))
            if distance < minDist or minDist == -1:
                minDist = distance
                bestVert = vertex            
    return bestVert

    

def createNurbsOnVertex(vertex, width=5, height=5):
    """
    creates a nurbs plane on the vertex with axis matching vertex normal
    
    vertex:
        a polygonal vertex
        
    width:
        the width of the nurbs surface
    
    height:
        the height of the nurbs surface
            
    return:
        the new nurbs plane
    """

    normal = vertex.getNormal()
    point = vertex.getPosition(space = 'world')
    ratio = float(width)/height
    plane = nurbsPlane(ch=1,o=1,po=0, ax=normal, w=width,lr = ratio , p = point)[0]

    return plane

    
    
def getJointsByLabel(side, part):
    '''
    gets all joints whose side and label attributes match the given variables
    
    side: 
        side attr to match (center,left,right,none)
    part:
        label attr to match (ex. spine, neck, shoulder, ...) 
    
    return:
        all the joints with matching side and label attrs
    '''
    jointsWithType = []
    for j in ls(type = 'joint'):
        labels = getJointLabels(j)
        lside = labels[0]
        lpart = labels[1]
        if side.lower() == lside.lower() and lpart.lower() == part.lower():
            jointsWithType.append(j)
    return jointsWithType

def nurbsConstraint(nurbs, obj, u=0, v=0):
    '''
    attaches an object to the surface of the nurbs
    nurbs:
        the nurbs object to attach to
    obj:
        the object attaching to the nurbs
    u:
        the u value of the nurbs, 0-1 value
    v:
        the v value of the nurbs, 0-1 value
    return:
        a list of objects created in the process, [constraint, transform, pos]
    '''
    pos = PyNode(pointOnSurface( nurbs, ch = 1))
    pos.turnOnPercentage.set(1)
    pos.parameterU.set(u)
    pos.parameterV.set(v)
    nurbsMatrix = createNode('fourByFourMatrix', name = 'nurbsConstMatrix')#rename
    pos.normalizedNormalX >> nurbsMatrix.in20
    pos.normalizedNormalY >> nurbsMatrix.in21
    pos.normalizedNormalZ >> nurbsMatrix.in22
    pos.normalizedTangentUX >> nurbsMatrix.in10
    pos.normalizedTangentUY >> nurbsMatrix.in11
    pos.normalizedTangentUZ >> nurbsMatrix.in12
    pos.normalizedTangentVX >> nurbsMatrix.in00
    pos.normalizedTangentVY >> nurbsMatrix.in01
    pos.normalizedTangentVZ >> nurbsMatrix.in02
    pos.positionX >> nurbsMatrix.in30
    pos.positionY >> nurbsMatrix.in31
    pos.positionZ >> nurbsMatrix.in32
    transformGrp = group(empty = 1, name="%s_dummy"%obj)#rename
    constraint = PyNode(parentConstraint(transformGrp, obj, w=1))
    nurbsMatrix.output >> constraint.constraintParentInverseMatrix
    return [constraint, transformGrp, pos]    
    
def swapShape(anim, obj):
    '''
    swaps the shape object of the anim with the shape obj of the obj, note: deletes obj
    anim:
        the object that is getting the shapes swapped
    obj:
        the transform of the new shape
    '''
    oldShape = anim.getShape()
    newShape =  obj.getShape()
    

    #match rotate order
    obj.rotateOrder.set(anim.rotateOrder.get())

    #make sure obj piv is on anim
    animTrans = anim.getTranslation(space = 'world')
    xform(obj, piv = animTrans, ws=1)
    rotateAx = anim.getRotateAxis()
    
    #find correct rotation
    jason = duplicate(anim)[0]
    for attr in ['rx', 'ry', 'rz']:
        jason.attr(attr).unlock()
        jason.attr(attr).set(keyable = 1)
    alignPointOrient(obj, jason, 0,1)
    post = jason.rotate.get()
    delete(jason)
    
    #move to origin and rotate correctly
    cutKey(obj, an = 'objects')
    move(obj,[0,0,0], rpr=1)
    obj.rotate.set(post-anim.rotate.get())
    makeIdentity(obj,apply =1, t=1, r=1, s=1, n=0)
    rotate(obj, -rotateAx, r=1, os=1)
    makeIdentity(obj,apply =1, t=1, r=1, s=1, n=0)    

    #add new shape delete old shape
    parent(newShape, anim,add=1,shape = 1)
    delete(obj)
    delete(oldShape)

def swapShapes(o1, o2):
    '''
    Swap shapes between two objects
    '''
    o1Shapes = o1.getChildren(s=1)
    o2Shapes = o2.getChildren(s=1)

    for o1Shape in o1Shapes:
        parent(o1Shape, o2, s=1, r=1)

    for o2Shape in o2Shapes:
        parent(o2Shape, o1, s=1, r=1)
    
def getNamespace(obj):
    '''
    obj:
        object to parse to get namespace
    return:
        a string representation of the namespace
        ex. 
            if obj = "test:pCube1", returns "test"
            if obj = PyNode("test:pCube1"), returns "test"
    '''
    return ":".join(obj.split(":")[:-1])

################################################################
#                    Compact Animation Clip
################################################################

class CompactAnimationClip():

    '''
    Stores multiple poses in one XML file per frame.  Attempts to do this is a somewhat compact manner.
    '''

    def __init__(self):
        pass
        
    def create(self, name, anims, timeRange=None):
        # If no time range is specified, sample the visible time range.
        if timeRange == None: timeRange = (playbackOptions(q=1, min=1), playbackOptions(q=1, max=1))
    
        self.name = name
        self.poses = {}
        for anim in anims:
            anim = PyNode(anim)
            for attr in anim.listAttr(keyable=1, u=1):
            
                attrName = self.filterAttrName(attr)
                
                # In general it's better to make as few query calls as possible, so all
                # of the attribute's keyframe information is stored in the arrays below.
                keyFrameValues = keyframe(attr, q=1, t=timeRange)
                keyAttrValues = keyframe(attr, q=1, vc=1, a=1, t=timeRange)
                keyTangentInfo = keyTangent(attr, q=1, ia=1, oa=1, iw=1, ow=1, itt=1, ott=1, t=timeRange)
                keyCount = keyframe(attr, q=1, kc=1, t=timeRange)
                
                for i in xrange(keyCount):
                    iOffset=6*i
                    # Make sure frame to attribute table exists
                    frame = keyFrameValues[i]
                    if not frame in self.poses: self.poses[frame] = {}
                    # Key information
                    # - Order of store tangent info for reference: ia, oa, iw, ow, itt, ott
                    keyInfo = self.KeyInfo()
                    keyInfo.value = keyAttrValues[i]
                    keyInfo.ia = keyTangentInfo[iOffset] # In Angle
                    keyInfo.oa = keyTangentInfo[iOffset+1] # Out Angle
                    keyInfo.iw = keyTangentInfo[iOffset+2] # In Weight
                    keyInfo.ow = keyTangentInfo[iOffset+3] # Out Weight
                    keyInfo.itt = keyTangentInfo[iOffset+4] # In Tangent Type
                    keyInfo.ott = keyTangentInfo[iOffset+5] # Out Tangent Type
                    self.poses[frame][attrName] = keyInfo

        # self.shiftAnimationToZero()
        self.shiftAnimationToMinFrame(timeRange[0])
                    
        return self
        
    def filterAttrName(self, attr):
        '''
        Completely remove any namespaces or renaming prefixes from the given attribute.
        '''
        
        attrName = str(attr.attrName())
        nodeName = str(attr.node().name())
        referenceFile = attr.node().referenceFile()

        # Uses a namespaces
        if referenceFile == None or referenceFile.isUsingNamespaces():
            return attr.node().stripNamespace().nodeName()+"."+attrName
        # Uses renaming prefix
        else:
            renamingPrefix = referenceFile.namespace+"_"
            # Replace beginning
            if nodeName.startswith(renamingPrefix):
                finalName = nodeName.replace(renamingPrefix, "", 1)
            else:
                finalName = nodeName
            # For full paths, replaced nested strings
            finalName = finalName.replace("|"+renamingPrefix, "|")
            # Done
            return finalName+"."+attrName    
        
    def shiftAnimationToZero(self):
        '''
        Shifts pose frames such that the first frame is at zero.
        '''
        
        # Find smallest frame
        smallestFrame = None
        for f in self.poses:
            if smallestFrame is None or f < smallestFrame:
                smallestFrame = f
        if smallestFrame is None: return None
        
        # Rebuild table such that everything is stored relative to the smallest frame
        newPoses = {}
        for f in self.poses:
            newPoses[f-smallestFrame] = self.poses[f]
        self.poses = newPoses
        
    def shiftAnimationToMinFrame(self, minFrame):
        '''
        Shift pose frames to the left such that the relative start frame (frame 0) is minFrame.
        '''
        
        newPoses = {}
        for f in self.poses:
            newPoses[f-minFrame] = self.poses[f]
        self.poses = newPoses
    
    def save(self, fileName):
        import xml.dom.minidom
        '''
        Example of output:      
        
        <AnimationClip name = "clipName">
            <AttrTable>
                <Attr n="attrName">
                <Attr n="attrName">
                ...
            <Pose frame = "0.0">
                <Key h="hexIndexIntoAttrTable" ia="inAngle" oa="outAngle" itt="inTangentType" ott="outTangentType" value="keyValue"/>
                <Key h="hexIndexIntoAttrTable" ia="inAngle" oa="outAngle" itt="inTangentType" ott="outTangentType" value="keyValue"/>
                ...
            </Pose>
            <Pose frame = "0.0">
                <Key h="hexIndexIntoAttrTable" ia="inAngle" oa="outAngle" itt="inTangentType" ott="outTangentType" value="keyValue"/>
                <Key h="hexIndexIntoAttrTable" ia="inAngle" oa="outAngle" itt="inTangentType" ott="outTangentType" value="keyValue"/>
                ...
            </Pose>
            ...
        </AnimationClip>
        '''
        
        doc = xml.dom.minidom.Document()
        
        # Animation Clip
        animationClip_e = doc.createElement("CompactAnimationClip")
        animationClip_e.setAttribute("name", self.name)
        
        attrToIndexTable = {}
        currentIndex = 0
        # Attribute Table
        attributeTable_e = doc.createElement("AttrTable")
        for pose in self.poses.values():
            for attrName, keyInfo in pose.items():
                if not attrName in attrToIndexTable:
                    # Table Entry
                    attrEntry_e = doc.createElement("Attr")
                    attrEntry_e.setAttribute("n", attrName)
                    # End Table Entry
                    attributeTable_e.appendChild(attrEntry_e)
                    # Add to internal table
                    attrToIndexTable[attrName] = currentIndex
                    currentIndex += 1
        # End Attribute Table
        animationClip_e.appendChild(attributeTable_e)
        for f, pose in self.poses.items():
            # Pose
            pose_e = doc.createElement("Pose")
            pose_e.setAttribute("frame", str(f))
            for attrName, keyInfo in pose.items():
                # Attribute Key
                attrIndex = attrToIndexTable[attrName]
                key_e = doc.createElement("Key")
                key_e.setAttribute("h", hex(attrIndex)[2:])
                if keyInfo.value != self.KeyInfo.defaultValue: key_e.setAttribute("value", str(round(keyInfo.value, 10)))
                if keyInfo.ia != self.KeyInfo.defaultIa: key_e.setAttribute("ia", str(round(keyInfo.ia, 10)))
                if keyInfo.oa != self.KeyInfo.defaultOa: key_e.setAttribute("oa", str(round(keyInfo.oa, 10)))
                if keyInfo.iw != self.KeyInfo.defaultIw: key_e.setAttribute("iw", str(round(keyInfo.iw, 10)))
                if keyInfo.ow != self.KeyInfo.defaultOw: key_e.setAttribute("ow", str(round(keyInfo.ow, 10)))
                if keyInfo.itt != self.KeyInfo.defaultItt: key_e.setAttribute("itt", str(keyInfo.itt))
                if keyInfo.ott != self.KeyInfo.defaultOtt: key_e.setAttribute("ott", str(keyInfo.ott))
                # End Attribute Key
                pose_e.appendChild(key_e)
            # End Pose
            animationClip_e.appendChild(pose_e)
        # End Animation Clip
        doc.appendChild(animationClip_e)
        
        # Write to file
        file = open(fileName, "w")
        file.writelines(doc.toprettyxml())
        file.close()
        
    def load(self, fileName):
        '''
        Loads animation clip from an XML file.
        '''
        
        import xml.dom.minidom
        
        doc = xml.dom.minidom.parse(fileName)
        
        animationClip_e = doc.getElementsByTagName("CompactAnimationClip")[0]
        self.name = animationClip_e.getAttribute("name")
        self.poses = {}
        pose_elements = animationClip_e.getElementsByTagName("Pose")
        
        # Load attr table
        attrTable_e = animationClip_e.getElementsByTagName("AttrTable")[0]
        attrTableAttrs_e = attrTable_e.getElementsByTagName("Attr")
        indexToAttrTable = {}
        currentIndex = 0
        for attr_e in attrTableAttrs_e:
            indexToAttrTable[currentIndex] = attr_e.getAttribute("n")
            currentIndex += 1
        
        # Load poses
        for pose_e in pose_elements:
            frame = float(pose_e.getAttribute("frame"))
            attr_elements = pose_e.getElementsByTagName("Key")
            self.poses[frame] = {}
            for attr_e in attr_elements:
                attrIndex = int("0x"+attr_e.getAttribute("h"), 0)
                attrName = indexToAttrTable[attrIndex]
                if attr_e.hasAttribute("value"):
                    attrValue = attr_e.getAttribute("value")
                    if (attrValue == "True"): attrValue = 1
                    if (attrValue == "False"): attrValue = 0
                else:
                    attrValue = 0
                keyInfo = self.KeyInfo()
                keyInfo.value = float(attrValue)
                if attr_e.hasAttribute("ia"): keyInfo.ia = float(attr_e.getAttribute("ia"))
                if attr_e.hasAttribute("oa"): keyInfo.oa = float(attr_e.getAttribute("oa"))
                if attr_e.hasAttribute("iw"): keyInfo.iw = float(attr_e.getAttribute("iw"))
                if attr_e.hasAttribute("ow"): keyInfo.ow = float(attr_e.getAttribute("ow"))
                if attr_e.hasAttribute("itt"): keyInfo.itt = attr_e.getAttribute("itt")
                if attr_e.hasAttribute("ott"): keyInfo.ott = attr_e.getAttribute("ott")
                self.poses[frame][attrName] = keyInfo
        
        return self
    
    def applyClip(self, namespace = ":", startFrame = 0):
        '''
        Apply animation starting from 
        '''

        if not namespace.endswith(":"): namespace += ":"
        
        savedSelection = ls(sl=1)
        select(d=1)
        
        # listConnections is computationally expensive, so cache the tests to see if an attribute is keyable here
        keyableAttrs = {}
        def isKeyable(attrName):
            if attrName in keyableAttrs:
                return keyableAttrs[attrName]
            '''
            -- Slow PyMEL --
            allConnections = newAttr.listConnections(s=1, d=0, p=1)
            animCurveConnections = newAttr.listConnections(s=1, d=0, p=1, type='animCurve')
            '''
            # Make sure the attribute isn't driven by something else such as a parent constraint
            allConnections = mc.listConnections(attrName, s=1, d=0, p=1)
            animCurveConnections = mc.listConnections(attrName, s=1, d=0, p=1, type="animCurve")
            # Make sure the attribute is settable
            isSettable = mc.getAttr(attrName, se=1)
            hasGoodConnections = (allConnections == animCurveConnections) # Only animCurve attrs are good connections (constraints = bad)
            # Cache and return
            keyableAttrs[attrName] = (isSettable and hasGoodConnections)
            
            return keyableAttrs[attrName]
        
        for frame, pose in self.poses.items():
            t = frame+startFrame
            currentTime(t)
            tangentModCommands = []
            for attr, keyInfo in pose.items():
                if objExists(namespace+attr):

                    newAttr = PyNode(ls(namespace+attr)[0])
                    newAttrName = str(newAttr)
                    
                    if isKeyable(newAttrName):
                        # Default tangent can't be fixed
                        if (keyInfo.itt == "fixed"): ittToUse = "auto"
                        else: ittToUse = keyInfo.itt
                        if (keyInfo.ott == "fixed"): ottToUse = "auto"
                        else: ottToUse = keyInfo.ott
                        newAttr.setKey(v=keyInfo.value, itt=ittToUse, ott=ottToUse)
                        # Whether or not tangents are weighted or not
                        isWeightedQuery = keyTangent(q=1, wt=1) # this can potentially return a None type
                        if type(isWeightedQuery) == type(list) and (not keyTangent(q=1, wt=1)[0] and (keyInfo.iw != 1 or keyInfo.ow != 1)):
                            keyTangent(e=1, wt=1)
                        # Set tangent modification command
                        tangentModCommands.append(lambda: keyTangent(newAttr, e=1, t=(t,t), ia=keyInfo.ia, oa=keyInfo.oa, iw=keyInfo.iw, ow=keyInfo.ow))
            # Run tangent update commands at the end, since doing so while still adding keyframes will provide inaccurate results
            for tmc in tangentModCommands: tmc()
            # Show the new keyed-in pose
            refresh()
        
        select(savedSelection) 
        
    class KeyInfo():
        
        defaultValue = 0.0
        defaultIa = 0.0
        defaultOa = 0.0
        defaultIw = 1.0
        defaultOw = 0.0
        defaultItt = "auto"
        defaultOtt = "auto"
        
        def __init__(self):
            self.value = self.defaultValue # Attribute Value
            self.ia = self.defaultIa # In Angle
            self.oa = self.defaultOa # Out Angle
            self.iw = self.defaultIw # In Weight
            self.ow = self.defaultOw # Out Weight
            self.itt = self.defaultItt # In Tangent Type
            self.ott = self.defaultOtt # Out Tangent Type

            
################################################################
#                           Pose
################################################################

class Pose():
    def __init__(self):
        pass

    def create(self, name, anims, t = None):
        self.name = name
        self.attrValue = {}
        for anim in anims:
            anim = PyNode(anim)
            for attr in anim.listAttr(keyable=1, u=1):
                attrName = self.filterAttrName(attr)
                self.attrValue[attrName] = attr.get(t=t)
        return self

    def set(self, name, attrValue):
        self.name = name
        self.attrValue = attrValue
        return self
        
    def saveToXML(self, fileName):
        '''
        example of output:      

        <Pose name = "poseName">
            <Attribute name = "attrName", value = "value"/>
            <Attribute name = "attrName", value = "value"/>
            <Attribute name = "attrName", value = "value"/>
        </Pose>
        '''
        import xml.dom.minidom

        doc = xml.dom.minidom.Document()
        #create pose Element
        pose_element = doc.createElement("Pose")
        pose_element.setAttribute("name", self.name)
        for attr, value in self.attrValue.items():
            attr_element = doc.createElement("Attribute")
            attr_element.setAttribute("name", str(attr))
            attr_element.setAttribute("value", str(value))       
            pose_element.appendChild(attr_element)
        doc.appendChild(pose_element)

        #create file
        FILE = open(fileName , "w")
        FILE.writelines(doc.toprettyxml())
        FILE.close()

        #return xml string
        return doc.toprettyxml()

    def readXML(self,file):
        '''
        creates a pose from a .xml file
        '''
        import xml.dom.minidom
        doc = xml.dom.minidom.parse(file)
        pose_element = doc.getElementsByTagName("Pose")[0]
        pose_name = pose_element.getAttribute("name")
        self.name = pose_name
        self.attrValue = {}
        attr_elements = pose_element.getElementsByTagName("Attribute")
        for x in attr_elements:
            attr_name = x.getAttribute("name")
            attr_value = x.getAttribute("value")
            if(attr_value == "True"):
                attr_value = 1
            if(attr_value == "False"):
                attr_value = 0
            self.attrValue[attr_name] = float(attr_value)
        return self

    def filterAttrName(self, attr):
        '''
        Completely remove any namespaces or renaming prefixes from the given attribute.
        '''
        
        attrName = str(attr.attrName())
        nodeName = str(attr.node().name())
        referenceFile = attr.node().referenceFile()

        # Uses a namespaces
        if referenceFile == None or referenceFile.isUsingNamespaces():
            return attr.node().stripNamespace().nodeName()+"."+attrName
        # Uses renaming prefix
        else:
            renamingPrefix = referenceFile.namespace+"_"
            # Replace beginning
            if nodeName.startswith(renamingPrefix):
                finalName = nodeName.replace(renamingPrefix, "", 1)
            else:
                finalName = nodeName
            # For full paths, replaced nested strings
            finalName = finalName.replace("|"+renamingPrefix, "|")
            # Done
            return finalName+"."+attrName  
        
    def getAnims(self):
        allAnims = []
        for key, value in self.attrValue.items():
            anim = key.split(".")[0]
            if not anim in allAnims:
                allAnims.append(anim)
        return allAnims
        
    def getValue(self, attr):
        if attr in self.attrValue.keys():
            return self.attrValue[attr]
        return None
        
    def getAttributes(self, obj = None):
        if obj:
            returnAttrs = []
            for key in self.attrValue.keys():
                if key.startswith(obj + "."):
                    returnAttrs.append(key)
            return returnAttrs
        else:
            return self.attrValue.keys()
        
    def differencePose(self, pose1, pose2):
        '''
        returnedPose = pose2 - pose1 
        '''
        newAttrValue = {} 
        for p2Key in pose2.attrValue.keys():
            if p2Key in pose1.attrValue.keys():
                if(pose2.attrValue[p2Key]=="True" or pose2.attrValue[p2Key]=="False"):
                    newValue = 1-( pose2.attrValue[p2Key] == pose1.attrValue[p2Key])
                else:
                    newValue = pose2.attrValue[p2Key] - pose1.attrValue[p2Key]
                if(newValue > .000001 or newValue < -.000001):
                    newAttrValue[p2Key] = newValue
        return self.set(pose2.name + " - " + pose1.name, newAttrValue)
                
    def goToPose(self, namespace = ":"):
        if not namespace.endswith(":"):
            namespace += ":"
        for attr, value in self.attrValue.items():
            if objExists(namespace+attr):
                newAttr = PyNode(ls(namespace+attr)[0]) # PyNode doesn't always navigate properly to the anim path anymore, need to use ls to get the full path.
                hasConnections = newAttr.listConnections(s=1, p=1, d=0)
                locked = newAttr.isLocked()
                hasGoodConnections = newAttr.listConnections(s=1, d=0, p=1, type = 'animCurve') == newAttr.listConnections(s=1, p=1, d=0) #only animCurve attrs are good connections
                if (not locked) and ( hasGoodConnections):
                    newAttr.set(value)

    def __str__(self):
        new_str = "Pose[%s]"%self.name
        for attr, value in self.attrValue.items():
            new_str += "\n\tAttribute[%s = %s]"%(str(attr), str(value))
        return new_str

################################################################
#                         Pose Blend
################################################################
            
'''
Contained system for blending a rig between two provided poses on the current frame.
'''
class PoseBlend():
    
    def __init__(self):
        pass
    
    '''
    startPose    - Pose class representing the pose when blend is 0.
    endPose      - Pose class representing the pose when blend is 1.
    anims        - Anims to blend these poses to.  Valid, keyable attributes are read in at the start.
    blend        - Blend between the start and end poses.
    '''
    def create(self, startPose, endPose, anims=[], startBlend=0):
        if (startPose == None or endPose == None): raise
        self._startPose = startPose
        self._endPose = endPose
        self._anims = anims
        self._blend = None
        
        self._attrBlendFuncs = set([])
        self._poseBlendSetup(startBlend)
        
    '''
    Create a pose blend between the current pose and a given pose.
    '''
    def blendWithCurrent(self, endPose, anims=[]):
        startPose = Pose().create("Current", anims, currentTime())
        self.create(startPose, endPose, anims)
        return self
        
    '''
    Return true if a particular attribute can be modified.
    '''
    def canBeModified(self, attr):
        attrFullName = attr.name()
        # Make sure the attribute isn't driven by something else such as a parent constraint
        allConnections = mc.listConnections(attrFullName, s=1, d=0, p=1)
        animCurveConnections = mc.listConnections(attrFullName, s=1, d=0, p=1, type="animCurve")
        # Make sure the attribute is settable
        isSettable = mc.getAttr(attrFullName, se=1)
        hasGoodConnections = (allConnections == animCurveConnections) # Only animCurve attrs are good connections (constraints = bad)
        
        return hasGoodConnections
    
    '''
    Create a simple gui for controlling this pose blend.
    '''
    def gui(self):
        if window('PoseBlendWindow', exists=1): deleteUI('PoseBlendWindow')
        
        self.window = window('PoseBlendWindow', title = "Blend Pose", s=False, width=256, height=64)
        
        layout = verticalLayout()
        blendSlider = floatSliderGrp(p=layout, min=0, max=1, fieldMinValue=0, fieldMaxValue=1, value=0, step=0.01)
        def blendCommand():
            self.updateBlend(blendSlider.getValue())
            
        blendSlider.dragCommand(Callback(blendCommand))
        layout.redistribute()
        
        showWindow(self.window)
    
    '''
    Setup the pose blend system.
    '''
    def _poseBlendSetup(self, startBlend):
        for anim in self._anims:
            anim = PyNode(anim)
            for attr in anim.listAttr(keyable=1, u=1):
                # Attr exists in the anim
                if not self.canBeModified(attr): continue
                attrName = attr.name().split(":")[-1]
                
                startV = self._startPose.getValue(attrName)
                endV = self._endPose.getValue(attrName)
                
                if (startV == None or endV == None): continue
                
                # Function that blends start pose value to end pose value given a blend from 0 to 1
                class BlendFuncWrapper:
                    _attrFullName = attr.name()
                    _startV = startV
                    _endV = endV
                    def blendFunc(self, b):
                        mc.setAttr(self._attrFullName, b*(self._endV-self._startV)+self._startV)
                self._attrBlendFuncs.add(BlendFuncWrapper().blendFunc)
        self.updateBlend(startBlend)
        
    '''
    Update the blend system.
    '''
    def updateBlend(self, b):
        if (self._blend == b): return None
        self._blend = b
        try:
            for blendFunc in self._attrBlendFuncs: blendFunc(b)
        except:
            print "Error encountered updating the pose blend."
        
################################################################
#                         Mesh Info
################################################################
class MeshVertexInfo():
    def __init__(self):
        pass
        
    def create(self, mesh, space = 'object'):
        mesh = PyNode(mesh)
        self.numVertices = len(mesh.vtx[:])
        self.index_pos = {}
        self.space = space
        self.index_normal = {}
        for x in xrange(self.numVertices):
            pos = mesh.vtx[x].getPosition(space = self.space)
            normal = mesh.vtx[x].getNormal()
            self.index_pos[x] = [float(str(pos[0])), float(str(pos[1])), float(str(pos[2]))]#str because it truncates the float, make sure __eq__ works
            self.index_normal[x] = [float(str(normal[0])), float(str(normal[1])), float(str(normal[2]))]
        return self
    
    def set(self, numVerts, space, index_pos, index_normal):
        self.numVertices = numVerts
        self.space = space
        self.index_pos = index_pos
        self.index_normal = index_normal
        return self


    def saveToXML(self, fileName):
        '''
        example of output:      

        <MeshVertexInfo>
            <space = local, world>
            <Vertex index = ###>
                <positionX>##</positionX>
                <positionY>##</positionY>
                <positionZ>##</positionZ>
            </Vertex>
            <Vertex index = ###>
            ...
        </MeshVertexInfo>
        '''
        import xml.dom.minidom
        doc = xml.dom.minidom.Document()
        #create pose Element
        MVI_element = doc.createElement("MeshVertexInfo")
        numVert_element = doc.createElement('NumberOfVertices')
        numVert_text = doc.createTextNode(str(self.numVertices))
        numVert_element.appendChild(numVert_text)
        MVI_element.appendChild(numVert_element)
        space_element = doc.createElement('Space')
        space_text = doc.createTextNode(str(self.space))
        space_element.appendChild(space_text)
        MVI_element.appendChild(space_element)
        for index in xrange(self.numVertices):
            vertex_element = doc.createElement("Vertex")
            vertex_element.setAttribute("index", str(index))
            posX_element = doc.createElement("PositionX")
            posX_text = doc.createTextNode(str(self.index_pos[index][0]))
            posX_element.appendChild(posX_text)
            posY_element = doc.createElement("PositionY")
            posY_text = doc.createTextNode(str(self.index_pos[index][1]))
            posY_element.appendChild(posY_text)
            posZ_element = doc.createElement("PositionZ")
            posZ_text = doc.createTextNode(str(self.index_pos[index][2]))
            posZ_element.appendChild(posZ_text)
            norX_element = doc.createElement("NormalX")
            norX_text = doc.createTextNode(str(self.index_normal[index][0]))
            norX_element.appendChild(norX_text)
            norY_element = doc.createElement("NormalY")
            norY_text = doc.createTextNode(str(self.index_normal[index][1]))
            norY_element.appendChild(norY_text)
            norZ_element = doc.createElement("NormalZ")
            norZ_text = doc.createTextNode(str(self.index_normal[index][2]))
            norZ_element.appendChild(norZ_text)
            
            vertex_element.appendChild(posX_element)
            vertex_element.appendChild(posY_element)
            vertex_element.appendChild(posZ_element)
            vertex_element.appendChild(norX_element)            
            vertex_element.appendChild(norY_element)
            vertex_element.appendChild(norZ_element)

            MVI_element.appendChild(vertex_element)
        doc.appendChild(MVI_element)
        
        #create file
        FILE = open(fileName , "w")
        FILE.writelines(MVI_element.toprettyxml())
        FILE.close()

        #return xml string
        return doc.toprettyxml()

    def readXML(self,file):
        '''
        creates a pose from a .xml file
        '''
        import xml.dom.minidom
        doc = xml.dom.minidom.parse(file)
        MVI_element = doc.getElementsByTagName("MeshVertexInfo")[0]
        numVert_element = MVI_element.getElementsByTagName('NumberOfVertices')[0]
        self.numVertices = int(numVert_element.firstChild.data)
        space_element = MVI_element.getElementsByTagName('Space')[0]
        self.space = str(space_element.firstChild.data).strip()
        self.index_pos = {}
        self.index_normal = {}
        vertex_elements = MVI_element.getElementsByTagName("Vertex")
        for x in vertex_elements:
            index = int(x.getAttribute('index'))
            pos = []
            normal = []
            posX_element = x.getElementsByTagName('PositionX')[0]
            pos.append(float(posX_element.firstChild.data))
            posY_element = x.getElementsByTagName('PositionY')[0]
            pos.append(float(posY_element.firstChild.data))
            posZ_element = x.getElementsByTagName('PositionZ')[0]
            pos.append(float(posZ_element.firstChild.data))
            self.index_pos[index] = pos
            norX_element = x.getElementsByTagName('NormalX')[0]
            normal.append(float(norX_element.firstChild.data))
            norY_element = x.getElementsByTagName('NormalY')[0]
            normal.append(float(norY_element.firstChild.data))
            norZ_element = x.getElementsByTagName('NormalZ')[0]
            normal.append(float(norZ_element.firstChild.data))
            self.index_normal[index] = normal

        return self

    def apply(self, mesh):
        mesh = PyNode(mesh)
        meshVertCount = len(mesh.vtx[:])
        numVerts = meshVertCount
        if self.numVertices < meshVertCount:
            numVerts = self.numVertices
        for x in xrange(numVerts):
            mesh.vtx[x].setPosition(self.index_pos[x], space = self.space)
            mesh.vtx[x].geomChanged() 

    def __repr__(self):
        return 'MeshVertexInfo().set(%s, "%s", %s)'%(self.numVertices.__repr__(), self.space, self.index_pos.__repr__(), self.index_normal.__repr__())

    def __str__(self):
        retString = "[MeshVertexInfo]: \n\t numberOfVertices = %s \n\t space = %s \n\t Vertices:"%(self.numVertices, self.space)
        for index in xrange(self.numVertices):
            retString += "\n\t\t %i: pos = %s, normal = %s"%(index, self.index_pos[index], self.index_normal[index])
        return retString

    def __eq__(self, other):
        if not self.space == other.space:
            return 0
        if not self.numVertices == other.numVertices:
            return 0
        if not self.index_pos == other.index_pos:
            return 0 
        if not self.index_normal == other.index_normal:
            return 0
        return 1



################################################################
#                           Corrective Blendshape
#################################################################
class CorrectiveBlendShape():
    def __init__(self):
        self.name = None
        self.mesh = None
        self.anims = None
        self.startPose = None 
        self.startMeshInfo = None
        self.blendPose = None
        self.blendMeshInfo = None
        self.blendShapeNode = None
        self.connectAttr = None
        
    def setDefaultState(self,name, mesh, anims):
        self.name = name
        self.mesh = mesh
        self.anims = anims
        self.startPose = Pose().create(self.name + "_startPose", anims)
        self.startMeshInfo = MeshVertexInfo().create(self.mesh)
    
    def setBlendShapeState(self):
        self.blendPose = Pose().create(self.name + "_blendPose", self.anims)
        self.startPose.goToPose(getNamespace(self.mesh))
        self.blendMeshInfo = MeshVertexInfo().create(self.mesh)
        self.blendPose.goToPose(getNamespace(self.mesh))

    def createBlendShape(self, connectingAttr):
        blendShapeMesh = duplicate(self.mesh)[0]
        blendShapeMesh.rename(self.name)
        tweakNode = PyNode(self.mesh).getShape().tweakLocation.listConnections(s=1, d=0)
        if tweakNode:
            delete(tweakNode[0])#deleting the tweak may cause problems if tweak is used
            print tweakNode[0]
        self.goToDefaultState()
        self.blendMeshInfo.apply(blendShapeMesh)
        blendShape(blendShapeMesh, self.mesh, foc=1)
        #delete(blendShapeMesh)
        
    def goToBlendShapeState(self):    
        if not (self.startPose and self.blendPose):
            return None
        self.startPose.goToPose(namespace = getNamespace(self.mesh))
        self.blendMeshInfo.apply(self.mesh)
        self.blendPose.goToPose(getNamespace(self.mesh))
        
    def goToDefaultState(self):
        if not self.startPose:
            return None
        self.startPose.goToPose(namespace = getNamespace(self.mesh))
        self.startMeshInfo.apply(self.mesh)



# 0) Line up objects so they overlap
# 1) Make sure SKINCLUSTER is set to the name of the skinCluster node of the bound rig shape
# 2) Select the bound rig shape first (the one with skin weighting)
# 3) Select the working shape second (unbound)
# 4) Run the entire thing

# Apply the difference of m1 and m2 (m1-m2) to the base mesh     
def matchTweakMeshToBSMesh(tweakMesh, bsMesh, skin):
    SKINCLUSTER = skin # Because I'm too lazy to get it programatically
    snapTable = {}
    numVsTweakMesh = len(tweakMesh.vtx)
    numVsBsMesh = len(bsMesh.vtx)
    
    if (numVsTweakMesh != numVsBsMesh):
        print "ERROR: Meshes don't have the same number of vertices."
        return None

    print "Generating snap table...."
    for i in xrange(numVsTweakMesh):
        tweakV = tweakMesh.vtx[i]
        bsV = bsMesh.vtx[i]
        result = worldSnapTweakVertexToTargetVertex(tweakV, bsV)
        if result != None:
            snapTable[tweakV] = result
    
    print "Forming skinned mesh to blend shape...."
    for v in snapTable.keys():
        t = snapTable[v]
        move(v, t, r=1)
        
    print "Acquiring blend shape!"
    SKINCLUSTER.envelope.set(0)
    name = bsMesh.name()
    delete(bsMesh)
    d = duplicate(tweakMesh, n=name)[0]
    d.tx.unlock()
    d.ty.unlock()
    d.tz.unlock()
    d.rx.unlock()
    d.ry.unlock()
    d.rz.unlock()
    d.sx.unlock()
    d.sy.unlock()
    d.sz.unlock()
    d.visibility.unlock()
    try:
        parent(d,w=1)
    except:
        """ Maya is being stupid. Ignore her. """
    SKINCLUSTER.envelope.set(1)

    print "REVERSING POLARITY!!! (Reversing the skinned mesh forming)..."
    for v in snapTable.keys():
        t = snapTable[v]
        move(v, [-t[0], -t[1], -t[2]], r=1)
    return d

def vMinus(v1, v2):
    return [v1[0]-v2[0], v1[1]-v2[1], v1[2]-v2[2]]

def vEquals(v1, v2):
    return ((v1[0]==v2[0]) and (v1[1]==v2[1]) and (v1[2]==v2[2]))

# Work around Maya's odd history behaviour to properly snap
# a skinned vertex to another vertex in world space
# - Return the actual movement needed to snap one vert to the other
def worldSnapTweakVertexToTargetVertex(v, targetV, LOC_DIST=15):
    center = xform(v, q=1, ws=1, t=1)
    targetCenter = xform(targetV, q=1, ws=1, t=1)
    if vEquals(center, targetCenter):
        return None
    
    # Figure out what space the relative move is ACTUALLY using
    # (accounting for all joint deformations and such)
    select(v)
    move([LOC_DIST,0,0], r=1)
    xEnd = xform(v, q=1, ws=1, t=1)
    move([-LOC_DIST,0,0], r=1)
    move([0,LOC_DIST,0], r=1)
    yEnd = xform(v, q=1, ws=1, t=1)
    move([0,-LOC_DIST,0], r=1)
    
    # Space locators representing how the new transform space will be oriented
    centerLoc = spaceLocator(n="lssCenter")
    move(center, ws=1)
    xEndLoc = spaceLocator(n="lssXDirection")
    move(xEnd, ws=1)
    yEndLoc = spaceLocator(n="lssYDirection")
    move(yEnd, ws=1)

    # Local space simulation
    lss = group(em=1, w=1, n="spaceSimulator")
    move(center, ws=1)
    ac = aimConstraint(xEndLoc, lss, aim=(1,0,0), wut="object", wuo=yEndLoc)
    
    # Clean up garbage
    delete(ac)
    delete(centerLoc)
    delete(xEndLoc)
    delete(yEndLoc)
    
    # Figure out relative movements to make to match v to targetV (can't do it
    # directly using xform ws because of how Maya saves tweak history)
    targetLoc = spaceLocator(n="target")
    move(targetCenter, ws=1)
    parent(targetLoc, lss)
    
    # Now use the local values of the target locator to perform movements
    movement = [targetLoc.tx.get(),targetLoc.ty.get(),targetLoc.tz.get()]
    
    # Further cleaning
    delete(targetLoc)
    delete(lss)
    
    return movement

################################################################
#                         LightLinking
################################################################

def exportLights(lights):
    fileXML = sceneName().parent + "/" +sceneName().split("/")[-1].split(".")[0] + "_lights.xml" 
    lightsFile = sceneName().parent +"/"+ sceneName().split("/")[-1].split(".")[0] + "_lights.ma"
    select(lights)
    LightLink().create(lights).saveToXML(fileXML)
    exportSelected(lightsFile,f=1, typ = "mayaAscii")
        

def importLights(lightNamespace, objectNamespace, xmlFile):
    LightLink().readXML(xmlFile).linkLights(lightNamespace, objectNamespace)


class LightLink():
    def __init__(self):
        pass
    
    def create(self, lights):
        self.light_link = {}
        self.light_ignore = {}
        self.lights = []
        for l in lights:
            light = PyNode(l)
            lightSh = light.getShape()
            lightName = light.name().split(":")[-1]
            linkObjs = []
            ignoreObjs = []
            for attr in lightSh.message.listConnections(plugs =1, destination =1):
                if attr.node().type() == 'lightLinker':
                    lightLinker = attr.node()
                    attrType = attr.name().split(".")[-1]
                    if attrType == 'light':
                        linkObj = attr.parent().object.listConnections()[0]
                        linkObj = linkObj.name().split(":")[-1]
                        linkObjs.append(linkObj)
                    elif attrType == 'lightIgnored':
                        ignoreObj = attr.parent().objectIgnored.listConnections()[0]
                        ignoreObj = ignoreObj.name().split(":")[-1]
                        ignoreObjs.append(ignoreObj)
            self.light_link[lightName] = linkObjs
            self.light_ignore[lightName] = ignoreObjs
            self.lights.append(lightName)
        return self

    def set(self, lights, light_link, light_ignore):
        self.lights = lights
        self.light_ignore = light_ignore
        self.light_link = light_link

    def saveToXML(self, fileName):
        '''
        example of output:      

        <LightLink>
            <Light name = objName(without namespace)>
                <Link>
                    <Object name = objName(without namespace)>    
                <Ignore>
                    <Object name = objName(without namespace)>
                    <Object name = objName(without namespace)>
            <Light name = objName(without namespace)>    
                ...    
        </LightLink>
        '''
        import xml.dom.minidom

        doc = xml.dom.minidom.Document()
        #create pose Element
        lightLink_element = doc.createElement("LightLink")
        for l in self.lights:
            #light
            light_element = doc.createElement("Light")
            light_element.setAttribute("name", l)
    
            #links
            link_element = doc.createElement("Link")
            linkObjs = self.light_link[l]
            for link in linkObjs:
                obj_element = doc.createElement("Object")
                obj_element.setAttribute("name", link)    
                link_element.appendChild(obj_element)

            ignore_element = doc.createElement("Ignore")
            ignoreObjs = self.light_ignore[l]
            #ignores
            for ig in ignoreObjs:
                obj_element = doc.createElement("Object")
                obj_element.setAttribute("name", ig)    
                ignore_element.appendChild(obj_element)
            light_element.appendChild(link_element)
            light_element.appendChild(ignore_element)
            lightLink_element.appendChild(light_element)            

        doc.appendChild(lightLink_element)

        #create file
        FILE = open(fileName , "w")
        FILE.writelines(doc.toprettyxml())
        FILE.close()

        #return xml string
        return doc.toprettyxml()

    def readXML(self, fileName):
        '''
        creates a LightLink from a .xml file
        '''
        import xml.dom.minidom
        doc = xml.dom.minidom.parse(fileName)
        lightLink_element = doc.getElementsByTagName("LightLink")[0]
        lightElements = lightLink_element.getElementsByTagName("Light")
        self.lights = []
        self.light_link = {}
        self.light_ignore = {}
        for le in lightElements:
            lightName = le.getAttribute("name")
            #link
            link_element = le.getElementsByTagName("Link")[0]
            linkObjElements = link_element.getElementsByTagName("Object")
            linkObjs = []
            for x in linkObjElements:
                linkObjs.append(x.getAttribute("name"))        
            #ignore
            ignore_element = le.getElementsByTagName("Ignore")[0]
            ignoreObjElements = ignore_element.getElementsByTagName("Object")
            ignoreObjs = []
            for x in ignoreObjElements:
                ignoreObjs.append(x.getAttribute("name"))
            self.lights.append(lightName)
            self.light_link[lightName] = linkObjs
            self.light_ignore[lightName] = ignoreObjs
        return self

    def linkLights(self, lightNamespace = ":", objectNamespace = ":"):
        import pymel.core.runtime as rt
        if not lightNamespace.endswith(":"):
            lightNamespace += ":"
        if not objectNamespace.endswith(":"):
            objectNamespace += ":"
        for l in self.lights:
            light = PyNode(lightNamespace + l)
            #breaks
            ignoreObjects = self.light_ignore[l]
            for obj in ignoreObjects:
                select(cl=1)
                if objExists(objectNamespace + obj):
                    ignoreObj = ls(objectNamespace + obj)#if multiple objects of same name, break links to all
                    select(light, ignoreObj)
                    rt.BreakLightLinks()
            #links
            linkObjects = self.light_link[l]
            for obj in linkObjects:
                select(cl=1)
                if objExists(objectNamespace + obj):
                    linkObjs = ls(objectNamespace + obj) #if multiple objects of same name, link to all
                    for linkObj in linkObjs:
                        select(light, linkObj)
                        rt.MakeLightLinks()
                
            
            
            select(cl=1)

#################################################################
#                        Projection Scripts
#################################################################



def projectPoint(point, vector, goals, tol = .0001):
    '''
    projects the point along the vector in the positive and negative direction and to find all the points where the vector intersects all the goal objects
    
    point: 
        the starting point of the vector, worldspace
    vector:
        the vector to project along, uses both positive and negative
    goals:
        a list or single obj to project onto
    tol:
        collsion tolerance of the obj
    return:
        a list of points [x,y,z] of there the intersection is in world space
        
    '''
    if not (type(goals) is list or type(goals) is tuple):
        goals = [goals]
    points = []
    for goal in goals:
        goal = PyNode(goal)
        intersections = []
        negVector = [-vector[0], -vector[1], -vector[2]]
        intersections.append(goal.intersect(point, vector, tolerance = tol, space = 'world'))
        intersections.append(goal.intersect(point, negVector, tolerance = tol, space = 'world'))

        if goal.getShape().type() == 'mesh':
            for i in intersections:
                if i[0]:
                    for p in i[1]:
                        points.append(p)

        elif goal.getShape().type() == 'nurbsSurface':
            for i in intersections:
                if i[0]:
                    points.append(i[3])            
    return points


def projectComponent(component, goals, tol = .001):
    '''
    project a component of an object onto the goals
    projects using the component normal and a vector from component to center of other obj
    currently only works for polygon vertices because Pymel only supports verts, face, edge
    
    component:
        the polygon component to project, usually vertex
    
    goals:
        a list or single obj to project onto.
    
    tol: 
        tolerance for collision
        
    return:
        the closest point the contacts on of the goals
        
    
    
    '''
    compPoint = component.getPosition(space = 'world')
    normals = component.getNormals()
    if (not type(goals) is list) and (not type(goals) is tuple):
        goals = [goals]
    for goal in goals:
        goal = PyNode(goal)
        gc = goal.boundingBox().center()
        cvect = [compPoint[0] - gc[0],compPoint[1] - gc[1],compPoint[2] - gc[2]]
        cvMag = sqrt(pow(cvect[0],2) + pow(cvect[1],2) + pow(cvect[2],2))
        cv = [cvect[0]/cvMag,cvect[1]/cvMag,cvect[2]/cvMag]
        normals.append(cv)
    points = []
    for norm in normals:
        newPoints = projectPoint(compPoint, norm, goals)
        map(lambda x: points.append(x), newPoints)
            
    min = -1
    bestPoint = compPoint
    cur = None
    for p in points:
        cur = sqrt( pow(p[0]-compPoint[0], 2) + pow(p[1]-compPoint[1], 2) + pow(p[2]-compPoint[2], 2))
        if cur < min or min == -1:
            min = cur
            bestPoint = p    

    return bestPoint 
    
    
def wrapPolyObj(obj, goals):
    '''
    projects the polygon object onto the goal objects
    
    obj:
        the polygon obj to project
        
    goal:
        the desired obj(s) to wrap to
    
    return:
        None
    

    '''

    newPoints = []
    obj = PyNode(obj)
    
    for num in xrange(obj.numVertices()):
        newPoints.append(projectComponent(PyNode('%s.vtx[%i]'%(obj.name(), num)), goals))
    #if change position before all newpoints are found component normal can be changed
    
    for num in xrange(obj.numVertices()):
        PyNode('%s.vtx[%i]'%(obj.name(), num)).setPosition(newPoints[num], space = 'world')

def turnNurbsToPoly(nurbs):
    """
    creates a polygone around the nurbs where the polygon vertex matches the nurbs CV
    doesn't delete the original
    
    nurbs:
        the nurbs obj to make polygonal
        
    return the Polygon obj
    
    """        

    nurbs = PyNode(nurbs)
    unum = nurbs.spansUV.get()[0] + nurbs.degreeUV.get()[1]
    vnum = nurbs.spansUV.get()[1] + nurbs.degreeUV.get()[1]
    poly = polyPlane(ch=1,w = 1, h=1, sw= vnum-1,sh = unum-1, n = "%s_poly"%nurbs.name())[0]
    vertNum = 0
    for u in xrange(unum):
        for v in xrange(vnum):
            nurbPoint = nurbs.getCV(u,v, space = 'world')
            vertex = PyNode('%s.vtx[%i]'%(poly.name(), vertNum))
            vertex.setPosition(nurbPoint, space = 'world')
            vertNum +=1

    return poly


def wrapNurbsObj(nurbs, goals):
    """
     wraps the nurbs obj around the goal objects
     
     nurbs:
         the object being projected
     
     goals:
         the object that is being projected to
         
     return:
         None

    """
    nurbs = PyNode(nurbs)
    poly = turnNurbsToPoly(nurbs)
    wrapPolyObj(poly, goals)
    unum = nurbs.spansUV.get()[0] + nurbs.degreeUV.get()[1]
    vnum = nurbs.spansUV.get()[1] + nurbs.degreeUV.get()[1]
    vertNum = 0
    for u in xrange(unum):
        for v in xrange(vnum):
            vertex = PyNode('%s.vtx[%i]'%(poly.name(), vertNum))
            vertPoint = vertex.getPosition(space = 'world')
            nurbs.setCV(u,v,vertPoint, space = 'world')
            vertNum +=1
    delete(poly)

def wrapObj(obj, goals):
    """
    wraps either polygonal or NURBS objects around the goal objs
    
    obj:
        object to project
        
    goals:
        object(s) to project to
    """

    obj = PyNode(obj)
    objType = obj.getShape().type()
    if objType == 'mesh':
        wrapPolyObj(obj,goals)
    elif objType == 'nurbsSurface':
        wrapNurbsObj(obj,goals)    
    
#################################################################
#                        AnimationClips
#################################################################
from pymel.core import *

class AnimationClip():

    def __init__(self):
        self.name = None
        self.objectsKeyInfos = None
        self.startTime = None
        self.endTime = None
        
    def create(self, name, objects , startTime, endTime):
        self.name = name
        self.startTime = round(startTime, 10)
        self.endTime = round(endTime, 10)
        self.objectKeyInfos = []
        for obj in objects:
            obj = PyNode(obj)
            self.objectKeyInfos.append(self.ObjectKeyInfo().create(obj))
        return self
        
    def createXML(self):
        '''
        create XML represention of AnimationClip
        
        return:
        <AnimationClip name = clipName>
            <StartTime value = time>
            <EndTime value = time>
            <ObjectKeyInfo>
                ...
                <AttributeKeyInfo>
                    ...
            ...
            <ObjectKeyInfo>
            ...
        </AnimationClip>
        '''
        import xml.dom.minidom
        doc = xml.dom.minidom.Document()
        
        ac_element = doc.createElement('AnimationClip')
        ac_element.setAttribute('name', str(self.name))
        
        startTime_element = doc.createElement('StartTime')
        startTime_element.setAttribute('value', str(self.startTime))
        
        endTime_element = doc.createElement('EndTime')
        endTime_element.setAttribute('value', str(self.endTime))
        
        ac_element.appendChild(startTime_element)
        ac_element.appendChild(endTime_element)
        
        for x in self.objectKeyInfos:
            ac_element.appendChild(x.createXML())
        return ac_element
            
    def saveToXML(self, fileName):
        element = self.createXML()
        xml = element.toprettyxml()
        
        FILE = open(fileName , "w")
        FILE.writelines(xml)
        FILE.close()
        
        return xml
        
    def apply(self, newStartTime, searchReplace = {}, namespace = ":"):
        timeOffset = newStartTime - self.startTime
        for oki in self.objectKeyInfos:
            oki.apply(self.startTime+timeOffset, self.endTime+timeOffset, timeOffset, searchReplace = searchReplace, namespace = namespace)
        
    def readXML(self, fileName, element = None):
        import xml.dom.minidom
    
        AC_element = None
    
        if fileName:
            doc = xml.dom.minidom.parse(fileName)
            AC_element = doc.getElementsByTagName('AnimationClip')[0]
        
        if element:
            AC_element = element
        
        if not AC_element:
            print "AnimationClip.readXML:  WARNING file %s doesn't exist"%fileName
            return None
    
        
        self.name = AC_element.getAttribute('name')
    
        startTime_element = AC_element.getElementsByTagName('StartTime')[0]
        self.startTime = round(float(startTime_element.getAttribute('value')), 10)
            
        endTime_element = AC_element.getElementsByTagName('EndTime')[0]
        self.endTime = round(float(endTime_element.getAttribute('value')),10)
            
        self.objectKeyInfos = []
        objInfo_elements = AC_element.getElementsByTagName('ObjectKeyInfo')
        for element in objInfo_elements:
            self.objectKeyInfos.append(self.ObjectKeyInfo().readXML(element))
            
        return self
        
    def __eq__(self, other):
        if not (self.endTime - self.startTime) == (other.endTime - other.startTime):
            return False
        for soki in self.objectKeyInfos:
            matchFound = 0
            for ooki in other.objectKeyInfos:
                if matchFound:
                    pass
                if soki == ooki:
                    matchFound = 1
            if not matchFound:
                return False
        return True
            
        
    class ObjectKeyInfo():
        def __init__(self):
            self.obj = None
            self.attrKeyInfos = None
        
        def create(self, obj):
            obj = PyNode(obj)
            attrInfos = []
            allKeyable = obj.listAttr(keyable =1)
            for key in allKeyable:
                times = keyframe(key, q=1, tc =1)
                for time in times:
                    attrInfo = self.AttributeKeyInfo().create(key, time)
                    attrInfos.append(attrInfo)
            self.set(obj, attrInfos)
            return self
                    
        def set(self, obj, attrKeyInfos):
            self.obj = str(obj).split(":")[-1]
            self.attrKeyInfos = attrKeyInfos
        
        def createXML(self):
            '''
            create XML representation of ObjectKeyInfo
            
            return XML object
            ex
            <ObjectKeyInfo>
                <Object name = objectName>
                <AttributeKeyInfo>
                    ...
                <AttributeKeyInfo>
                    ...
                ...
            <ObjectKeyInfo>
            '''
            import xml.dom.minidom
            doc = xml.dom.minidom.Document()
            
            OKI_element = doc.createElement('ObjectKeyInfo')
            
            object_element = doc.createElement("Object")
            object_element.setAttribute('name', str(self.obj))
            OKI_element.appendChild(object_element)
            
            for x in self.attrKeyInfos:
                OKI_element.appendChild(x.createXML())
            
            return OKI_element
            
        def saveToXML(self, file):
            element = self.createXML()
            xml = element.toprettyxml()
            
            FILE = open(fileName , "w")
            FILE.writelines(xml)
            FILE.close()
            
            return xml
            
        
        def readXML(self, element, fileName = None):
            import xml.dom.minidom
        
            OKI_element = element
            
            if fileName:
                doc = xml.dom.minidom.parse(fileName)
                OKI_element = doc.getElementsByTagName('ObjectKeyInfo')
            
            obj_element = OKI_element.getElementsByTagName('Object')[0]
            self.obj = obj_element.getAttribute('name')
            
            attr_elements = OKI_element.getElementsByTagName('AttributeKeyInfo')
            self.attrKeyInfos = []
            for element in attr_elements:
                self.attrKeyInfos.append(self.AttributeKeyInfo().readXML(element))
                
            return self
            
        def __eq__(self, other):
            if not self.obj == other.obj:
                return False
            for saki in self.attrKeyInfos:
                matchFound = 0
                for oaki in other.attrKeyInfos:
                    if matchFound:
                        pass
                    if saki == oaki:
                        matchFound = 1
                if not matchFound:
                    return False
            return True
        
        def apply(self, startTime, endTime, timeOffset, searchReplace = {}, namespace = namespace):
            newObject = self.obj
            for old, new in searchReplace.items():
                newObject = newObject.replace(old, new)
            if not namespace.endswith(":"):
                namespace += ":"
            newObject = namespace + newObject
            if objExists(newObject):
                for attr in self.attrKeyInfos:
                    attr.apply(newObject, timeOffset)
            else:
                print "Warning: can't apply to object, %s doesn't exist"%newObject
        
        class AttributeKeyInfo():
            def __init__(self):
                self.attr = None
                self.time = None
                self.value = None
                self.inTangent = None
                self.outTangent = None
                self.inWeight = None
                self.outWeight = None
                self.inAngle = None
                self.outAngle = None
                
            def set(self, attrName, time, value, inTangent, outTangent, inWeight, outWeight, inAngle, outAngle):
                self.attr = attrName.split('.')[-1]
                self.time = round(time, 10)
                self.value = round(value, 10)
                self.inTangent = inTangent
                self.outTangent = outTangent
                self.inWeight = round(inWeight, 10)
                self.outWeight = round(outWeight, 10)
                self.inAngle = round(inAngle, 10)
                self.outAngle = round(outAngle, 10)
                return self
            
            
            def create(self,attr, time):
                attr = PyNode(attr)
                value = keyframe(attr, q=1,t = (time, time), vc=1)[0]
                inTangent = keyTangent(attr,t=(time, time), q=1,itt=1)[0]
                outTangent = keyTangent(attr,t=(time, time), q=1,ott=1)[0]
                inWeight = keyTangent(attr,t=(time, time), q=1, iw=1)[0]
                outWeight = keyTangent(attr,t=(time, time), q=1, ow=1)[0]
                inAngle = keyTangent(attr,t=(time, time), q=1, ia=1)[0]
                outAngle = keyTangent(attr,t=(time, time), q=1, oa=1)[0]
                return self.set(attr, time, value, inTangent, outTangent, inWeight, outWeight, inAngle, outAngle)
        
            def createXML(self):
                '''
                creates an XML representation of the attrubteKeyInfo
                
                return: XML object
                <AttribteKeyInfo>
                    <Attribute name = 'translateX'>
                    <Time value = 1.0>
                    <Value value = 1.0>
                    <InTangent value = 'Clamped'>
                    <OutTangent value = 'Clamped'>
                    <InWeight value = 1>
                    <OutWeight value = .5>
                </AttributeKeyInfo>
                '''
                import xml.dom.minidom
                doc = xml.dom.minidom.Document()
                AKI_element = doc.createElement('AttributeKeyInfo')
                attr_element = doc.createElement('Attribute')
                attr_element.setAttribute('name', str(self.attr))
                
                time_element = doc.createElement('Time')
                time_element.setAttribute('value', str(self.time))
                
                value_element = doc.createElement('Value')
                value_element.setAttribute('value', str(self.value))
                
                it_element = doc.createElement('InTangent')
                it_element.setAttribute('value', str(self.inTangent))
                
                ot_element = doc.createElement('OutTangent')
                ot_element.setAttribute('value', str(self.outTangent))
                
                iw_element = doc.createElement('InWeight')
                iw_element.setAttribute('value', str(self.inWeight))
                
                ow_element = doc.createElement('OutWeight')
                ow_element.setAttribute('value', str(self.outWeight))
                
                ia_element = doc.createElement('InAngle')
                ia_element.setAttribute('value', str(self.inAngle))
                
                oa_element = doc.createElement('OutAngle')
                oa_element.setAttribute('value', str(self.outAngle))
                
                AKI_element.appendChild(attr_element)
                AKI_element.appendChild(time_element)
                AKI_element.appendChild(value_element)
                AKI_element.appendChild(it_element)
                AKI_element.appendChild(ot_element)
                AKI_element.appendChild(iw_element)
                AKI_element.appendChild(ow_element)
                AKI_element.appendChild(ia_element)
                AKI_element.appendChild(oa_element)
                
                return AKI_element
                
            def saveToXML(self, file):
                element = self.createXML()
                xml = element.toprettyxml()
                
                FILE = open(fileName , "w")
                FILE.writelines(xml)
                FILE.close()
                
                return xml
                
            
            def readXML(self, element, fileName = None):
                import xml.dom.minidom
            
                AKI_element = element
            
                if fileName:
                    doc = xml.dom.minidom.parse(fileName)
                    AKI_element = doc.getElementsByTagName('AttributeKeyInfo')
                
                attr_element = AKI_element.getElementsByTagName('Attribute')[0]
                self.attr = attr_element.getAttribute('name')
                
                time_element = AKI_element.getElementsByTagName('Time')[0]
                self.time = round(float(time_element.getAttribute('value')), 10)
                
                value_element = AKI_element.getElementsByTagName('Value')[0]
                self.value = round(float(value_element.getAttribute('value')),10)
                
                inTangent_element = AKI_element.getElementsByTagName('InTangent')[0]
                self.inTangent = inTangent_element.getAttribute('value')
                
                outTangent_element = AKI_element.getElementsByTagName('OutTangent')[0]
                self.outTangent = outTangent_element.getAttribute('value')
                
                inWeight_element = AKI_element.getElementsByTagName('InWeight')[0]
                self.inWeight = round(float(inWeight_element.getAttribute('value')),10)
                
                outWeight_element = AKI_element.getElementsByTagName('OutWeight')[0]
                self.outWeight = round(float(outWeight_element.getAttribute('value')), 10)
                
                inAngle_element = AKI_element.getElementsByTagName('InAngle')[0]
                self.inAngle = round(float(inAngle_element.getAttribute('value')),10)
                
                outAngle_element = AKI_element.getElementsByTagName('OutAngle')[0]
                self.outAngle = round(float(outAngle_element.getAttribute('value')), 10)
                
                return self
                
            def apply(self, object, timeOffset):
                object = PyNode(object)
                if object.hasAttr(self.attr):
                    attr = object.attr(self.attr)
                    newTime = self.time+timeOffset
                    setKeyframe(attr, value = self.value , time = (newTime, newTime))
                    keyTangent(attr,e=1,t = (newTime, newTime), itt = self.inTangent)
                    keyTangent(attr,e=1, t = (newTime, newTime), ott = self.outTangent)
                    keyTangent(attr,e=1,t = (newTime, newTime), iw = self.inWeight)
                    keyTangent(attr,e=1,t = (newTime, newTime), ow = self.outWeight)
                    if self.inTangent == 'fixed':
                        keyTangent(attr,e=1,t = (newTime, newTime), ia = self.inAngle)
                    if self.inTangent == 'fixed':
                        keyTangent(attr,e=1,t = (newTime, newTime), oa = self.outAngle)
                else:
                    print "Warning: can't apply attribute: %s.%s doesn't exist"%(object, self.attr)
                
            def __eq__(self, other):
                if not self.attr == other.attr:
                    return False
                if not self.time == other.time:
                    return False
                if not self.value ==  other.value:
                    return False
                if not self.inTangent == other.inTangent:
                    return False
                if not self.outTangent == other.outTangent:
                    return False
                if not self.inWeight == other.inWeight:
                    return False
                if not self.outWeight == other.outWeight:
                    return False
                if not self.inAngle == other.inAngle:
                    return False
                if not self.outAngle == other.outAngle:
                    return False
                return True
                

    
##################################################################
#                    MISC/ NOT COMPLETE
##################################################################


def getAllAnims():
    pass

def isManagerNode():
    pass

def getSceneMangager():
    pass        
        
        
'''    
    jointSideEnums = {    "Center":0,
                        "Left":1,
                        "Right":2,
                        "None": 3}
                    
    jointLabelEnums = {    "None":0,
                        "Root":1,
                        "hip":2,
                        "knee":3,
                        "foot":4,
                        "toe":5,
                        "spine":6,
                        "neck":7,
                        "head": 8,
                        "collar":9,
                        "shoulder":10,
                        "elbow":11,
                        "hand":12,
                        "finger":13,
                        "thumb":14,
                        "propA":15,
                        "propB":16,
                        "propC":17,
                        "other":18,
                        "index finger":19,
                        "middle finger":20,
                        "ring finger":21,
                        "pinkyFinger":22,
                        "extra finger":23,
                        "big toe":24,
                        "index toe":25,
                        "middle toe":26,
                        "ring toe":27,
                        "pinky toe":28,
                        "extra toe":29}
'''                    
