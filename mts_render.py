#!/usr/bin/env python2
import sys
import os
import logging
import multiprocessing

import mitsuba
from mitsuba.core import *
from mitsuba.render import Scene, RenderQueue, RenderJob

class Mitsuba(object):
    def __init__(self):
        # add path for the Python extension module
        if 'MITSUBA_DIR' not in os.environ:
            raise Exception('Set MITSUBA_DIR env variable, or source Mitsuba setpath.sh')
        MITSUBA_DIR = os.path.join(os.environ['MITSUBA_DIR'], 'dist')
        sys.path.append(MITSUBA_DIR + os.sep + 'python' + os.sep + '2.7')

        # Ensure python can find Mitsuba core libraries
        os.environ['PATH'] = MITSUBA_DIR + os.pathsep + os.environ['PATH']

        # set up logger
        FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
        logging.basicConfig(format=FORMAT)
        self.log = logging.getLogger('mts-render')
        self.log.setLevel(logging.INFO)

        # default setup
        self.setup = {'integrator': 'path', # choices: path, mlt, vpl, ao
                      'emitter': 'constant',
                      'sensor': 'perspective',
                      'film': 'ldrfilm',
                      'sampler': 'ldsampler',
                      'pixelFormat': 'rgba',
                      'exposure': 0.0, #Exposure value e, scales radiance by 2^e
                      'banner': False,

                      'camera_up': Vector(0,1,0),
                      'eye': Point(0,0,0),
                      'target': Point(0,0,0),
                      'sampleCount': 256,
                      'fov': 90.0,
                      'width': 640,
                      'height': 480,
                      }

        # Start up the scheduling system
        self.scheduler = Scheduler.getInstance()
        for i in range(0, multiprocessing.cpu_count()):
            self.scheduler.registerWorker(LocalWorker(i, 'wrk%i' % i))

        self.queue = RenderQueue()
        self.pmgr = PluginManager.getInstance()

    def set_fov(self, degree):
        self.setup['fov'] = degree

    def set_sampleCount(self, sampleCount):
        self.setup['sampleCount'] = sampleCount

    def set_camera_up(self, x,y,z):
        self.setup['camera_up'] = Vector(x,y,z)

    def set_eye(self, x,y,z):
        self.setup['eye'] = Point(x,y,z)

    def set_target(self, x,y,z):
        self.setup['target'] = Point(x,y,z)

    def set_width(self, width):
        self.setup['width'] = width

    def set_height(self, height):
        self.setup['height'] = height

    def load_mesh(self, mesh_filenames):
        self.mesh = []
        self.mesh_meta = []

        for mesh_filename in mesh_filenames:
            if mesh_filename.endswith('.ply'):
                self.mesh.append(self.pmgr.create({'type': 'ply',
                                                   'filename': mesh_filename,
                                                   'bsdf':  {'type':'twosided', 
                                                   'bsdf': {'type': 'diffuse', 
                                                             'reflectance': {'type':'vertexcolors'}}}}))
            elif mesh_filename.endswith('.obj'):
                self.mesh.append(pmgr.create({'type': 'obj',
                                              'filename': mesh_filename}))
            else:
                raise RuntimeError('Unsupported file type: ' + meshfile)

        #metadata
        for mesh in self.mesh:
            aabb = mesh.getAABB()
            bsphere = aabb.getBSphere()
            self.mesh_meta.append({'bsphere':{'center':bsphere.center, 'radius':bsphere.radius}, 'aabb':{'min': aabb.min, 'max':aabb.max}})

            self.log.info(aabb)
            self.log.info(bsphere)

    def render(self, filename):
        self.scheduler.start()
        # create globals
        integrator = self.pmgr.create({'type': self.setup['integrator']})
        emitter = self.pmgr.create({'type': self.setup['emitter']})
        sensor = self.pmgr.create({
            'type': self.setup['sensor'],
            'film': {
                'type': self.setup['film'],
                'width': self.setup['width'],
                'height': self.setup['height'],
                'pixelFormat': self.setup['pixelFormat'],
                'exposure': self.setup['exposure'],
                'banner': self.setup['banner']
            },
            'sampler': {
                'type': self.setup['sampler'],
                'sampleCount': self.setup['sampleCount']
            },
            'fov': self.setup['fov'],
        })

        scene = Scene()
        scene.addChild(integrator)
        scene.addChild(emitter)
        scene.addChild(sensor)
        for mesh in self.mesh:
            scene.addChild(mesh)
        scene.configure()
        scene.initialize()  # needed to force build of kd-tree

        transformCurr = Transform.lookAt(self.setup['eye'], self.setup['target'], self.setup['camera_up'])
        sensor.setWorldTransform(transformCurr)
        scene.setDestinationFile(filename)

        job = RenderJob('job', scene, self.queue)
        job.start()

        self.queue.waitLeft(0)
        self.queue.join()
        self.scheduler.stop()
