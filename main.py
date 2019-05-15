import math
import argparse
import numpy as np
import os
from mts_render import Mitsuba

parser = argparse.ArgumentParser(description='Render PLY file using Mitsuba')
parser.add_argument('--filename', type=str, help='Output file')
parser.add_argument('--samples', type=int, default=64, help='Number of samples per pixel')
parser.add_argument('--width', type=int, default=320, help='Image width')
parser.add_argument('--height', type=int, default=240, help='Image height')
parser.add_argument('--meshfolder', type=str, help='mesh folder')
parser.add_argument('--roundtable', action='store_true', default=False, help='render turntable')
args = parser.parse_args()

meshes = []
for mesh in os.listdir(args.meshfolder):
    meshes.append(os.path.join(args.meshfolder, mesh))

mts_render = Mitsuba()
mts_render.load_mesh(meshes)
mts_render.set_camera_up(0,0,1)
mts_render.set_width(args.width)
mts_render.set_height(args.height)
mts_render.set_sampleCount(args.samples)

bsphere_radius = mts_render.mesh_meta[0]['bsphere']['radius']
center = mts_render.mesh_meta[0]['bsphere']['center']

if args.roundtable:  # render turntable sequence
    degree_per_frame = 5
    mts_render.set_target(center[0], center[1], center[2])

    for i in range(0, 360 / degree_per_frame):
        x = center[0] + bsphere_radius*math.cos(i*degree_per_frame*math.pi/180.0)
        y = center[1] + bsphere_radius*math.sin(i*degree_per_frame*math.pi/180.0)
        mts_render.set_eye(x,y, bsphere_radius)
        mts_render.render('%03i.png' % i)

    # convert to video
    os.system('ffmpeg -y -pix_fmt yuv420p -r 30 -i %03d.png -vcodec libx264 scene.mp4')
    os.system('rm *.png')
else:
    mts_render.set_target(center[0], center[1], center[2])
    mts_render.set_eye(center[0]/2, center[1]/2, bsphere_radius/2)
    mts_render.render('scene.png')
