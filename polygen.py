#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) [2021] [Joseph Zakar], [observing@gmail.com]
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
"""
Given the number of polygon sides, a profile to be generated perpendicular to
each side, and a straight line whose distance is the radius of the revolved
outline, this program generates (1) a paper model of one of the n sides with tabs
to assemble into a full 3D model; (2) the top and bottom lids for the generated
model; and (3) wrappers to cover each side of the generated model.
"""

import inkex
import math
import copy
import inspect

from inkex import PathElement, Style
from inkex.paths import Move, Line, ZoneClose, Path
from inkex.elements._groups import Group

class pathStruct(object):
    def __init__(self):
        self.id="path0000"
        self.path=Path()
        self.enclosed=False
        self.style = None
    def __str__(self):
        return self.path
    
class pnPoint(object):
   # This class came from https://github.com/JoJocoder/PNPOLY
    def __init__(self,p):
        self.p=p
    def __str__(self):
        return self.p
    def InPolygon(self,polygon,BoundCheck=False):
        inside=False
        if BoundCheck:
            minX=polygon[0][0]
            maxX=polygon[0][0]
            minY=polygon[0][1]
            maxY=polygon[0][1]
            for p in polygon:
                minX=min(p[0],minX)
                maxX=max(p[0],maxX)
                minY=min(p[1],minY)
                maxY=max(p[1],maxY)
            if self.p[0]<minX or self.p[0]>maxX or self.p[1]<minY or self.p[1]>maxY:
                return False
        j=len(polygon)-1
        for i in range(len(polygon)):
            if ((polygon[i][1]>self.p[1])!=(polygon[j][1]>self.p[1]) and (self.p[0]<(polygon[j][0]-polygon[i][0])*(self.p[1]-polygon[i][1])/( polygon[j][1] - polygon[i][1] ) + polygon[i][0])):
                    inside =not inside
            j=i
        return inside

class Polygen(inkex.EffectExtension):
    
    def add_arguments(self, pars):
        pars.add_argument("--usermenu")
        pars.add_argument("--polysides", type=int, default=6,\
            help="Number of Polygon Sides")
        pars.add_argument("--tabangle", type=float, default=45.0,\
            help="Angle of tab edges in degrees")
        pars.add_argument("--tabheight", type=float, default=0.4,\
            help="Height of tab in dimensional units")
        pars.add_argument("--cntroffset", type=float, default=0.4,\
            help="Offset from center in dimensional units")
        pars.add_argument("--dashlength", type=float, default=0.1,\
            help="Length of dashline in dimentional units (zero for solid line)")
        pars.add_argument("--linesonwrapper", type=inkex.Boolean, dest="linesonwrapper",\
            help="Put dashlines on wrappers")
        pars.add_argument("--unit", default="in",\
            help="Dimensional units of selected paths")

    #draw SVG line segment(s) between the given (raw) points
    def drawline(self, dstr, name, parent, sstr=None):
        line_style   = {'stroke':'#000000','stroke-width':'0.25','fill':'#eeeeee'}
        if sstr == None:
            stylestr = str(Style(line_style))
        else:
            stylestr = sstr
        el = parent.add(PathElement())
        el.path = dstr
        el.style = stylestr
        el.label = name

    def makepoly(self, toplength, numpoly):
      r = toplength/(2*math.sin(math.pi/numpoly))
      pstr = Path()
      for ppoint in range(0,numpoly):
         xn = r*math.cos(2*math.pi*ppoint/numpoly)
         yn = r*math.sin(2*math.pi*ppoint/numpoly)
         if ppoint == 0:
            pstr.append(Move(xn,yn))
         else:
            pstr.append(Line(xn,yn))
      pstr.append(ZoneClose())
      return pstr

    def insidePath(self, path, p):
        point = pnPoint((p.x, p.y))
        pverts = []
        for pnum in path:
            if pnum.letter == 'Z':
                pverts.append((path[0].x, path[0].y))
            else:
                pverts.append((pnum.x, pnum.y))
        isInside = point.InPolygon(pverts, True)
        return isInside # True if point p is inside path

    def makescore(self, pt1, pt2, dashlength):
        # Draws a dashed line of dashlength between two points
        # Dash = dashlength space followed by dashlength mark
        # if dashlength is zero, we want a solid line
        # Returns dashed line as a Path object
        apt1 = Line(0.0,0.0)
        apt2 = Line(0.0,0.0)
        ddash = Path()
        if math.isclose(dashlength, 0.0):
            #inkex.utils.debug("Draw solid dashline")
            ddash.append(Move(pt1.x,pt1.y))
            ddash.append(Line(pt2.x,pt2.y))
        else:
            if math.isclose(pt1.y, pt2.y):
                #inkex.utils.debug("Draw horizontal dashline")
                if pt1.x < pt2.x:
                    xcushion = pt2.x - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    xcushion = pt1.x - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if (xpt + dashlength*2) <= xcushion:
                        xpt = xpt + dashlength
                        ddash.append(Move(xpt,ypt))
                        xpt = xpt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            elif math.isclose(pt1.x, pt2.x):
                #inkex.utils.debug("Draw vertical dashline")
                if pt1.y < pt2.y:
                    ycushion = pt2.y - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    ycushion = pt1.y - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if(ypt + dashlength*2) <= ycushion:
                        ypt = ypt + dashlength         
                        ddash.append(Move(xpt,ypt))
                        ypt = ypt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            else:
                #inkex.utils.debug("Draw sloping dashline")
                if pt1.y > pt2.y:
                    apt1.x = pt1.x
                    apt1.y = pt1.y
                    apt2.x = pt2.x
                    apt2.y = pt2.y
                else:
                    apt1.x = pt2.x
                    apt1.y = pt2.y
                    apt2.x = pt1.x
                    apt2.y = pt1.y
                m = (apt1.y-apt2.y)/(apt1.x-apt2.x)
                theta = math.atan(m)
                msign = (m>0) - (m<0)
                ycushion = apt2.y + dashlength*math.sin(theta)
                xcushion = apt2.x + msign*dashlength*math.cos(theta)
                xpt = apt1.x
                ypt = apt1.y
                done = False
                while not(done):
                    nypt = ypt - dashlength*2*math.sin(theta)
                    nxpt = xpt - msign*dashlength*2*math.cos(theta)
                    if (nypt >= ycushion) and (((m<0) and (nxpt <= xcushion)) or ((m>0) and (nxpt >= xcushion))):
                        # move to end of space / beginning of mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Move(xpt,ypt))
                        # draw the mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
        return ddash

    def detectIntersect(self, x1, y1, x2, y2, x3, y3, x4, y4):
        td = (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
        if td == 0:
            # These line segments are parallel
            return False
        t = ((x1-x3)*(y3-y4)-(y1-y3)*(x3-x4))/td
        if (0.0 <= t) and (t <= 1.0):
            return True
        else:
            return False

    def orientTab(self,pt1,pt2,height,angle,theta,orient):
        tpt1 = Line(0.0,0.0)
        tpt2 = Line(0.0,0.0)
        tpt1.x = pt1.x + orient[0]*height + orient[1]*height/math.tan(math.radians(angle))
        tpt2.x = pt2.x + orient[2]*height + orient[3]*height/math.tan(math.radians(angle))
        tpt1.y = pt1.y + orient[4]*height + orient[5]*height/math.tan(math.radians(angle))
        tpt2.y = pt2.y + orient[6]*height + orient[7]*height/math.tan(math.radians(angle))
        if not math.isclose(theta, 0.0):
            t11 = Path([Move(pt1.x,pt1.y),Line(tpt1.x, tpt1.y)])
            t12 = Path([Move(pt1.x,pt1.y),Line(tpt2.x, tpt2.y)])
            thetal1 = t11.rotate(theta, [pt1.x,pt1.y])
            thetal2 = t12.rotate(theta, [pt2.x,pt2.y])
            tpt1.x = thetal1[1].x
            tpt1.y = thetal1[1].y
            tpt2.x = thetal2[1].x
            tpt2.y = thetal2[1].y
        return tpt1,tpt2

    def makeTab(self, tpath, pt1, pt2, tabht, taba):
        # tpath - the pathstructure containing pt1 and pt2
        # pt1, pt2 - the two points where the tab will be inserted
        # tabht - the height of the tab
        # taba - the angle of the tab sides
        # returns the two tab points (Line objects) in order of closest to pt1
        tpt1 = Line(0.0,0.0)
        tpt2 = Line(0.0,0.0)
        currTabHt = tabht
        currTabAngle = taba
        testAngle = 1.0
        testHt = currTabHt * 0.001
        adjustTab = 0
        tabDone = False
        while not tabDone:
            # Let's find out the orientation of the tab
            if math.isclose(pt1.x, pt2.x):
                # It's vertical. Let's try the right side
                if pt1.y < pt2.y:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,1,0,-1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,1,0,-1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,1,0,-1]) # Guessed right
                else: # pt2.y < pt1.y
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,-1,0,1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,-1,0,1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,-1,0,1]) # Guessed right
            elif math.isclose(pt1.y, pt2.y):
                # It's horizontal. Let's try the top
                if pt1.x < pt2.x:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,1,0,-1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                else: # pt2.x < pt1.x
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,-1,0,1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,-1,0,-1,0]) # Guessed right

            else: # the orientation is neither horizontal nor vertical
                # Let's get the slope of the line between the points
                # Because Inkscape's origin is in the upper-left corner,
                # a positive slope (/) will yield a negative value
                slope = (pt2.y - pt1.y)/(pt2.x - pt1.x)
                # Let's get the angle to the horizontal
                theta = math.degrees(math.atan(slope))
                # Let's construct a horizontal tab
                seglength = math.sqrt((pt1.x-pt2.x)**2 +(pt1.y-pt2.y)**2)
                if slope < 0.0:
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
                else: # slope > 0.0
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,+1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
            # Check to see if any tabs intersect each other
            if self.detectIntersect(pt1.x, pt1.y, tpt1.x, tpt1.y, pt2.x, pt2.y, tpt2.x, tpt2.y):
                # Found an intersection.
                if adjustTab == 0:
                    # Try increasing the tab angle in one-degree increments
                    currTabAngle = currTabAngle + 1.0
                    if currTabAngle > 88.0: # We're not increasing the tab angle above 89 degrees
                        adjustTab = 1
                        currTabAngle = taba
                if adjustTab == 1:
                    # So, try reducing the tab height in 20% increments instead
                    currTabHt = currTabHt - tabht*0.2 # Could this lead to a zero tab_height?
                    if currTabHt <= 0.0:
                        # Give up
                        currTabHt = tabht
                        adjustTab = 2
                if adjustTab == 2:
                    tabDone = True # Just show the failure
            else:
                tabDone = True
            
        return tpt1,tpt2

    def BuildPolyside(self, npaths, outlpath, radpath, yorient, layer, polysides, lines_on_wrapper, dashlength, tab_height, tab_angle, groupid="0"):
        dscore = Path() # Used for building dashlines for model
        dwscore = Path() # Used for building dashlines for wrapper
        if yorient:
            # Make sure the outline's points are ordered in ascending Y
            if npaths[outlpath].path[0].y < npaths[outlpath].path[0].y:
                npaths[outlpath].path.reverse()
            # construct the side panel
            xpos = ypos = 0.0
            lhs = Path() # Left hand side of panel
            rhs = Path() # Right hand side of panel
            for npoint in range(len(npaths[outlpath].path)):
                pr = abs(npaths[radpath].path[0].x - npaths[outlpath].path[npoint].x)
                pwidth = 2.0*pr*math.tan(math.pi/polysides)
                pR = pr/math.cos(math.pi/polysides)
                if npoint == 0:
                    topR = pR
                    topw = pwidth
                    lhs.append(Move(xpos - pwidth/2,ypos))
                    rhs.append(Move(xpos + pwidth/2,ypos))
                else:
                    seglength = math.sqrt((npaths[outlpath].path[npoint-1].x - npaths[outlpath].path[npoint].x)**2 + \
                                          (npaths[outlpath].path[npoint-1].y - npaths[outlpath].path[npoint].y)**2)
                    ypos += seglength
                    lhs.append(Line(xpos - pwidth/2,ypos))
                    rhs.append(Line(xpos + pwidth/2,ypos))
                    if npoint == len(npaths[outlpath].path)-1:
                        bottomR = pR
                        bottomw = pwidth
            # Put score marks across the panel
            for pcnt in range(len(lhs)):
                if (pcnt != 0) and (pcnt != (len(lhs)-1)):
                    dscore.append(self.makescore(lhs[pcnt], rhs[pcnt], dashlength))
            dwscore = dscore.copy() # wrapper only needs these scorelines
            rhs=rhs.reverse() # Reverse the order so we can create a closed path
            cpath = pathStruct()
            cpath.enclosed = False
            cpath.id = 'panel'
            cpath.path = lhs + rhs
            # add tabs to panel
            dprop = Path() # Used for building the main path
            dwrap = Path() # Used for building the wrapper
            for ptn in range(len(cpath.path)):
                if ptn == 0:
                    dprop.append(Move(cpath.path[ptn].x,cpath.path[ptn].y))
                    dwrap.append(Move(cpath.path[ptn].x,cpath.path[ptn].y))
                else:
                    if ptn > (len(npaths[outlpath].path)-1):
                        dscore += self.makescore(cpath.path[ptn-1], cpath.path[ptn],dashlength)
                        tabpt1, tabpt2 = self.makeTab(cpath, cpath.path[ptn-1], cpath.path[ptn], tab_height, tab_angle)
                        dprop.append(tabpt1)
                        dprop.append(tabpt2)
                    dprop.append(Line(cpath.path[ptn].x,cpath.path[ptn].y))
                    dwrap.append(Line(cpath.path[ptn].x,cpath.path[ptn].y))
                    if ptn == len(cpath.path)-1:
                        tabpt1, tabpt2 = self.makeTab(cpath, cpath.path[ptn], cpath.path[0], tab_height, tab_angle)
                        dprop.append(tabpt1)
                        dprop.append(tabpt2)
                        dprop.append(ZoneClose())
                        dscore.append(self.makescore(cpath.path[ptn], cpath.path[0],dashlength))
                        dwrap.append(ZoneClose())
            if npaths[outlpath].style != None:
                lsstr = npaths[outlpath].style.split(';')
                replacedit = False
                for stoken in range(len(lsstr)):
                    if lsstr[stoken].startswith('fill'):
                        swt = lsstr[stoken].split(':')[1]
                        swf = '#eeeeee'
                        lsstr[stoken] = lsstr[stoken].replace(swt, swf)
                        replacedit = True
                if not replacedit:
                    lsstr.append("\'fill\':\'#eeeeee\'")
                sstr = ";".join(lsstr)
            if math.isclose(dashlength, 0.0):
                # lump together all the score lines
                groupm = Group()
                groupm.label = "group"+groupid+"ms"
                self.drawline(str(dprop),'model',groupm,sstr) # Output the model
                self.drawline(str(dscore),'mscore',groupm,sstr) # Output the scorelines separately
                layer.append(groupm)
                if lines_on_wrapper:
                    groupw = Group()
                    groupw.label = "group"+groupid+"ws"
                    self.drawline(str(dwrap),'wrapper',groupw,sstr) # Output the model
                    self.drawline(str(dwscore),'wscore',groupw,sstr) # Output the scorelines separately
                    layer.append(groupw)
                else: # Just the wrapper
                    self.drawline(str(dwrap),npaths[outlpath].id+"ws",layer,sstr) # Output the model
            else:
                dprop = dscore + dprop
                self.drawline(str(dprop),npaths[outlpath].id+"ms",layer,sstr)
                if lines_on_wrapper:
                    dwrap = dwscore + dwrap
                self.drawline(str(dwrap),npaths[outlpath].id+"ws",layer,sstr)
        return topw,bottomw,sstr

    def effect(self):
        scale = self.svg.unittouu('1'+self.options.unit)
        layer = self.svg.get_current_layer()
        polysides = int(self.options.polysides)
        tab_angle = float(self.options.tabangle)
        tab_height = float(self.options.tabheight) * scale
        cntroffset = float(self.options.cntroffset) * scale
        dashlength = float(self.options.dashlength) * scale
        lines_on_wrapper = self.options.linesonwrapper
        if not math.isclose(cntroffset, 0.0, abs_tol = 1e-09):
            # Make sure polysides is 4
            if polysides != 4:
                inkex.errormsg("INFO: A non-zero Offset from the centerline requires exactly four sides. Ignoring Number of Polygon sides specified.")
                polysides = 4
        npaths = []
        elems = []
        sstr = None
        radpath = 0 # Initial assumption is that first path is the radius
        outlpath = 1 # and second path is the outline
        yorient = True # assuming we are revolving around the Y axis
        for selem in self.svg.selection.filter(PathElement):
            elems.append(copy.deepcopy(selem))
        if len(elems) == 0:
            raise inkex.AbortExtension("ERROR: Nothing selected")
        elif len(elems) != 2:
            raise inkex.AbortExtension("ERROR: Select only the outline and its radius line\n"\
                                       +"Nothing more or less.")
        for elem in elems: # for each path
            escale = 1.0
            if 'transform' in elem.attrib:
                transforms = elem.attrib['transform'].split()
                for tf in transforms:
                    if tf.startswith('scale'):
                        escale = float(tf.split('(')[1].split(')')[0])
                if 'style' in elem.attrib:
                    lsstr = elem.attrib['style'].split(';')
                    for stoken in range(len(lsstr)):
                        if lsstr[stoken].startswith('stroke-width'):
                            swt = lsstr[stoken].split(':')[1]
                            if not swt[2:].isalpha(): # is value expressed in units (e.g. px)?
                                swf = str(float(swt)*escale) # no. scale it
                                lsstr[stoken] = lsstr[stoken].replace(swt, swf)
                        if lsstr[stoken].startswith('stroke-miterlimit'):
                            swt = lsstr[stoken].split(':')[1]
                            if not swt[2:].isalpha(): # is value expressed in units (e.g. px)?
                                swf = str(float(swt)*escale) # no. scale it
                                lsstr[stoken] = lsstr[stoken].replace(swt, swf)
                    sstr = ";".join(lsstr)
                else:
                    sstr = None
                elem.apply_transform()
            last_letter = 'Z'
            for ptoken in elem.path.to_absolute(): # For each point in the path
                if ptoken.letter == 'M': # Starting point
                    # Hold this point in case we receive a Z
                    ptx1 = mx = ptoken.x
                    pty1 = my = ptoken.y
                    '''
                    Assign a structure to the new path. We assume that there is
                    only one path and, therefore, it isn't enclosed by a
                    sub-path. However, we'll suffix the ID, if we find a
                    sub-path.
                    '''
                    npath = pathStruct()
                    npath.enclosed = False
                    npath.id = elem.get_id()
                    if sstr == None:
                        if 'style' in elem.attrib:
                            npath.style = elem.attrib['style']
                    else:
                        npath.style = sstr
                    npath.path.append(Move(ptx1,pty1))
                else:
                    if last_letter != 'M':
                        ptx1 = ptx2
                        pty1 = pty2
                    if ptoken.letter == 'L':
                        ptx2 = ptoken.x
                        pty2 = ptoken.y
                    elif ptoken.letter == 'H':
                        ptx2 = ptoken.x
                        pty2 = pty1
                    elif ptoken.letter == 'V':
                        ptx2 = ptx1
                        pty2 = ptoken.y
                    elif ptoken.letter == 'Z':
                        raise inkex.AbortExtension("ERROR: Paths must be open")
                    else:
                        raise inkex.AbortExtension("ERROR: Unrecognized path command {0}".format(ptoken.letter))
                    npath.path.append(Line(ptx2,pty2))
                last_letter = ptoken.letter
            npaths.append(npath)
                
        # Let's validate the input
        if len(npaths[1].path) == 2:
            # Our initial assumption was wrong
            radpath = 1
            outlpath = 0
        if math.isclose(npaths[radpath].path[0].y,npaths[radpath].path[1].y):
            # Guessed wrong. For now, we're just going to abort
            # TODO: Support revolving around the X axis
            raise inkex.AbortExtension("ERROR: This extension can only revolve about the Y axis")
        '''
        The model will be open at the top and the bottom, so we have to calculate
        the size of the polygons that will cover them. We were given the number
        of sides.
        '''
        topw0, bottomw0, sstr0 = self.BuildPolyside(npaths, outlpath, radpath, yorient, layer, polysides, lines_on_wrapper, dashlength, tab_height, tab_angle, "0")
        if math.isclose(cntroffset, 0.0):
            # Generate the top and bottom polygons
            self.drawline(str(self.makepoly(topw0, polysides)),npaths[outlpath].id+"lid0",layer,sstr0)
            self.drawline(str(self.makepoly(bottomw0, polysides)),npaths[outlpath].id+"lid1",layer,sstr0)
        else: # Special case: we're doing a rectangular shape
            npaths[radpath].path[0].x += cntroffset
            npaths[radpath].path[1].x += cntroffset
            topw1, bottomw1, sstr1 = self.BuildPolyside(npaths, outlpath, radpath, yorient, layer, polysides, lines_on_wrapper, dashlength, tab_height, tab_angle, "1")
            dprop = Path()
            dprop.append(Move(0.0,0.0))
            dprop.append(Line(topw0,0.0))
            dprop.append(Line(topw0,topw1))
            dprop.append(Line(0.0,topw1))
            dprop.append(ZoneClose())
            self.drawline(str(dprop),npaths[outlpath].id+"lid0",layer,sstr0)
            dprop = Path()
            dprop.append(Move(0.0,0.0))
            dprop.append(Line(bottomw0,0.0))
            dprop.append(Line(bottomw0,bottomw1))
            dprop.append(Line(0.0,bottomw1))
            dprop.append(ZoneClose())
            self.drawline(str(dprop),npaths[outlpath].id+"lid1",layer,sstr1)
                        
        
if __name__ == '__main__':
    Polygen().run()
