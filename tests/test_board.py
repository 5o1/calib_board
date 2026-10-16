import json
from pathlib import Path
import cv2
import numpy as np
import pytest
from pypdf import PdfReader
from pypdf.generic import ContentStream
from calib_board.common import read_data,DEFAULT_SPEC,intrinsics,save_json,quaternion
from calib_board.generate import generate,rectangles,PT
from calib_board.detect import detect
from calib_board.extrinsics import extrinsics,placement_transform,joint_extrinsics
from calib_board.gray_ramp import analyze
from calib_board.synthetic import pose,render,minimum_cell_px,workcell_pose
from acceptance_support import tabletop_board,projection_metrics,world_grid,project_world

SPEC=read_data(DEFAULT_SPEC)

@pytest.mark.parametrize('spec_path',['docs/archive/legacy/superseded/spec/board_v1.json','spec/board_v1_1.json'])
def test_pdf(tmp_path,spec_path):
    SPEC=read_data(spec_path)
    a=generate(spec_path,tmp_path/'a.pdf',False);b=generate(spec_path,tmp_path/'b.pdf',False)
    assert a.read_bytes()==b.read_bytes()
    reader=PdfReader(a);p=reader.pages[0]
    assert np.allclose([float(p.mediabox.width),float(p.mediabox.height)],np.array([420,297])*PT,atol=1e-4)
    resources=p['/Resources']
    for ob in resources.get('/XObject',{}).values(): assert ob.get_object().get('/Subtype')!='/Image'
    ops=ContentStream(p.get_contents(),reader).operations
    assert all(op!=b'INLINE IMAGE' for _,op in ops)
    rects=[list(map(float,args)) for args,op in ops if op==b're']
    expected=[r for _,r,_ in rectangles(SPEC)]+[f['rect_mm'] for f in SPEC['frames']]
    assert len(rects)==len(expected)
    ox,oy=SPEC['paper']['board_origin_from_top_left_mm']
    for actual,(x,y,w,h) in zip(rects,expected):
        assert np.max(np.abs(np.array(actual)/PT-[x+ox,297-(y+oy+h),w,h]))<=.01
    # Check circle centers and radii directly from cubic Bezier path endpoints.
    circles=[];current=[]
    for args,op in ops:
        if op==b'm': current=[np.array(list(map(float,args)))]
        elif op==b'c': current.extend(np.array(list(map(float,args))).reshape(3,2)[[2]])
        elif op==b'S' and len(current)==5:
            circles.append(np.array(current))
    assert len(circles)==4
    for pts,h in zip(circles,SPEC['holes']):
        center=(pts.min(axis=0)+pts.max(axis=0))/2/PT
        assert np.max(np.abs(center-[ox+h['center_mm'][0],297-oy-h['center_mm'][1]]))<.01
        assert abs((pts[:,0].max()-pts[:,0].min())/PT-3.2)<.01
    # Every crosshair and ruler tick must exist in the PDF content stream.
    lines=[];start=None
    for args,op in ops:
        if op==b'm': start=np.array(list(map(float,args)))
        elif op==b'l' and start is not None: lines.append(np.r_[start,np.array(list(map(float,args)))])
    segments=[segment for h in SPEC['holes'] for segment in h['cross_segments_mm']]
    segments += [[r['start_mm'],r['end_mm']] for r in SPEC['rulers']]
    segments += [[t['start_mm'],t['end_mm']] for r in SPEC['rulers'] for t in r['ticks']]
    for a,b in segments:
        want=np.array([ox+a[0],297-oy-a[1],ox+b[0],297-oy-b[1]])*PT
        assert min(np.max(np.abs(line-want))/PT for line in lines)<.01

def rect_distance(a,b):
    ax,ay,aw,ah=a;bx,by,bw,bh=b
    return np.hypot(max(ax-bx-bw,bx-ax-aw,0),max(ay-by-bh,by-ay-ah,0))

@pytest.mark.parametrize('spec_path',['docs/archive/legacy/superseded/spec/board_v1.json','spec/board_v1_1.json'])
def test_hole_clearance(spec_path):
    SPEC=read_data(spec_path)
    targets=[SPEC['charuco']['rect_mm'],SPEC['colorchecker_slot']['rect_mm']]+[g['rect_mm'] for g in SPEC['gray_ramp']]
    for r in SPEC['rulers']:
        points=np.array([r['start_mm'],r['end_mm']]+[p for t in r['ticks'] for p in [t['start_mm'],t['end_mm']]])
        lo=points.min(axis=0)-.1;hi=points.max(axis=0)+.1
        targets.append([*lo,*(hi-lo)])
    for h in SPEC['holes']:
        x,y=h['center_mm'];paper=np.array([x,y])+SPEC['paper']['board_origin_from_top_left_mm']
        assert min(*paper,420-paper[0],297-paper[1])>=10
        # Crosshair bounds include the circle and stroke width.
        bounds=[x-5.1,y-5.1,10.2,10.2]
        for r in targets:
            assert rect_distance(bounds,r)>=5
            assert rect_distance(h['label_bounds_mm'],r)>=5
    centers=np.array([h['center_mm'] for h in SPEC['holes']])
    assert np.array_equal(centers[1]-centers[0],[400,0])
    assert np.array_equal(centers[2]-centers[1],[0,277])
    assert np.array_equal(centers[3]-centers[0],[0,277])

def rotation_error(A,B): return float(np.linalg.norm(cv2.Rodrigues(A.T@B)[0])*180/np.pi)

# Fix cases, noise and thresholds before detection; do not select views by error.
WORKCELL_CASES=[
    ('center',.725,.9,0,0,(0,0),False),
    ('left',.725,.9,0,0,(-.04,0),False),
    ('right',.725,.9,0,0,(.04,0),True),
    ('back',.725,.9,0,0,(0,-.04),False),
    ('front',.725,.9,0,0,(0,.04),True),
    ('near_low',.65,.8,25,-3,(0,0),False),
    ('far_high',.8,1.,90,3,(0,0),True),
    ('far_low',.65,1.,45,-4,(0,0),False),
]

@pytest.mark.parametrize('camera',['1280','640'])
@pytest.mark.parametrize('name,height,distance,azimuth,roll,shift,occlusion',WORKCELL_CASES)
def test_closed_loop(camera,name,height,distance,azimuth,roll,shift,occlusion):
    K,D,info=intrinsics(f'examples/camera_{camera}.json');wh=[info['width'],info['height']]
    T,geometry=workcell_pose(SPEC,height,distance,azimuth,roll,shift)
    assert .65-1e-9 <= geometry['height_m'] <= .8+1e-9
    assert .8-1e-9 <= geometry['distance_m'] <= 1.+1e-9
    assert 30 <= geometry['normal_angle_deg'] <= 60
    assert 30 <= geometry['plane_view_angle_deg'] <= 60
    name=f'{camera}_{name}';directory=Path('build/review5_single');directory.mkdir(exist_ok=True)
    base=directory/name
    image=render(SPEC,T,K,wh,occlude=occlusion,noise_seed=17)
    cv2.imwrite(str(base)+'.png',image)
    metrics={'camera':camera,'case':name,'geometry':geometry,'occlusion':occlusion,
             'min_cell_px':minimum_cell_px(SPEC,T,K),'detected':False,'meets_pose_gate':False}
    try:
        detection,overlay=detect(image,SPEC,K,D)
    except ValueError as exc:
        metrics['error']=str(exc);save_json(str(base)+'_metrics.json',metrics)
        if camera=='1280':raise
        return
    save_json(str(base)+'_detection.json',detection)
    cv2.imwrite(str(base)+'_overlay.png',overlay)
    recovered=np.array(detection['T_camera_optical_board'])
    wb=tabletop_board(SPEC)
    wb[:3,3]+=wb[:3,:3]@np.r_[shift,0.]
    ext=extrinsics([detection],{'T_world_board':wb.tolist()},SPEC)
    truth=wb@np.linalg.inv(T);estimate=np.array(ext['T_world_camera_optical'])
    dt=float(np.linalg.norm(estimate[:3,3]-truth[:3,3])*1000);dr=rotation_error(estimate[:3,:3],truth[:3,:3])
    dbt=float(np.linalg.norm(recovered[:3,3]-T[:3,3])*1000);dbr=rotation_error(recovered[:3,:3],T[:3,:3])
    gray=analyze(image,detection,SPEC)
    metrics.update(detected=True,corners=len(detection['corner_ids']),board_translation_error_mm=dbt,
                   board_rotation_error_deg=dbr,camera_translation_error_mm=dt,camera_rotation_error_deg=dr,
                   reprojection_median_px=detection['reprojection_median_px'],reprojection_p95_px=detection['reprojection_p95_px'],
                   gray_monotonic=gray['monotonic_increasing'],gray_visible=sum(p['valid'] for p in gray['patches']))
    metrics['meets_pose_gate']=bool(dbt<=2 and dt<=2 and dbr<=.2 and dr<=.2 and detection['reprojection_median_px']<=.5)
    metrics['workspace_projection']=projection_metrics(truth,estimate,K,D,*wh)
    save_json(str(base)+'_metrics.json',metrics);save_json(str(base)+'_gray.json',gray)
    if camera=='1280':
        assert gray['monotonic_increasing']
        # Single-view workspace errors are recorded without a release threshold.
        assert detection['reprojection_median_px']<=.5

def test_white_margin():
    p=SPEC['charuco'];margin=(p['square_mm']-p['marker_mm'])/2;module=p['marker_mm']/6
    assert .75<=p['marker_mm']/p['square_mm']<=.8
    assert margin>=5 and margin>.7*module
    assert len(p['corners'])==20

def test_cells():
    # Require 3.5 px at the reference condition; document the limits elsewhere.
    K,_,_=intrinsics('examples/camera_1280.json')
    mins=[minimum_cell_px(SPEC,pose(SPEC,.9,45,a),K) for a in range(0,360,5)]
    save_json('build/cell_design_v1_1.json',{'min_px_1280_0.9m_45deg_all_azimuth':min(mins)})
    assert min(mins)>=3.5

def test_hole_placement():
    data=read_data('examples/placement_holes.json');T=placement_transform(data,SPEC)
    holes={h['id']:h for h in SPEC['holes']}
    for m in data['hole_measurements']:
        p=T@np.r_[np.array(holes[m['id']]['center_mm'])/1000,0,1]
        assert np.allclose(p[:3],[m['from_back_edge_mm']/1000,m['from_left_edge_mm']/1000,.005])
    # Test rotated placement using diagonal holes and a world origin offset.
    theta=.37;c,s=np.cos(theta),np.sin(theta)
    truth=np.eye(4);truth[:3,:3]=[[c,s,0],[s,-c,0],[0,0,-1]];truth[:3,3]=[.25,.4,.012]
    refs=[]
    for key in ['H2','H4']:
        p=truth@np.r_[np.array(holes[key]['center_mm'])/1000,0,1]
        refs.append({'id':key,'from_back_edge_mm':p[0]*1000,'from_left_edge_mm':p[1]*1000})
    assert np.allclose(placement_transform({'hole_measurements':refs,'board_surface_above_table_mm':12},SPEC),truth)
    bad={**data,'hole_measurements':[dict(x) for x in data['hole_measurements']]};bad['hole_measurements'][1]['from_back_edge_mm']+=20
    with pytest.raises(ValueError):placement_transform(bad,SPEC)

def test_multi_image_and_quaternion():
    wb=placement_transform(read_data('examples/placement_holes.json'),SPEC)
    T=pose(SPEC,.9,45);ds=[]
    for dx in [-.001,0,.001]:
        t=T.copy();t[0,3]+=dx
        ds.append({'board_id':SPEC['board_id'],'spec_version':SPEC['version'],'T_camera_optical_board':t.tolist()})
    r=extrinsics(ds,{'T_world_board':wb.tolist()},SPEC)
    assert np.allclose(r['T_world_camera_optical'],wb@np.linalg.inv(T))
    assert np.linalg.norm(r['uncertainty']['translation_std_m'])>0
    assert extrinsics(ds[:1],{'T_world_board':wb.tolist()},SPEC)['uncertainty']['translation_std_m'] is None
    for axis in np.eye(3):
        R=cv2.Rodrigues(axis*np.pi)[0];q=quaternion(R);w,x,y,z=q
        reconstructed=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                                [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                                [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        assert np.allclose(reconstructed,R)


@pytest.mark.parametrize('group,height,distance,azimuth,roll',[
    ('A',.725,.9,90,0),('B',.7,.9,30,-3),('C',.75,.9,90,3)])
def test_three_position_joint(group,height,distance,azimuth,roll):
    K,D,info=intrinsics('examples/camera_1280.json');wh=[info['width'],info['height']]
    base=Path('build/review5_joint')/group;base.mkdir(parents=True,exist_ok=True)
    initial=tabletop_board(SPEC);cb,_=workcell_pose(SPEC,height,distance,azimuth,roll)
    truth=initial@np.linalg.inv(cb)
    detections=[];placements=[];views=[]
    for label,world_y in [('center',0.),('left',-.15),('right',.15)]:
        wb=initial.copy();wb[1,3]+=world_y
        cam_board=np.linalg.inv(truth)@wb
        image=render(SPEC,cam_board,K,wh,occlude=False,noise_seed=17)
        detection,overlay=detect(image,SPEC,K,D)
        placement={'T_world_board':wb.tolist()}
        cv2.imwrite(str(base/f'{label}.png'),image);cv2.imwrite(str(base/f'{label}_overlay.png'),overlay)
        save_json(base/f'{label}_detection.json',detection);save_json(base/f'{label}_placement.json',placement)
        detections.append(detection);placements.append(placement)
        center_camera=cam_board@np.r_[np.array(SPEC['charuco']['rect_mm'][2:])/2000,0.,1.]
        view_distance=float(np.linalg.norm(center_camera[:3]))
        plane_angle=float(np.rad2deg(np.arcsin(height/view_distance)))
        views.append({'label':label,'board_center_world_m':[0,world_y,.005],
                      'distance_to_board_center_m':view_distance,'plane_view_angle_deg':plane_angle,
                      'normal_angle_deg':90-plane_angle,'corners':len(detection['corner_ids'])})
        assert .8<=view_distance<=1.0 and 30<=plane_angle<=60

    result=joint_extrinsics(detections,placements,SPEC);estimate=np.array(result['T_world_camera_optical'])
    dt=float(np.linalg.norm(estimate[:3,3]-truth[:3,3])*1000);dr=rotation_error(estimate[:3,:3],truth[:3,:3])
    metrics={'group':group,'camera_height_above_board_m':height,'central_distance_m':distance,
             'views':views,'camera_translation_error_mm':dt,'camera_rotation_error_deg':dr,
             'workspace_projection':projection_metrics(truth,estimate,K,D),
             'reprojection_median_px':result['reprojection_median_px'],'total_corners':result['total_corners'],
             'true_T_world_camera_optical':truth.tolist()}
    save_json(base/'extrinsics.json',result);save_json(base/'metrics.json',metrics)
    assert len(placements)>=3
    assert result['total_corners']==sum(len(d['corner_ids']) for d in detections)
    assert dt<=2 and dr<=.2
    assert result['reprojection_median_px']<=.5
    # All three placements use full transforms; verify the world camera estimate.
    assert result['uncertainty']['translation_std_m'] is not None


def test_projection_grid_definition():
    grid=world_grid()
    assert grid.shape==(6273,3)
    assert np.allclose(grid.min(axis=0),[-.25,-.2,0])
    assert np.allclose(grid.max(axis=0),[.25,.2,.1])
    K,D,_=intrinsics('examples/camera_1280.json')
    wb=tabletop_board(SPEC);cb,_=workcell_pose(SPEC,.725,.9);wc=wb@np.linalg.inv(cb)
    metrics=projection_metrics(wc,wc,K,D)
    assert metrics['max_px']==0 and metrics['mean_px']==0
    # Verify the independent fx*dx/Z prediction for a 1 mm camera-X translation.
    points=np.array([[0.,0.,1.],[.2,.1,1.]])
    identity=np.eye(4);offset=identity.copy();offset[0,3]=.001
    a=project_world(points,identity,K,D);b=project_world(points,offset,K,D)
    assert np.allclose(a-b,[[K[0,0]*.001,0]]*2)


def test_joint_rejects_mismatched_observations():
    wb=tabletop_board(SPEC);T,_=workcell_pose(SPEC,.725,.9);K,D,_=intrinsics('examples/camera_1280.json')
    board,_=__import__('calib_board.common',fromlist=['make_board']).make_board(SPEC)
    obj=board.getChessboardCorners().astype(float)
    pixels=cv2.projectPoints(obj,cv2.Rodrigues(T[:3,:3])[0],T[:3,3],K,D)[0].reshape(-1,2)
    detection={'board_id':SPEC['board_id'],'spec_version':SPEC['version'],'K':K.tolist(),'D':D.tolist(),
               'image_size_wh':[1280,720],'object_points_m':obj.tolist(),'corners_px':pixels.tolist()}
    placement={'T_world_board':wb.tolist()}
    result=joint_extrinsics([detection],[placement],SPEC)
    assert np.allclose(result['T_world_camera_optical'],wb@np.linalg.inv(T),atol=1e-6)
    with pytest.raises(ValueError):joint_extrinsics([detection],[],SPEC)
    bad={**detection,'K':(K*1.01).tolist()}
    with pytest.raises(ValueError):joint_extrinsics([detection,bad],[placement,placement],SPEC)
