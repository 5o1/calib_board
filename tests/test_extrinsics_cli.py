"""CLI acquisition policy, diagnostic behavior, and joint pose recovery."""
import subprocess
import sys

import cv2
import numpy as np
import pytest

from calib_board.common import DEFAULT_SPEC, read_data, save_json, intrinsics, make_board, matrix


@pytest.fixture
def observations(tmp_path):
    spec = read_data(DEFAULT_SPEC)
    board, _ = make_board(spec)
    K, D, _ = intrinsics('examples/camera_1280.json')
    obj = board.getChessboardCorners().astype(float)
    camera_board = matrix(np.array([.5, .1, 0.]), np.array([-.15, -.1, .9]))
    detections, placements = [], []
    for i in range(3):
        placement = np.eye(4)
        placement[0, 3] = i * .1
        transform = camera_board @ placement
        pixels = cv2.projectPoints(obj, cv2.Rodrigues(transform[:3, :3])[0], transform[:3, 3], K, D)[0].reshape(-1, 2)
        detection = {'board_id': spec['board_id'], 'spec_version': spec['version'],
                     'T_camera_optical_board': transform.tolist(), 'image_size_wh': [1280, 720],
                     'K': K.tolist(), 'D': D.tolist(), 'object_points_m': obj.tolist(), 'corners_px': pixels.tolist()}
        detection_file = tmp_path / f'detection_{i}.json'
        placement_file = tmp_path / f'placement_{i}.json'
        save_json(detection_file, detection)
        save_json(placement_file, {'T_world_board': placement.tolist()})
        detections.append(str(detection_file))
        placements.append(str(placement_file))
    return detections, placements, np.linalg.inv(camera_board)


def run_cli(detections, placements, output, *extra, option='--placements'):
    return subprocess.run([sys.executable, '-m', 'calib_board.extrinsics', *detections, option,
                           *placements, '--output', str(output), *extra], capture_output=True, text=True)


@pytest.mark.parametrize('option', ['--placement', '--placements'])
def test_single_image_quick_check(tmp_path, observations, option):
    detections, placements, truth = observations
    output = tmp_path / 'quick.json'
    result = run_cli(detections[:1], placements[:1], output, '--quick-check', option=option)
    assert result.returncode == 0, result.stderr
    assert 'recommended' in result.stderr
    record = read_data(output)
    assert record['calibration_mode'] == 'quick_check'
    assert record['physical_accuracy_verified'] is False
    assert np.allclose(record['T_world_camera_optical'], truth, atol=1e-6)


@pytest.mark.parametrize('indices', [[0], [0, 1], [0, 0, 0]])
def test_accept_few_distinct_placements(tmp_path, observations, indices):
    detections, placements, truth = observations
    output = tmp_path / 'few.json'
    result = run_cli([detections[i] for i in indices], [placements[i] for i in indices], output)
    assert result.returncode == 0, result.stderr
    assert 'recommended' in result.stderr
    record = read_data(output)
    assert record['distinct_placements'] == len(set(indices))
    assert record['below_recommended_placements'] is True
    assert np.allclose(record['T_world_camera_optical'], truth, atol=1e-6)


def test_joint_cli(tmp_path, observations):
    detections, placements, truth = observations
    output = tmp_path / 'joint.yaml'
    result = run_cli(detections, placements, output)
    assert result.returncode == 0, result.stderr
    record = read_data(output)
    assert record['calibration_mode'] == 'multi_position'
    assert record['distinct_placements'] == 3
    assert np.allclose(record['T_world_camera_optical'], truth, atol=1e-6)
