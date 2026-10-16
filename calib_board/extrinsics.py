"""Solve the camera optical pose in world coordinates from measured board placements."""
import argparse
import sys
import cv2
import numpy as np
from .common import DEFAULT_SPEC,read_data,save_data,check_transform,quaternion

def placement_transform(data,spec):
    if 'T_world_board' in data: return check_transform(data['T_world_board'])
    refs=data['hole_measurements']; holes={h['id']:h for h in spec['holes']}
    if len(refs)!=2 or refs[0]['id']==refs[1]['id']: raise ValueError('Measurements of two different holes are required')
    b=np.array([holes[h['id']]['center_mm'] for h in refs])/1000
    w=np.array([[h['from_back_edge_mm'],h['from_left_edge_mm']] for h in refs])/1000
    db=b[1]-b[0];dw=w[1]-w[0]
    mismatch=abs(np.linalg.norm(db)-np.linalg.norm(dw))*1000
    if mismatch>data.get('distance_tolerance_mm',2): raise ValueError(f'Hole distance mismatch: {mismatch:.3f} mm')
    # Face-up board: +Z points down; the complete 3D rotation remains right-handed.
    theta=np.arctan2(dw[1],dw[0])+np.arctan2(db[1],db[0])
    c,s=np.cos(theta),np.sin(theta);R=np.array([[c,s,0],[s,-c,0],[0,0,-1.]])
    offset=np.asarray(data.get('world_back_left_m',[0,0,0]),float)
    surface_z=data['board_surface_above_table_mm']/1000
    targets=np.c_[w,np.full(2,surface_z)]+offset
    T=np.eye(4);T[:3,:3]=R;T[:3,3]=np.mean(targets-(R@np.c_[b,np.zeros(2)].T).T,axis=0)
    return T

def mean_transform(transforms):
    Rsum=sum(T[:3,:3] for T in transforms);U,_,V=np.linalg.svd(Rsum)
    R=U@np.diag([1,1,np.linalg.det(U@V)])@V
    T=np.eye(4);T[:3,:3]=R;T[:3,3]=np.mean([v[:3,3] for v in transforms],axis=0)
    return T

def extrinsics(detections,placement,spec):
    if not detections: raise ValueError('No detections provided')
    wb=placement_transform(placement,spec)
    for d in detections:
        if (d['board_id'],d['spec_version'])!=(spec['board_id'],spec['version']): raise ValueError('Board ID or specification version mismatch')
    ts=[wb@np.linalg.inv(check_transform(d['T_camera_optical_board'])) for d in detections]
    T=mean_transform(ts)
    uncertainty={'method':'leave-one-image-out jackknife','n':len(ts),'translation_std_m':None,'rotation_std_rad':None,
                 'scope':'Image repeatability only; excludes intrinsics, printing and placement errors. All images must share a fixed camera and board.'}
    if len(ts)>1:
        leave=[mean_transform(ts[:i]+ts[i+1:]) for i in range(len(ts))]
        delta=np.array([np.r_[L[:3,3]-T[:3,3],cv2.Rodrigues(T[:3,:3].T@L[:3,:3])[0].ravel()] for L in leave])
        delta-=delta.mean(axis=0)
        std=np.sqrt((len(ts)-1)/len(ts)*np.sum(delta**2,axis=0))
        uncertainty['translation_std_m']=std[:3].tolist();uncertainty['rotation_std_rad']=std[3:].tolist()
    return {'T_world_camera_optical':T.tolist(),'pose_xyz_qw_qx_qy_qz':np.r_[T[:3,3],quaternion(T[:3,:3])].tolist(),
            'translation_unit':'m','camera_axes':'ROS optical: x right, y down, z forward','uncertainty':uncertainty}


def joint_extrinsics(detections,placements,spec):
    """Map all board corners to world coordinates, then jointly solve PnP and standard LM."""
    if not detections or len(detections)!=len(placements):
        raise ValueError('Each detection must have a corresponding measured board placement')
    first=detections[0];K=np.asarray(first['K'],float);D=np.asarray(first['D'],float)
    points=[];pixels=[]
    for detection,placement in zip(detections,placements):
        if (detection['board_id'],detection['spec_version'])!=(spec['board_id'],spec['version']):
            raise ValueError('Board ID or specification version mismatch')
        if (detection['image_size_wh']!=first['image_size_wh'] or
            not np.array_equal(np.asarray(detection['K']),K) or
            not np.array_equal(np.asarray(detection['D']),D)):
            raise ValueError('Joint calibration requires a fixed camera, identical resolution and K/D')
        wb=placement_transform(placement,spec)
        obj=np.asarray(detection['object_points_m'],float).reshape(-1,3)
        img=np.asarray(detection['corners_px'],float).reshape(-1,2)
        if len(obj)!=len(img):raise ValueError('Object point and image corner counts differ')
        points.append(obj@wb[:3,:3].T+wb[:3,3]);pixels.append(img)
    def solve(indices):
        world=np.concatenate([points[i] for i in indices]);image=np.concatenate([pixels[i] for i in indices])
        if len(world)<6 or np.linalg.matrix_rank(world-world.mean(axis=0))<2:
            raise ValueError('At least six non-collinear world points are required')
        ok,rv,tv=cv2.solvePnP(world,image,K,D,flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:raise ValueError('Joint solvePnP failed')
        rv,tv=cv2.solvePnPRefineLM(world,image,K,D,rv,tv)
        cw=np.eye(4);cw[:3,:3]=cv2.Rodrigues(rv)[0];cw[:3,3]=tv.ravel()
        if np.min((world@cw[:3,:3].T+cw[:3,3])[:,2])<=0:
            raise ValueError('Joint solution places points behind the camera')
        error=np.linalg.norm(cv2.projectPoints(world,rv,tv,K,D)[0].reshape(-1,2)-image,axis=1)
        return np.linalg.inv(cw),error
    n=len(detections);T,error=solve(range(n))
    uncertainty={'method':'leave-one-image-out jackknife, refit all remaining world/image correspondences',
                 'n':n,'translation_std_m':None,'rotation_std_rad':None,
                 'scope':'Leave-one-image-out repeatability only; excludes systematic placement, printing and intrinsic errors. Camera must remain fixed.'}
    if n>1:
        leave=[solve([j for j in range(n) if j!=i])[0] for i in range(n)]
        delta=np.array([np.r_[L[:3,3]-T[:3,3],cv2.Rodrigues(T[:3,:3].T@L[:3,:3])[0].ravel()] for L in leave])
        delta-=delta.mean(axis=0)
        std=np.sqrt((n-1)/n*np.sum(delta**2,axis=0))
        uncertainty['translation_std_m']=std[:3].tolist();uncertainty['rotation_std_rad']=std[3:].tolist()
    return {'T_world_camera_optical':T.tolist(),
            'pose_xyz_qw_qx_qy_qz':np.r_[T[:3,3],quaternion(T[:3,:3])].tolist(),
            'translation_unit':'m','camera_axes':'ROS optical: x right, y down, z forward',
            'method':'all world/image corners, solvePnP ITERATIVE + solvePnPRefineLM; equal corner weights; no rejection',
            'images':n,'corners_per_image':[len(p) for p in points],'total_corners':len(error),
            'reprojection_median_px':float(np.median(error)),
            'reprojection_p95_px':float(np.percentile(error,95)),
            'uncertainty':uncertainty}


def check_placements(placements, spec, quick_check=False):
    """Enforce the acquisition requirement at user-facing solver entry points."""
    transforms = [placement_transform(p, spec) for p in placements]
    unique = []
    for transform in transforms:
        if not any(np.allclose(transform, other, atol=1e-6, rtol=0) for other in unique):
            unique.append(transform)
    if not quick_check and len(unique) < 3:
        raise ValueError('Calibration requires at least three distinct board placements; '
                         'use --quick-check for diagnostic output only')
    return {'calibration_mode': 'quick_check' if quick_check else 'multi_position',
            'distinct_placements': len(unique),
            'physical_accuracy_verified': False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('detections',nargs='+',help='Detection JSON/YAML files')
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--placement',help='Legacy fixed-board pose averaging; requires --quick-check')
    group.add_argument('--placements',nargs='+',help='Placement JSON/YAML files matching detection files in count and order')
    p.add_argument('--quick-check',action='store_true',help='Allow fewer than three placements; diagnostic output only')
    p.add_argument('--spec',default=str(DEFAULT_SPEC));p.add_argument('--output',default='build/extrinsics.json');a=p.parse_args()
    detections=[read_data(d) for d in a.detections];spec=read_data(a.spec)
    try:
        if a.placements:
            if len(a.placements)!=len(detections):p.error('--placements must match detection files in count and order')
            placements=[read_data(d) for d in a.placements]
        else:
            if not a.quick_check:p.error('--placement is a legacy diagnostic interface; use --placements or --quick-check')
            placements=[read_data(a.placement)]
        status=check_placements(placements,spec,a.quick_check)
        if a.quick_check:
            print('Warning: quick-check output is diagnostic only; calibration requires at least three distinct board placements.',file=sys.stderr)
        if a.placements:
            result=joint_extrinsics(detections,placements,spec)
        else:
            result=extrinsics(detections,placements[0],spec)
        result.update(status)
        save_data(a.output,result)
    except (ValueError,OSError,cv2.error) as exc:
        p.error(str(exc))
    print(f"Saved {a.output} ({result['calibration_mode']})")
if __name__=='__main__':main()
