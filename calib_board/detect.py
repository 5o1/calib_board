"""Detect ChArUco and estimate T_camera_optical_board, with translation in meters."""
import argparse
from pathlib import Path
import cv2
import numpy as np
from .common import DEFAULT_SPEC, read_data, save_json, make_board, intrinsics, matrix

def detect(image, spec, K, D):
    if image is None: raise ValueError('Cannot read image')
    board,_=make_board(spec)
    cp=cv2.aruco.CharucoParameters(); cp.cameraMatrix=K; cp.distCoeffs=D
    # The OpenCV ChArUco tutorial recommends disabling marker corner refinement.
    # detectBoard performs ChArUco subpixel refinement internally.
    cp.minMarkers=2;cp.tryRefineMarkers=False
    dp=cv2.aruco.DetectorParameters();dp.cornerRefinementMethod=cv2.aruco.CORNER_REFINE_NONE
    detector=cv2.aruco.CharucoDetector(board,cp,dp)
    corners,ids,markers,marker_ids=detector.detectBoard(image)
    if ids is None or len(ids)<6: raise ValueError('At least six non-collinear ChArUco corners are required')
    obj,img=board.matchImagePoints(corners,ids)
    obj=obj.reshape(-1,3); img=img.reshape(-1,2)
    if np.linalg.matrix_rank(obj-obj.mean(axis=0))<2: raise ValueError('ChArUco corners are collinear')
    ok,rv,tv=cv2.solvePnP(obj,img,K,D,flags=cv2.SOLVEPNP_ITERATIVE)
    if not ok: raise ValueError('solvePnP failed')
    rv,tv=cv2.solvePnPRefineLM(obj,img,K,D,rv,tv)
    if np.min((cv2.Rodrigues(rv)[0]@obj.T+tv)[2])<=0: raise ValueError('Estimated board lies behind the camera')
    residual=np.linalg.norm(cv2.projectPoints(obj,rv,tv,K,D)[0].reshape(-1,2)-img,axis=1)
    T=matrix(rv,tv)
    result={'board_id':spec['board_id'],'spec_version':spec['version'],'translation_unit':'m',
            'image_size_wh':[image.shape[1],image.shape[0]],'K':K.tolist(),'D':D.tolist(),
            'corner_ids':ids.ravel().tolist(),'corners_px':img.tolist(),'object_points_m':obj.tolist(),
            'marker_ids':[] if marker_ids is None else marker_ids.ravel().tolist(),
            'detector_parameters':{'cornerRefinementMethod':'CORNER_REFINE_NONE','minMarkers':2,'tryRefineMarkers':False,'charuco_refinement':'OpenCV detectBoard internal default'},
            'rvec':rv.ravel().tolist(),'tvec_m':tv.ravel().tolist(),
            'T_camera_optical_board':T.tolist(),'reprojection_errors_px':residual.tolist(),
            'reprojection_median_px':float(np.median(residual)),'reprojection_p95_px':float(np.percentile(residual,95))}
    overlay=image.copy();cv2.aruco.drawDetectedCornersCharuco(overlay,corners,ids)
    cv2.drawFrameAxes(overlay,K,D,rv,tv,.08)
    return result,overlay

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('image');p.add_argument('--intrinsics',required=True)
    p.add_argument('--spec',default=str(DEFAULT_SPEC));p.add_argument('--output',default='build/detection.json')
    p.add_argument('--overlay',default='build/detection_overlay.png');a=p.parse_args()
    K,D,info=intrinsics(a.intrinsics);im=cv2.imread(a.image)
    if im is None: p.error('Cannot read image')
    if 'width' in info and (info['width'],info['height'])!=(im.shape[1],im.shape[0]):
        p.error('Image resolution does not match intrinsics; intrinsics are not automatically scaled')
    r,overlay=detect(im,read_data(a.spec),K,D);r['image']=str(Path(a.image).resolve())
    save_json(a.output,r);Path(a.overlay).parent.mkdir(parents=True,exist_ok=True)
    if not cv2.imwrite(a.overlay,overlay): raise OSError(a.overlay)
    print(f"Corners {len(r['corner_ids'])}; median {r['reprojection_median_px']:.4f} px; P95 {r['reprojection_p95_px']:.4f} px")
if __name__=='__main__': main()
