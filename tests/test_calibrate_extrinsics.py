"""Photo manifests, measured placements, and recovery of a known camera pose."""
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
import pytest

from calib_board.calibrate_extrinsics import calibrate
from calib_board.common import DEFAULT_SPEC, read_data, save_data, save_json
from calib_board.generate import generate
from calib_board.synthetic import render, workcell_pose
from acceptance_support import tabletop_board


@pytest.fixture(scope='module')
def dataset(tmp_path_factory):
    root = tmp_path_factory.mktemp('extrinsic_photos')
    spec = read_data(DEFAULT_SPEC)
    pdf = generate(DEFAULT_SPEC, root / 'board.pdf', preview=False)
    K = np.array([[906.561, 0, 647.896], [0, 905.986, 362.233], [0, 0, 1.]])
    save_json(root / 'camera.json', {'width': 1280, 'height': 720, 'K': K.tolist(), 'D': [0.] * 5})
    initial = tabletop_board(spec)
    camera_board, _ = workcell_pose(spec, .725, .9, 90)
    truth = initial @ np.linalg.inv(camera_board)
    observations = []
    for label, y in [('center', 0.), ('left', -.15), ('right', .15)]:
        placement = initial.copy()
        placement[1, 3] += y
        image = render(spec, np.linalg.inv(truth) @ placement, K, [1280, 720], pdf=pdf, noise_seed=17)
        cv2.imwrite(str(root / f'{label}.png'), image)
        save_json(root / f'{label}.json', {'T_world_board': placement.tolist()})
        observations.append({'image': f'{label}.png', 'placement': f'{label}.json'})
    manifest = {'intrinsics': 'camera.json', 'observations': observations}
    save_data(root / 'manifest.yaml', manifest)
    return root, manifest, spec, truth


def test_photo_cli(dataset, tmp_path):
    root, _, _, truth = dataset
    output = tmp_path / 'pose.json'
    result = subprocess.run([sys.executable, '-m', 'calib_board.calibrate_extrinsics',
                             str(root / 'manifest.yaml'), '--output', str(output),
                             '--diagnostics-dir', str(tmp_path / 'views')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    recovered = read_data(output)
    estimate = np.array(recovered['T_world_camera_optical'])
    assert np.linalg.norm(estimate[:3, 3] - truth[:3, 3]) < .002
    rotation = cv2.Rodrigues(estimate[:3, :3].T @ truth[:3, :3])[0]
    assert np.linalg.norm(rotation) * 180 / np.pi < .2
    assert recovered['reprojection_median_px'] < .5
    assert recovered['distinct_placements'] == 3
    assert recovered['calibration_mode'] == 'multi_position'
    assert len(list((tmp_path / 'views').glob('*_detection.json'))) == 3
    assert len(list((tmp_path / 'views').glob('*_overlay.png'))) == 3


def test_photo_quick_check(dataset):
    root, manifest, spec, _ = dataset
    save_json(root / 'single.json', {**manifest, 'observations': manifest['observations'][:1]})
    with pytest.raises(ValueError, match='three distinct'):
        calibrate(root / 'single.json', spec)
    result = calibrate(root / 'single.json', spec, quick_check=True)
    assert result['calibration_mode'] == 'quick_check'
    assert result['uncertainty']['translation_std_m'] is None


def test_repeated_photograph(dataset):
    root, manifest, spec, _ = dataset
    save_json(root / 'duplicate.json', {**manifest, 'observations': [manifest['observations'][0]] * 3})
    with pytest.raises(ValueError, match='different image'):
        calibrate(root / 'duplicate.json', spec)


def test_distinct_photos_repeated_placement(dataset):
    root, manifest, spec, _ = dataset
    observations = [{**item, 'placement': 'center.json'} for item in manifest['observations']]
    save_json(root / 'repeated.json', {**manifest, 'observations': observations})
    with pytest.raises(ValueError, match='three distinct'):
        calibrate(root / 'repeated.json', spec)


def test_wrong_camera_resolution(dataset):
    root, _, spec, _ = dataset
    camera = read_data(root / 'camera.json')
    save_json(root / 'wrong_camera.json', {**camera, 'width': 640})
    with pytest.raises(ValueError, match='resolution does not match'):
        calibrate(root / 'manifest.yaml', spec, intrinsics_path=root / 'wrong_camera.json')
