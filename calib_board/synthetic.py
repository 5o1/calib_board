"""Synthetic validation: project the rendered PDF rather than detector-generated targets."""
from pathlib import Path
import cv2
import numpy as np
import pypdfium2 as pdfium
from .common import matrix

def pose(spec,distance_m,tilt_deg,azimuth_deg=0,roll_deg=0):
    # Center the board on the optical axis; tilt is the normal-to-view angle.
    a=np.deg2rad(azimuth_deg);axis=np.array([np.cos(a),np.sin(a),0.])
    R=cv2.Rodrigues(axis*np.deg2rad(tilt_deg))[0]
    R=cv2.Rodrigues(np.array([0.,0.,np.deg2rad(roll_deg)]))[0]@R
    w,h=spec['charuco']['rect_mm'][2:]
    center=np.array([w/2000,h/2000,0])
    return matrix(cv2.Rodrigues(R)[0],np.array([0.,0.,distance_m])-R@center)

def render(spec,T,K,wh,pdf='build/board_v1_1_A3.pdf',occlude=False,noise_seed=0):
    scale=300/72; doc=pdfium.PdfDocument(str(pdf));page=doc[0]
    source=np.asarray(page.render(scale=scale).to_pil().convert('RGB'))[:,:,::-1].copy()
    page.close();doc.close()
    ppm=300/25.4
    ox,oy=spec['paper']['board_origin_from_top_left_mm']
    # Source pixel (0,0) is centered at paper coordinates (0.5/ppm, 0.5/ppm) mm.
    xy=np.array([[0,0],[source.shape[1]-1,0],[source.shape[1]-1,source.shape[0]-1],[0,source.shape[0]-1]],float)
    pts=np.c_[(xy+.5)/ppm-[ox,oy],np.zeros(4)]/1000
    rv=cv2.Rodrigues(T[:3,:3])[0];tv=T[:3,3]
    dst=cv2.projectPoints(pts,rv,tv,K,np.zeros(5))[0].reshape(4,2)
    super_factor=3
    H=cv2.getPerspectiveTransform(xy.astype(np.float32),(dst*super_factor+(super_factor-1)/2).astype(np.float32))
    img=cv2.warpPerspective(source,H,(wh[0]*super_factor,wh[1]*super_factor),flags=cv2.INTER_LINEAR,borderValue=(155,155,155))
    img=cv2.resize(img,tuple(wh),interpolation=cv2.INTER_AREA)
    if occlude:
        # Occlude the upper-left 28% x 48% of the pattern, leaving gray patches visible.
        w,h=spec['charuco']['rect_mm'][2:]
        q=np.array([[0,0,0],[.28*w,0,0],[.28*w,.48*h,0],[0,.48*h,0]],float)/1000
        p=cv2.projectPoints(q,rv,tv,K,np.zeros(5))[0].reshape(-1,2)
        cv2.fillConvexPoly(img,np.rint(p).astype(np.int32),(145,145,145))
    img=cv2.GaussianBlur(img,(3,3),.45)
    noise=np.random.default_rng(noise_seed).normal(0,.6,img.shape)
    return np.clip(img.astype(float)+noise,0,255).round().astype(np.uint8)

def minimum_cell_px(spec,T,K):
    n=6 if spec['charuco']['dictionary']=='DICT_4X4_50' else 7
    rv=cv2.Rodrigues(T[:3,:3])[0];tv=T[:3,3]
    lengths=[]
    for m in spec['charuco']['markers']:
        x,y,w,h=m['rect_mm'];xx,yy=np.meshgrid(np.linspace(x,x+w,n+1),np.linspace(y,y+h,n+1))
        pts=np.c_[xx.ravel(),yy.ravel(),np.zeros(xx.size)]/1000
        uv=cv2.projectPoints(pts,rv,tv,K,np.zeros(5))[0].reshape(n+1,n+1,2)
        # Minimum singular value of each projected cell basis includes oblique compression.
        u=uv[:-1,1:]-uv[:-1,:-1];v=uv[1:,:-1]-uv[:-1,:-1]
        lengths.extend(np.linalg.svd(np.stack([u,v],axis=-1),compute_uv=False)[...,-1].ravel())
    return float(np.min(lengths))


def workcell_pose(spec,height_m,distance_m,azimuth_deg=0,roll_deg=0,board_shift_xy_m=(0,0)):
    """Translate the board with a fixed camera; recompute geometry from the final transform."""
    if not 0 < height_m <= distance_m: raise ValueError('Height must be in (0, distance]')
    tilt=float(np.rad2deg(np.arccos(height_m/distance_m)))
    T=pose(spec,distance_m,tilt,azimuth_deg,roll_deg)
    T[:3,3]+=T[:3,:3]@np.r_[board_shift_xy_m,0.]
    center=np.r_[np.array(spec['charuco']['rect_mm'][2:])/2000,0.,1.]
    camera_center=T@center
    height=abs(float(T[:3,2]@camera_center[:3]));distance=float(np.linalg.norm(camera_center[:3]))
    return T,{'height_m':height,'distance_m':distance,'normal_angle_deg':float(np.rad2deg(np.arccos(height/distance))),
              'plane_view_angle_deg':float(np.rad2deg(np.arcsin(height/distance))),'board_shift_xy_m':list(board_shift_xy_m)}
