#!/usr/bin/env python
import sys
sys.path.append('../build')
import libry as ry
import numpy as np
import time
import cv2 as cv
import glob
import os
print(cv.__version__)
from utils import *


SCENE_FILE = "../scenarios/ball_deflector_scene.g"

class BallDeflector:
    def __init__(self, perceptionMode='cheat', exportVideoMode = False, debug = False):
        self.tau = 0.01
        self.t = 0
        self.debug = debug

        self.setupSim()
        self.setupC()


        self.exportVideoMode = exportVideoMode
        if self.exportVideoMode:
            self.speed_scale = 2
            self.extraFrameList = []
            os.system("mkdir -p images/sim_view")
            os.system("mkdir -p images/config_view")
            os.system("mkdir -p images/cam_rgb_view")
            os.system("rm -r ./images/sim_view/*.png")
            os.system("rm -r ./images/config_view/*.png")
            os.system("rm -r ./images/cam_rgb_view/*.png")

        self.perceptionMode = perceptionMode
        if perceptionMode == 'komo': self.setupKomoPerception()


    def stepTime(self):
        self.t += 1
        if self.t % self.speed_scale == 0 and self.exportVideoMode :
            self.exportScreenshot()

    def runSim(self, time_interval):
        print('===== Running Sim for ',time_interval ,' units =====')
        for i in range(time_interval):
            if self.t % 50 == 0 and self.debug:
                if(self.perceptionMode == 'cheat'):
                    position, errPer = self.RealWorld.getFrame(self.targetFrame).getPosition()
                elif(self.perceptionMode == 'komo'):
                    position, errPer = self.perceptionGetPosition(self.targetFrame)
                self.createBallFrame('real_ball'+str(i),position,[0,0,0,1],color = [0,1,1,0.3])
            time.sleep(self.tau)
            self.S.step([], self.tau, ry.ControlMode.none)
            self.C.setJointState(self.S.get_q())
            self.V.setConfiguration(self.C)
            self.stepTime()

    def exportScreenshot(self):
        frame_num = int(self.t / self.speed_scale)
        frame_num = str(frame_num)
        frame_num = frame_num.zfill(5)
        img_name = "img-"+frame_num+".png"

        img = self.S.getScreenshot()
        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        img = cv.flip(img, 0 )
        cv.imwrite("images/sim_view/"+img_name, img)


        img = self.V.getScreenshot()
        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        img = cv.flip(img, 0 )
        cv.imwrite("images/config_view/"+img_name, img)

        [img,depth] = self.S.getImageAndDepth()
        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
        # img = cv.flip(img, 0 )
        cv.imwrite("images/cam_rgb_view/"+img_name, img)

        # depth =  cv.cvtColor(depth, cv.IMREAD_GRAYSCALE)
        # depth = cv.flip(depth, 0 )
        # cv.imwrite("images/cam_depth/"+str(self.t)+".png", depth)


    def convertToVideo(self):
        img_array = []
        files = glob.glob('./images/*.png')
        files.sort(key=os.path.getmtime)
        for filename in files:
            img = cv.imread(filename)
            height, width, layers = img.shape
            size = (width,height)
            img_array.append(img)

        out = cv.VideoWriter('./output/project.avi',cv.VideoWriter_fourcc(*'DIVX'), 15, size)

        for i in range(len(img_array)):
            out.write(img_array[i])
        out.release()

        # os.system("rm -r ./images/*.png")


    def selectBall(self, ballFrame):
        if ballFrame == 'ball1':
            colorMode = 'r'
        elif ballFrame == 'ball2':
            colorMode = 'g'
        elif ballFrame == 'ball3':
            colorMode = 'b'
        else:
            colorMode = 'invalid'

        print('============',ballFrame,' selects ',colorMode, ' color ==============')
        # input()

        self.colorMode = colorMode
        self.setTarget(ballFrame)

    def setTarget(self, ballFrame):
        self.targetFrame = ballFrame
        #you can also change the shape & size
        self.targetObj = self.RealWorld.getFrame(ballFrame)
        self.targetObj.setContact(1)
        self.obj = self.createBallFrame(ballFrame, targetPosition = [0,0,0], color = [0,1,1,0.3], contact = 1 )

        # input()

    def createBallFrame(self, targetFrame, targetPosition = [0,0,0], targetQuaternion = [0,0,0,1], color = [0,1,0,0.3], contact = 1 ):
        obj = self.C.addFrame(targetFrame)
        obj.setShape(ry.ST.sphere, [.05])
        obj.setColor(color)
        obj.setContact(contact)
        obj.setPosition(targetPosition)
        obj.setQuaternion(targetQuaternion)
        self.V.setConfiguration(self.C)
        self.extraFrameList.append(targetFrame)
        return obj

    def clearExtraFrames(self):
        for frame in self.extraFrameList:
            self.C.delFrame(frame)
            print('Deleting frame : ', frame)
        self.V.setConfiguration(self.C)


    def setupSim(self):
        #-- REAL WORLD configuration, which is attached to the physics engine
        self.RealWorld = ry.Config()
        self.RealWorld.addFile(SCENE_FILE)

        # testBall = self.RealWorld.getFrame('ball3')
        # objectPosition = self.testBall.getPosition()
        # testBall.setPosition([1, 0, .5])

        # Configure Physics Engine
        self.S = self.RealWorld.simulation(ry.SimulatorEngine.physx, True)
        # Attach Camera Sensor
        self.S.addSensor("camera")

        # Record Initial Position of Robot A
        self.q0 = self.S.get_q()

    def setupC(self):
        #-- MODEL WORLD configuration, this is the data structure on which you represent
        # what you know about the world and compute things (controls, contacts, etc)
        self.C = ry.Config()
        self.C.addFile(SCENE_FILE)

        self.C.delFrame("ball1")
        self.C.delFrame("ball2")
        self.C.delFrame("ball3")

        #-- using the viewer, you can view configurations or paths
        self.V = ry.ConfigurationViewer()
        self.V.setConfiguration(self.C)
        self.cameraFrame = self.C.frame("camera")

        #the focal length
        self.f = 0.895
        self.f = self.f * 360.
        self.fxfypxpy = [self.f, self.f, 320., 180.]
        self.V.setConfiguration(self.C)

    def setupKomoPerception(self):
        self.perceptionC = ry.Config()
        self.komoBallFrame = "ball"

        table = self.perceptionC.addFrame("table")
        table.setPosition(self.C.frame("table").getPosition())
        table.setShape(ry.ST.ssBox, self.S.getGroundTruthSize("table"))

        self.percepObj = self.perceptionC.addFrame(self.komoBallFrame)
        self.percepObj.setShape(ry.ST.sphere, [.05])
        self.percepObj.setContact(1)
        self.perceptionC.makeObjectsFree([self.komoBallFrame])
        # self.percepObj.setQuaternion([1,1,0,0])

    def komoBallPose(self,obj_points, num_batch = 5):
        num_obj = int(obj_points.shape[0]/num_batch)
        # permutation = np.random.permutation(obj_points.shape[0])
        permutation = np.arange(obj_points.shape[0])
        for b in range(num_batch):
            for o in range(num_obj):
                name = "pointCloud%i" % o
                obj = self.perceptionC.addFrame(name)
                obj.setShape(ry.ST.sphere, [.001])
                obj.setContact(0)
                indices = permutation[o+num_obj*b]
                obj.setPosition(obj_points[indices])

            komo = self.perceptionC.komo_path(1.,1,self.tau,True)
            komo.clearObjectives()
            # komo.add_qControlObjective(order=1, scale=1e3) # Prior
            # komo.addSquaredQuaternionNorms(0., 1., 1e2)
            # if not self.S.getGripperIsGrasping("A_gripper"):
                # komo.addObjective([1.], ry.FS.distance, [self.komoBallFrame, "table"], ry.OT.eq, [1e2])
                # komo.addObjective([], ry.FS.vectorY, [self.komoBallFrame], ry.OT.eq, [1e2], order=1)
            # komo.addObjective([], ry.FS.accumulatedCollisions, type=ry.OT.ineq, scale=[1e1])
            for o in range(num_obj):
                name = "pointCloud%i" % o
                komo.addObjective([1.], ry.FS.distance, [self.komoBallFrame, name], ry.OT.sos, [1e0], target = [.001]) # Likelihood
            komo.optimize()

            self.perceptionC.setFrameState(komo.getConfiguration(0))
            p_obj = self.percepObj.getPosition()
            q_obj = self.percepObj.getQuaternion()
            for o in range(num_obj):
                name = "pointCloud%i" % o
                self.perceptionC.delFrame(name)

        return p_obj, q_obj


    def perceptionGetPosition(self, ballFrame):
        position = [0,0,0]
        # grab sensor readings from the simulation & set the model object to percept
        [rgb, depth] = self.S.getImageAndDepth()
        if self.perceptionMode == 'cheat': #TOTAL CHEAT: grab the true position from the RealWorld
            objectPosition = self.targetObj.getPosition()
            objectQuaternion = self.targetObj.getQuaternion()
            self.obj.setPosition(objectPosition)
            self.obj.setQuaternion(objectQuaternion)
            self.V.setConfiguration(self.C)
            errPer = 0.
        elif self.perceptionMode == 'komo':
            obj_points, rel_points, masked_rgb = find_pixels(rgb, depth, self.cameraFrame, self.fxfypxpy, self.colorMode)
            self.cameraFrame.setPointCloud(rel_points, masked_rgb)
            self.V.recopyMeshes(self.C)
            errPer = np.inf
            if len(obj_points)>0:
                p_obj, q_obj = self.komoBallPose(obj_points)
                errPer = np.abs(self.obj.getPosition()-self.targetObj.getPosition()).max() # only for print
                self.obj.setPosition(p_obj)
                self.obj.setQuaternion(q_obj)
                self.V.setConfiguration(self.C)
            position = self.obj.getPosition()
        else:
            print('perceptionMode was not defined well!!')
        print('obj position', position)
        return position, errPer


    def testPerception(self, ballFrame, simTime):
        for i in range(simTime):
            pos,errPer=self.perceptionGetPosition(ballFrame)
            self.S.step([], self.tau, ry.ControlMode.none)
            print('t: {:.1f}, Perception Error: {:.3f}'.format(self.t*self.tau, errPer))
            print('t: {:.1f}, True: {}, Estimated: {}'.format(self.t*self.tau, self.targetObj.getPosition(), self.obj.getPosition()))
            self.stepTime()

    def openGripper(self, robotName):
        gripperFrame = robotName + "_gripper"
        print('===== Opening =====')
        self.S.openGripper(gripperFrame)
        self.C.attach("world", self.targetFrame)
        for i in range(50):
            time.sleep(self.tau)
            self.S.step([], self.tau, ry.ControlMode.none)
            self.C.setJointState(self.S.get_q())
            self.V.setConfiguration(self.C)
            self.stepTime()
        print('===== Done Opening =====')

    def align(self, robotName):
        gripperCenterFrame = robotName + "_gripperCenter"
        gripperFingerFrame = robotName + "_finger1"
        print('===== Aligning =====')
        T = 30
        self.C.setJointState(self.S.get_q())
        komo = self.C.komo_path(1.,T,T*self.tau,True)
        komo.addObjective([1.], ry.FS.positionDiff, [gripperCenterFrame, self.targetFrame], ry.OT.eq, [2e1], target=[0,0,0.1+0.03])
        komo.addObjective([1.], ry.FS.vectorZ, [gripperCenterFrame], ry.OT.eq, scale=[1e1], target=[0,0,1]);
        komo.addObjective([1.], ry.FS.scalarProductYX, [gripperCenterFrame, self.targetFrame], ry.OT.eq);
        komo.addObjective([1.], ry.FS.scalarProductYY, [gripperCenterFrame, self.targetFrame], ry.OT.eq);
        komo.addObjective([], ry.FS.accumulatedCollisions, type=ry.OT.ineq, scale=[1e1])
        komo.addObjective([], ry.FS.qItself, [gripperFingerFrame], ry.OT.eq, [1e1], order=1)
        komo.addObjective([1.], ry.FS.qItself, [], ry.OT.eq, [1e1], order=1)
        komo.optimize()
        for t in range(T):
            self.C.setFrameState(komo.getConfiguration(t))
            q = self.C.getJointState()
            time.sleep(self.tau)
            self.S.step(q, self.tau, ry.ControlMode.position)
            self.V.setConfiguration(self.C)
            self.stepTime()

        print('===== Done Aligning =====')

    def alignDeflector(self, robotName):
        gripperCenterFrame = robotName + "_gripperCenter"
        gripperFingerFrame = robotName + "_finger1"
        print('===== Aligning =====')
        T = 30
        self.C.setJointState(self.S.get_q())
        komo = self.C.komo_path(1.,T,T*self.tau,True)
        komo.addObjective([1.], ry.FS.positionDiff, [gripperCenterFrame, self.targetFrame], ry.OT.eq, [2e1], target=[0.01,0,0.8])
        komo.addObjective([1.], ry.FS.vectorZ, [gripperCenterFrame], ry.OT.eq, scale=[1e1], target=[0,0,1]);
        komo.addObjective([1.], ry.FS.scalarProductYX, [gripperCenterFrame, self.targetFrame], ry.OT.eq);
        komo.addObjective([1.], ry.FS.scalarProductYY, [gripperCenterFrame, self.targetFrame], ry.OT.eq);
        komo.addObjective([], ry.FS.accumulatedCollisions, type=ry.OT.ineq, scale=[1e1])
        komo.addObjective([], ry.FS.qItself, [gripperFingerFrame], ry.OT.eq, [1e1], order=1)
        komo.addObjective([1.], ry.FS.qItself, [], ry.OT.eq, [1e1], order=1)
        komo.optimize()
        for t in range(T):
            self.C.setFrameState(komo.getConfiguration(t))
            q = self.C.getJointState()
            time.sleep(self.tau)
            self.S.step(q, self.tau, ry.ControlMode.position)
            self.V.setConfiguration(self.C)
            self.stepTime()

        print('===== Done Aligning =====')

    def pick(self, robotName):
        gripperCenterFrame = robotName + "_gripperCenter"
        gripperFrame = robotName + "_gripper"
        gripperFingerFrame = robotName + "_finger1"
        T = 20
        self.C.setJointState(self.S.get_q())
        komo = self.C.komo_path(1.,T,T*self.tau,True)
        target = self.C.getFrame(gripperCenterFrame).getPosition()
        target[-1] -= 0.12
        komo.addObjective([1.], ry.FS.position, [gripperCenterFrame], ry.OT.eq, [2e1], target=target)
        komo.addObjective([], ry.FS.quaternion, [gripperCenterFrame], ry.OT.eq, scale=[1e1], order=1)
        komo.addObjective([], ry.FS.accumulatedCollisions, type=ry.OT.ineq, scale=[1e1])
        komo.addObjective([], ry.FS.qItself, [gripperFingerFrame], ry.OT.eq, [1e1], order=1)
        komo.addObjective([1.], ry.FS.qItself, [], ry.OT.eq, [1e1], order=1)
        komo.optimize()
        for t in range(T):
            self.C.setFrameState(komo.getConfiguration(t))
            q = self.C.getJointState()
            time.sleep(self.tau)
            self.S.step(q, self.tau, ry.ControlMode.position)
            self.V.setConfiguration(self.C)
            self.stepTime()
        self.S.closeGripper(gripperFrame)
        print('===== Closed =====')
        while True:
            time.sleep(self.tau)
            self.S.step([], self.tau, ry.ControlMode.none)
            self.C.setJointState(self.S.get_q())
            self.V.setConfiguration(self.C)
            self.stepTime()
            if self.S.getGripperIsGrasping(gripperFrame):
                print('===== Done Closing =====')
                self.C.attach(gripperFrame, self.targetFrame)
                return True
            if self.S.getGripperWidth(gripperFrame)<-0.05 :
                print('===== Failed to Close =====')
                return False


    def moveToDest(self, robotName, targetPose):
        gripperCenterFrame = robotName + "_gripperCenter"
        gripperFingerFrame = robotName + "_finger1"
        # print('===== Lifting =====')
        T = 30
        self.C.setJointState(self.S.get_q())
        komo = self.C.komo_path(1.,T,T*self.tau,True)
        # target[:2] = (np.random.rand(2)-.5)/3
        komo.addObjective([1.], ry.FS.position, [gripperCenterFrame], ry.OT.eq, [2e1], target=targetPose)
        komo.addObjective([], ry.FS.accumulatedCollisions, type=ry.OT.ineq, scale=[1e1])
        komo.addObjective([], ry.FS.qItself, [gripperFingerFrame], ry.OT.eq, [1e1], order=1)
        komo.addObjective([1.], ry.FS.qItself, [], ry.OT.eq, [1e1], order=1)
        komo.optimize()
        for t in range(T):
            self.C.setFrameState(komo.getConfiguration(t))
            q = self.C.getJointState()
            self.S.step(q, self.tau, ry.ControlMode.position)
            self.V.setConfiguration(self.C)
            self.stepTime()
            time.sleep(self.tau)

        # print('===== Done Lifting =====')

    def moveToInit(self):
        print('===== Go to Initial Pose =====')
        T = 30
        self.C.setJointState(self.S.get_q())
        komo = self.C.komo_path(1.,T,T*self.tau,True)
        komo.addObjective([1.], ry.FS.qItself, [], ry.OT.eq, [2e1], target=self.q0)
        komo.addObjective([], ry.FS.accumulatedCollisions, type=ry.OT.ineq, scale=[1e1])
        komo.addObjective([1.], ry.FS.qItself, [], ry.OT.eq, [1e1], order=1)
        komo.optimize()
        for t in range(T):
            self.C.setFrameState(komo.getConfiguration(t))
            q = self.C.getJointState()
            self.S.step(q, self.tau, ry.ControlMode.position)
            self.V.setConfiguration(self.C)
            self.stepTime()
            time.sleep(self.tau)

        print('===== At Initial Pose =====')

    def destroy(self):
        self.S = 0
        self.C = 0
        self.V = 0
        # if self.exportVideoMode:
        #     self.convertToVideo()

    def pickAndLift(self, robotName, targetFrame):
        self.setTarget(targetFrame)
        self.openGripper(robotName)
        self.moveToInit()
        self.perception()
        self.align(robotName)
        # input()
        success = self.pick(robotName)
        if success:
            self.moveToDest(robotName)
            print('====== Done ======')
        # input()

    def pickAndPlace(self, robotName, ballFrame, destFrame):
        self.setTarget(ballFrame)
        self.openGripper(robotName)
        self.moveToInit()
        self.perceptionGetPosition(ballFrame)
        self.align(robotName)
        # input()
        success = self.pick(robotName)
        if success:
            targetPose = self.C.getFrame(destFrame).getPosition()
            targetPose[2] += 0.75
            targetPose[0] -= 0
            self.moveToDest(robotName,targetPose)
            self.openGripper(robotName)
            print('====== Done ======')
            # input()


    def deflectBall(self, robotName, ballFrame,binFrame):
        # print(' Deflecting',ballFrame,' to ',ballFrame,' #')
        print('===== Hitting ',ballFrame,' with Robot ', robotName ,' =====')

        self.setTarget(ballFrame)
        self.moveToInit()
        self.perception()
        self.alignDeflector(robotName)
        targetPose = self.RealWorld.getFrame(ballFrame).getPosition()
        # targetPose[1] += -0.55
        targetPose[2] += 0.55
        # targetPose[1] += 0.5

        self.moveToDest(robotName,targetPose)

    def movingBallPerception(self, ballFrame, observeTime):
        if(self.perceptionMode == 'cheat'):
            p1 = self.RealWorld.getFrame(ballFrame).getPosition()
            self.runSim(observeTime)
            p2 = self.RealWorld.getFrame(ballFrame).getPosition()
        elif(self.perceptionMode == 'komo'):
            p1, errPer = self.perceptionGetPosition(ballFrame)
            self.runSim(observeTime)
            p2, errPer = self.perceptionGetPosition(ballFrame)
        else:
            # TODO: Add OpenCV Ball Position Perception
            p1 = [0,0,0]
            p2 = [0,0,0]

        return p1,p2

    def hitBall(self, robotName, ballFrame, goalFrame):
        print('===== Hitting ',ballFrame,' =====')
        dt = 50
        steps = 6
        total_time = dt*steps
        observeTime = 50
        self.setTarget(ballFrame)
        # if self.debug:
        #     for i in range(1,steps+1):
        #         p1,p2 = self.movingBallPerception(ballFrame,observeTime)
        #         position = self.calculateFuturePosition(p1, p2, observeTime, dt*i)
        #         self.createBallFrame('ball_'+str(i),position,color = [0,0,0,0.5])


        p1,p2 = self.movingBallPerception(ballFrame,observeTime)
        position = self.calculateFuturePosition(p1,p2, observeTime, total_time)
        self.createBallFrame('future_ball',position,color = [0,1,0,0.3],contact = 0)
        # self.createBallFrame('future_ball',[1, 0, .3],[0,0,0,1])
        # self.moveGripper('B','init',[0.3,0,0.62],[ -0.383, 0,0,0.924])
        goalPos = self.RealWorld.getFrame(goalFrame).getPosition()
        goalPos[2] = 0.3
        self.createBallFrame('goal',goalPos,[0,0,0,1],contact = 0)
        startPosition = self.C.getFrame('future_ball').getPosition()
        goalPosition = self.C.getFrame('goal').getPosition()
        offset = 0.5
        initPosition, angle = self.calculateDeflectorInit('B',startPosition, goalPosition, offset)

        # Predict Future Trajectory
        if self.debug:
            steps = 9
            dt = 0.2
            for i in range(1,steps+1):
                position = [0,0,0]
                position[0] = startPosition[0] - i*dt*np.cos(angle)
                position[1] = startPosition[1] - i*dt*np.sin(angle)
                position[2] = 0.3
                self.createBallFrame('fball_'+str(i),position,color = [0,0,0,0.3],contact = 0)

        hitTimeDelay = -65 # 65 time units early
        # angle = angle - np.pi/2
        # angle= angle/2
        q = euler_to_quaternion(angle,0,0)
        print('Deflector Init Pos : ',initPosition, ' , quaternion: ',q)
        self.createBallFrame('init',initPosition,[0,0,0,1],[1,1,0,0.3],contact = 0)
        self.moveGripper('B','init',[0,0,0.63],q) # 30 time units
        self.runSim(total_time + hitTimeDelay)
        self.moveGripper('B','future_ball',[0,0,0.63],q) # 30 time units


    def moveGripper(self, robotName, targetFrame, targetOffset, targetOrientation):
        gripperCenterFrame = robotName + "_gripperCenter"
        gripperFingerFrame = robotName + "_finger1"
        print('===== Move Robot ',robotName,' with gripper frame ', gripperCenterFrame, ' to targetFrame ',targetFrame)

        T = 30
        self.C.setJointState(self.S.get_q())
        komo = self.C.komo_path(1.,T,T*self.tau,True)
        komo.addObjective([1.], ry.FS.positionDiff, [gripperCenterFrame, targetFrame], ry.OT.eq, [2e1], target=targetOffset)
        komo.addObjective([1.], ry.FS.quaternion, [gripperCenterFrame], ry.OT.eq, target=targetOrientation)
        komo.addObjective([1.], ry.FS.vectorZ, [gripperCenterFrame], ry.OT.eq, scale=[1e1], target=[0,0,1]);
        komo.addObjective([], ry.FS.accumulatedCollisions, type=ry.OT.ineq, scale=[1e1])
        komo.optimize()
        for t in range(T):
            self.C.setFrameState(komo.getConfiguration(t))
            q = self.C.getJointState()
            time.sleep(self.tau)
            self.S.step(q, self.tau, ry.ControlMode.position)
            self.V.setConfiguration(self.C)
            self.stepTime()

        print('===== Done Moving =====')


    def calculateFuturePosition(self,p1,p2, observeTime, futureTimeInterval):
        # t = observeTime

        [vx,vy] = [(p2[0] - p1[0])/observeTime, (p2[1] - p1[1])/observeTime ]

        v_abs = np.sqrt(vx*vx + vy*vy)
        distance = v_abs * (futureTimeInterval - observeTime)

        print('futureTimeInterval : ',futureTimeInterval)
        print('observeTime : ',observeTime)
        print('p1 : ',p1)
        print('p2 : ',p2)
        print('vx,vy : ',[vx,vy])
        print('v_abs : ',v_abs)
        print('distance : ',distance)
        angle = np.arctan2((p2[1] - p1[1]),(p2[0] - p1[0]))
        position = [0,0,0]
        position[0] = p2[0] + distance*np.cos(angle)
        position[1] = p2[1] + distance*np.sin(angle)
        position[2] = p2[2]

        print('future angle : ',angle )
        print('future pos : ',position)
        # input('===========calculatedFuturePosition===========')

        return position

    def calculateDeflectorInit(self,robotName,startPosition, goalPosition, offset):
        angle = np.arctan2((startPosition[1] - goalPosition[1]),(startPosition[0] - goalPosition[0]))
        # angle = 0
        initPosition = [0,0,0]
        initPosition[0] = startPosition[0] + offset*np.cos(angle)
        initPosition[1] = startPosition[1] + offset*np.sin(angle)
        initPosition[2] = 0.3
        print('Calc Deflector Init Pos : ',initPosition, ' , Ang: ',angle , ' rad = ', angle*180/np.pi, ' degrees')
        return initPosition, angle
