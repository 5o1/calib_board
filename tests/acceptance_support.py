"""World-frame test helpers and workspace projection metrics."""
import cv2
import numpy as np

def tabletop_board(spec):
    # Synthetic world origin is the table center; board surface is 5 mm above Z=0.
    width,height=spec['charuco']['rect_mm'][2:]
    T=np.diag([1.,-1.,-1.,1.]);T[:3,3]=[-width/2000,height/2000,.005]
    return T

def world_grid():
    x,y=np.meshgrid(np.arange(-25,26)*.01,np.arange(-20,21)*.01)
    return np.concatenate([np.c_[x.ravel(),y.ravel(),np.full(x.size,z)] for z in [0,.05,.1]])

def project_world(points,wc,K,D):
    cw=np.linalg.inv(wc)
    if np.min((points@cw[:3,:3].T+cw[:3,3])[:,2])<=0:
        raise ValueError('Workspace points are not in front of the camera')
    return cv2.projectPoints(points,cv2.Rodrigues(cw[:3,:3])[0],cw[:3,3],K,D)[0].reshape(-1,2)

def projection_metrics(truth,estimate,K,D,width=1280,height=720):
    points=world_grid();uv=project_world(points,truth,K,D);predicted=project_world(points,estimate,K,D)
    errors=np.linalg.norm(uv-predicted,axis=1)
    visible=(uv[:,0]>=0)&(uv[:,0]<width)&(uv[:,1]>=0)&(uv[:,1]<height)
    layers=[]
    for z in [0,.05,.1]:
        e=errors[np.isclose(points[:,2],z)]
        layers.append({'height_above_table_m':z,'points':len(e),'max_px':float(e.max()),'mean_px':float(e.mean())})
    return {'points':len(points),'grid_size_xyz':[51,41,3],'spacing_mm':10,
            'workspace_center_world_m':[0,0,0],'workspace_size_xy_mm':[500,400],
            'heights_above_table_mm':[0,50,100],'true_in_frame_points':int(visible.sum()),
            'max_px':float(errors.max()),'mean_px':float(errors.mean()),'per_layer':layers,
            'scope':'All 6273 points participate, including projections outside the image; no clipping, outlier removal or alignment compensation.'}
