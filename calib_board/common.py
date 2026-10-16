import json
import glob
from pathlib import Path
import cv2
import numpy as np
import yaml

DEFAULT_SPEC = Path(__file__).resolve().parents[1] / 'spec/board_v1_1.json'

def read_data(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8'))

def save_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def save_data(path, value):
    """Write JSON or YAML, selected by the output filename."""
    if Path(path).suffix.lower() in ('.yaml', '.yml'):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(yaml.safe_dump(value, sort_keys=False), encoding='utf-8')
    else:
        save_json(path, value)

def image_paths(inputs):
    """Expand image files, directories and quoted globs in stable order."""
    suffixes = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'}
    paths = []
    for value in inputs:
        path = Path(value)
        if path.is_dir():
            matches = sorted(p for p in path.iterdir() if p.suffix.lower() in suffixes)
        elif path.is_file():
            matches = [path]
        else:
            matches = [Path(p) for p in sorted(glob.glob(str(path))) if Path(p).is_file()]
        if not matches:
            raise ValueError(f'No input images found: {value}')
        paths.extend(matches)
    resolved = [p.resolve() for p in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError('Duplicate input image paths; each image must appear once')
    return paths

def make_board(spec):
    p = spec['charuco']
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, p['dictionary']))
    board = cv2.aruco.CharucoBoard(tuple(p['squares_xy']), p['square_mm']/1000,
                                 p['marker_mm']/1000, dictionary)
    board.setLegacyPattern(False)
    return board, dictionary

def intrinsics(path):
    d = read_data(path)
    def array(key, ros):
        a = d.get(key, d.get(ros))
        return np.asarray(a['data'] if isinstance(a, dict) else a, dtype=float)
    K, D = array('K','camera_matrix').reshape(3,3), array('D','distortion_coefficients').ravel()
    if d.get('distortion_model','plumb_bob') not in ('plumb_bob','rational_polynomial'):
        raise ValueError('Only OpenCV pinhole / ROS plumb_bob and rational_polynomial are supported')
    return K, D, d

def matrix(rvec, tvec):
    T = np.eye(4)
    T[:3,:3] = cv2.Rodrigues(np.asarray(rvec, dtype=float))[0]
    T[:3,3] = np.asarray(tvec).ravel()
    return T

def check_transform(T):
    T = np.asarray(T, dtype=float)
    if T.shape != (4,4) or not np.all(np.isfinite(T)) or not np.allclose(T[3],[0,0,0,1]):
        raise ValueError('Expected a finite 4x4 homogeneous transform with translation in meters')
    if not np.allclose(T[:3,:3].T @ T[:3,:3], np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(T[:3,:3]),1):
        raise ValueError('Rotation must belong to SO(3)')
    return T

def quaternion(R):
    K = np.array([[R[0,0]-R[1,1]-R[2,2],R[0,1]+R[1,0],R[0,2]+R[2,0],R[2,1]-R[1,2]],
                  [R[0,1]+R[1,0],R[1,1]-R[0,0]-R[2,2],R[1,2]+R[2,1],R[0,2]-R[2,0]],
                  [R[0,2]+R[2,0],R[1,2]+R[2,1],R[2,2]-R[0,0]-R[1,1],R[1,0]-R[0,1]],
                  [R[2,1]-R[1,2],R[0,2]-R[2,0],R[1,0]-R[0,1],np.trace(R)]])
    q = np.linalg.eigh(K)[1][:,-1][[3,0,1,2]]
    return q if q[0]>=0 else -q
