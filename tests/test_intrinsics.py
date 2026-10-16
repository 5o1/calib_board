"""Intrinsic recovery from PDF images distorted by a known pinhole model."""
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
import pytest

from calib_board.common import DEFAULT_SPEC, image_paths, read_data, intrinsics
from calib_board.intrinsics import calibrate
from calib_board.synthetic import pose, render


@pytest.fixture(scope='module')
def captures(tmp_path_factory):
    root = tmp_path_factory.mktemp('intrinsic_photos')
    spec = read_data(DEFAULT_SPEC)
    K = np.array([[906.561, 0, 647.896], [0, 905.986, 362.233], [0, 0, 1.]])
    D = np.array([-.16, .045, .001, -.001, 0.])
    # For each distorted output pixel, find its corresponding ideal source pixel.
    x, y = np.meshgrid(np.arange(1280), np.arange(720))
    grid = np.stack([x, y], axis=-1).astype(np.float32).reshape(-1, 1, 2)
    source = cv2.undistortPoints(grid, K, D, P=K).reshape(720, 1280, 2)
    paths = []
    for i in range(18):
        transform = pose(spec, .60 + .04 * (i % 5), 15 + 12 * (i % 3), i * 37, (i % 5 - 2) * 5)
        transform[:2, 3] += [(i % 3 - 1) * .21, (i // 3 % 3 - 1) * .10]
        ideal = render(spec, transform, K, [1280, 720], noise_seed=100 + i)
        distorted = cv2.remap(ideal, source[:, :, 0], source[:, :, 1], cv2.INTER_LINEAR, borderValue=(155, 155, 155))
        path = root / f'view_{i:02d}.png'
        assert cv2.imwrite(str(path), distorted)
        paths.append(path)
    return root, paths, spec, K, D


def test_intrinsic_cli_recovery(captures, tmp_path):
    root, paths, spec, K, D = captures
    output = tmp_path / 'intrinsics.yaml'
    result = subprocess.run([sys.executable, '-m', 'calib_board.intrinsics', str(root),
                             '--output', str(output), '--overlay-dir', str(tmp_path / 'overlays')],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    recovered, distortion, info = intrinsics(output)
    assert info['used_images'] == 18
    assert info['skipped_images'] == []
    assert info['rms_px'] < .5
    assert np.allclose(np.diag(recovered)[:2], np.diag(K)[:2], rtol=.01)
    assert np.max(np.abs(recovered[:2, 2] - K[:2, 2])) < 5
    # Check projected rays, including the image periphery, instead of relying on
    # individual weakly constrained high-order distortion coefficients.
    xx, yy = np.meshgrid(np.linspace(-.55, .55, 9), np.linspace(-.32, .32, 7))
    rays = np.c_[xx.ravel(), yy.ravel(), np.ones(xx.size)]
    truth = cv2.projectPoints(rays, np.zeros(3), np.zeros(3), K, D)[0]
    estimate = cv2.projectPoints(rays, np.zeros(3), np.zeros(3), recovered, distortion)[0]
    assert np.max(np.linalg.norm(truth - estimate, axis=2)) < 5
    assert len(list((tmp_path / 'overlays').glob('*.png'))) == 18
    assert info['spec_version'] == spec['version']


def test_skipped_images_are_reported(captures, tmp_path):
    _, paths, spec, _, _ = captures
    blank = tmp_path / 'blank.png'
    cv2.imwrite(str(blank), np.full((720, 1280, 3), 155, np.uint8))
    result = calibrate(paths + [blank], spec)
    assert result['input_images'] == 19
    assert result['used_images'] == 18
    assert result['skipped_images'] == [{'image': str(blank), 'reason': 'Fewer than six ChArUco corners'}]


def test_insufficient_views(captures):
    _, paths, spec, _, _ = captures
    with pytest.raises(ValueError, match='Need 10 usable views; found 2'):
        calibrate(paths[:2], spec)


def test_mixed_resolution(captures, tmp_path):
    _, paths, spec, _, _ = captures
    small = tmp_path / 'small.png'
    cv2.imwrite(str(small), np.zeros((480, 640, 3), np.uint8))
    with pytest.raises(ValueError, match='same resolution'):
        calibrate([paths[0], small], spec)


def test_missing_image(captures, tmp_path):
    _, _, spec, _, _ = captures
    with pytest.raises(ValueError, match='Cannot read image'):
        calibrate([tmp_path / 'missing.png'], spec)


def test_image_input_expansion(captures):
    root, paths, _, _, _ = captures
    assert image_paths([str(root)]) == paths
    assert image_paths([str(root / '*.png')]) == paths
    with pytest.raises(ValueError, match='Duplicate'):
        image_paths([str(paths[0]), str(paths[0])])
    with pytest.raises(ValueError, match='No input images'):
        image_paths([str(root / 'missing*.png')])
